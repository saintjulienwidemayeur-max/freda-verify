import logging
import uuid
from datetime import timedelta

import pyotp
from fastapi import APIRouter, BackgroundTasks, Depends, Request
from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.core import ratelimit
from app.core.config import get_settings
from app.core.deps import get_current_user
from app.core.errors import AppError, unauthorized
from app.core.net import client_ip
from app.core.security import (
    create_jwt,
    decode_jwt,
    decrypt_secret,
    encrypt_secret,
    hash_password,
    new_hex,
    new_token,
    safe_equal,
    sha256,
    validate_password,
    verify_password,
)
from app.db.session import get_db
from app.models import Membership, Organization, PasswordResetToken, RecoveryCode, RefreshSession, Role, User, now
from app.schemas import ForgotIn, LoginIn, MfaCodeIn, MfaDisableIn, MfaRequiredOut, MfaVerifyIn, RefreshIn, RegisterIn, ResetIn, TokensOut, UserOut
from app.services import audit, mailer

router = APIRouter(prefix="/auth", tags=["auth"])
log = logging.getLogger("fv.auth")


def _slug(name: str) -> str:
    base = "".join(c if c.isalnum() else "-" for c in name.lower()).strip("-")
    return f"{'-'.join(p for p in base.split('-') if p)[:60] or 'org'}-{new_hex(3)}"


def _limit(request: Request, extra: str = "") -> None:
    ratelimit.enforce(f"auth:{client_ip(request)}", get_settings().auth_rate_limit)
    if extra:
        ratelimit.enforce(f"auth-id:{sha256(extra.lower())}", get_settings().auth_rate_limit)


def _issue(db: Session, request: Request, user: User) -> TokensOut:
    s = get_settings()
    refresh = new_token(48)
    db.add(RefreshSession(user_id=user.id, token_hash=sha256(refresh), user_agent=request.headers.get("user-agent", "")[:300],
                          ip=client_ip(request), expires_at=now() + timedelta(days=s.refresh_token_days)))
    user.last_login_at = now()
    return TokensOut(access_token=create_jwt(str(user.id), "access", s.access_token_minutes), refresh_token=refresh,
                     expires_in=s.access_token_minutes * 60, user=UserOut.model_validate(user))


def _revoke_all(db: Session, user_id) -> None:
    db.execute(update(RefreshSession).where(RefreshSession.user_id == user_id, RefreshSession.revoked_at.is_(None)).values(revoked_at=now()))


@router.post("/register", response_model=TokensOut, status_code=201)
def register(body: RegisterIn, request: Request, db: Session = Depends(get_db)):
    _limit(request, body.email)
    problems = validate_password(body.password, body.email)
    if problems:
        raise AppError(422, "weak_password", "Password " + ", ".join(problems), [{"field": "password", "message": p} for p in problems])
    email = body.email.lower()
    if db.scalar(select(User.id).where(User.email == email)):
        raise AppError(409, "email_taken", "An account with this e-mail already exists")
    user = User(email=email, password_hash=hash_password(body.password), full_name=body.full_name)
    org = Organization(name=body.organization_name, slug=_slug(body.organization_name))
    db.add_all([user, org])
    db.flush()
    db.add(Membership(organization_id=org.id, user_id=user.id, role=Role.owner))
    audit.record(db, request, "user.registered", org_id=org.id, user_id=user.id, target_type="user", target_id=user.id)
    audit.record(db, request, "org.created", org_id=org.id, user_id=user.id, target_type="organization", target_id=org.id)
    out = _issue(db, request, user)
    db.commit()
    return out


@router.post("/login", response_model=TokensOut | MfaRequiredOut)
def login(body: LoginIn, request: Request, db: Session = Depends(get_db)):
    _limit(request, body.email)
    s = get_settings()
    user = db.scalar(select(User).where(User.email == body.email.lower()))
    if user and user.locked_until and user.locked_until > now():
        raise AppError(429, "rate_limited", "Too many attempts. Try again later.", headers={"Retry-After": "900"})
    if not verify_password(body.password, user.password_hash if user else None) or not user or not user.is_active:
        if user:
            user.failed_logins += 1
            if user.failed_logins >= s.login_max_failures:
                user.locked_until, user.failed_logins = now() + timedelta(minutes=s.login_lock_minutes), 0
                audit.record(db, request, "auth.account_locked", user_id=user.id)
            audit.record(db, request, "auth.login_failed", user_id=user.id)
            db.commit()
        raise unauthorized("Invalid e-mail or password")
    user.failed_logins, user.locked_until = 0, None
    if user.mfa_enabled:
        db.commit()
        return MfaRequiredOut(mfa_token=create_jwt(str(user.id), "mfa", 5))
    out = _issue(db, request, user)
    audit.record(db, request, "auth.login", user_id=user.id)
    db.commit()
    return out


def _check_second_factor(db: Session, user: User, code: str) -> bool:
    code = code.strip().replace(" ", "")
    if user.mfa_secret_enc and code.isdigit() and len(code) == 6:
        totp = pyotp.TOTP(decrypt_secret(user.mfa_secret_enc))
        for step_offset in (0, -1, 1):
            step = int(now().timestamp() // 30) + step_offset
            if safe_equal(totp.at(step * 30), code):
                if user.mfa_last_step is not None and step <= user.mfa_last_step:
                    return False                                       # replay of an already used code
                user.mfa_last_step = step
                return True
        return False
    h = sha256(code.lower().replace("-", ""))                          # recovery code, single use
    rc = db.scalar(select(RecoveryCode).where(RecoveryCode.user_id == user.id, RecoveryCode.code_hash == h, RecoveryCode.used_at.is_(None)))
    if rc:
        rc.used_at = now()
        return True
    return False


@router.post("/mfa/verify", response_model=TokensOut)
def mfa_verify(body: MfaVerifyIn, request: Request, db: Session = Depends(get_db)):
    claims = decode_jwt(body.mfa_token, "mfa")
    if not claims:
        raise unauthorized("MFA session expired. Sign in again.")
    _limit(request, claims["sub"])
    user = db.get(User, uuid.UUID(claims["sub"]))
    if not user or not user.is_active or not user.mfa_enabled:
        raise unauthorized()
    if not _check_second_factor(db, user, body.code):
        audit.record(db, request, "auth.mfa_failed", user_id=user.id)
        db.commit()
        raise unauthorized("Invalid code")
    out = _issue(db, request, user)
    audit.record(db, request, "auth.login", user_id=user.id, meta={"mfa": True})
    db.commit()
    return out


@router.post("/refresh", response_model=TokensOut)
def refresh(body: RefreshIn, request: Request, db: Session = Depends(get_db)):
    _limit(request)
    sess = db.scalar(select(RefreshSession).where(RefreshSession.token_hash == sha256(body.refresh_token)))
    if not sess:
        raise unauthorized("Invalid refresh token")
    if sess.revoked_at is not None:                                   # a rotated/revoked token came back: assume theft, kill every session
        _revoke_all(db, sess.user_id)
        audit.record(db, request, "auth.refresh_reuse_detected", user_id=sess.user_id)
        db.commit()
        raise unauthorized("Invalid refresh token")
    user = db.get(User, sess.user_id)
    if sess.expires_at <= now() or not user or not user.is_active:
        raise unauthorized("Invalid refresh token")
    sess.revoked_at = now()
    out = _issue(db, request, user)
    db.commit()
    return out


@router.post("/logout", status_code=204)
def logout(body: RefreshIn, db: Session = Depends(get_db)):
    db.execute(update(RefreshSession).where(RefreshSession.token_hash == sha256(body.refresh_token), RefreshSession.revoked_at.is_(None)).values(revoked_at=now()))
    db.commit()


@router.get("/me", response_model=UserOut)
def me(user: User = Depends(get_current_user)):
    return user


@router.post("/password/forgot", status_code=202)
def forgot(body: ForgotIn, request: Request, background: BackgroundTasks, db: Session = Depends(get_db)):
    _limit(request, body.email)
    user = db.scalar(select(User).where(User.email == body.email.lower()))
    if user and user.is_active:
        token = new_token(32)
        db.add(PasswordResetToken(user_id=user.id, token_hash=sha256(token), expires_at=now() + timedelta(minutes=30)))
        audit.record(db, request, "auth.password_reset_requested", user_id=user.id)
        db.commit()
        if mailer.enabled():
            link = f"{get_settings().hosted_url.rstrip('/')}/reset-password?token={token}"
            # sent AFTER the response (background task) so the answer and its timing are identical whether or not the account exists
            background.add_task(mailer.send_email, [user.email], "Reset your Freda Verify password",
                                "Someone asked to reset the password of your Freda Verify account. The link below works once and expires in 30 minutes.\nIf it was not you, ignore this e-mail: your password is unchanged.",
                                ("Choose a new password", link))
        elif get_settings().app_env == "dev":
            log.warning("[dev only] password reset token for %s: %s", user.email, token)
        else:
            log.info("password reset requested (no e-mail provider configured)")
    return {"message": "If an account exists for this e-mail, a reset link has been sent."}   # identical response either way


@router.post("/password/reset", status_code=204)
def reset(body: ResetIn, request: Request, db: Session = Depends(get_db)):
    _limit(request)
    t = db.scalar(select(PasswordResetToken).where(PasswordResetToken.token_hash == sha256(body.token)))
    if not t or t.used_at is not None or t.expires_at <= now():
        raise AppError(400, "invalid_token", "This reset link is invalid or has expired")
    user = db.get(User, t.user_id)
    problems = validate_password(body.new_password, user.email)
    if problems:
        raise AppError(422, "weak_password", "Password " + ", ".join(problems), [{"field": "new_password", "message": p} for p in problems])
    user.password_hash, user.failed_logins, user.locked_until = hash_password(body.new_password), 0, None
    t.used_at = now()
    _revoke_all(db, user.id)
    audit.record(db, request, "auth.password_reset", user_id=user.id)
    db.commit()


@router.post("/mfa/setup")
def mfa_setup(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if user.mfa_enabled:
        raise AppError(409, "mfa_already_enabled", "MFA is already enabled")
    secret = pyotp.random_base32()
    user.mfa_secret_enc = encrypt_secret(secret)
    db.commit()
    return {"secret": secret, "otpauth_uri": pyotp.TOTP(secret).provisioning_uri(name=user.email, issuer_name="Freda Verify")}


@router.post("/mfa/enable")
def mfa_enable(body: MfaCodeIn, request: Request, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if user.mfa_enabled or not user.mfa_secret_enc:
        raise AppError(409, "mfa_not_pending", "Start with /auth/mfa/setup")
    if not _check_second_factor(db, user, body.code):
        raise AppError(400, "invalid_code", "Invalid code")
    user.mfa_enabled = True
    codes = [f"{h[:5]}-{h[5:]}" for h in (new_hex(5) for _ in range(8))]
    for c in codes:
        db.add(RecoveryCode(user_id=user.id, code_hash=sha256(c.replace("-", ""))))
    audit.record(db, request, "auth.mfa_enabled", user_id=user.id)
    db.commit()
    return {"recovery_codes": codes, "note": "Store these codes safely. Each works once and they are not shown again."}


@router.post("/mfa/disable", status_code=204)
def mfa_disable(body: MfaDisableIn, request: Request, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if not user.mfa_enabled:
        return
    if not verify_password(body.password, user.password_hash) or not _check_second_factor(db, user, body.code):
        raise AppError(400, "invalid_credentials", "Password or code is incorrect")
    user.mfa_enabled, user.mfa_secret_enc, user.mfa_last_step = False, None, None
    db.execute(RecoveryCode.__table__.delete().where(RecoveryCode.user_id == user.id))
    audit.record(db, request, "auth.mfa_disabled", user_id=user.id)
    db.commit()
