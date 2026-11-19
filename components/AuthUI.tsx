"use client";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState, type FormEvent, type ReactNode } from "react";
import { API_URL, api, ApiError, safeNext } from "@/lib/api";
import { useAuth } from "@/lib/auth";

export function AuthShell({ title, subtitle, children, footer }: { title: string; subtitle?: string; children: ReactNode; footer?: ReactNode }) {
  return (
    <div className="grid min-h-screen lg:grid-cols-2">
      <main className="flex flex-col px-6 py-8 sm:px-12">
        <Link href="/" className="flex w-fit items-center gap-2 font-display text-lg font-extrabold tracking-tight">
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img src="/logo-mark.svg" alt="" className="h-9 w-9" />Freda <span className="text-electric">Verify</span>
        </Link>
        <div className="mx-auto flex w-full max-w-sm flex-1 flex-col justify-center py-10">
          <h1 className="font-display text-3xl font-extrabold tracking-tight">{title}</h1>
          {subtitle && <p className="mt-2 text-sm text-navy/60">{subtitle}</p>}
          {!API_URL && <p role="alert" className="mt-5 rounded-xl border border-[#f1d9b6] bg-[#FEF3E2] p-3 text-xs text-[#B54708]">The API address is not configured for this build (<code>NEXT_PUBLIC_API_URL</code>). Sign-in will not work.</p>}
          <div className="mt-6">{children}</div>
          {footer && <div className="mt-6 text-center text-sm text-navy/60">{footer}</div>}
        </div>
      </main>
      <aside className="relative hidden overflow-hidden bg-navy p-12 text-white lg:flex lg:flex-col lg:justify-between" aria-hidden>
        <div className="pointer-events-none absolute -right-24 -top-24 h-96 w-96 rounded-full bg-blue/40 blur-3xl" />
        <div className="pointer-events-none absolute -bottom-32 -left-16 h-96 w-96 rounded-full bg-electric/30 blur-3xl" />
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img src="/logo-mark.svg" alt="" className="relative h-14 w-14" />
        <div className="relative">
          <p className="font-display text-4xl font-extrabold leading-tight tracking-tight">Verify identities.<br />Detect fraud.<br /><span className="text-sky">Protect businesses.</span></p>
          <ul className="mt-8 space-y-3 text-sm text-white/75">
            {["A hosted verification page in your own brand", "API keys for test and live, with an audit trail", "Teams, roles and organization-level isolation"].map((t) => (
              <li key={t} className="flex items-center gap-3"><span className="grid h-5 w-5 place-items-center rounded-full bg-white/15 text-[11px]">✓</span>{t}</li>
            ))}
          </ul>
        </div>
        <p className="relative text-xs text-white/50">Freda Verify</p>
      </aside>
    </div>
  );
}

export function Field({ label, error, hint, ...p }: { label: string; error?: string; hint?: string } & React.InputHTMLAttributes<HTMLInputElement>) {
  return (
    <label className="block text-sm font-medium">
      {label}
      <input {...p} aria-invalid={!!error} className="mt-1.5 block w-full rounded-xl border border-[#d6e2ff] bg-white px-3.5 py-3 text-[15px] font-normal outline-none transition focus:border-blue focus:ring-2 focus:ring-blue/20 aria-[invalid=true]:border-[#D92D20]" />
      {error ? <span role="alert" className="mt-1 block text-xs font-normal text-[#B42318]">{error}</span> : hint ? <span className="mt-1 block text-xs font-normal text-navy/50">{hint}</span> : null}
    </label>
  );
}

export const PrimaryButton = ({ busy, children }: { busy?: boolean; children: ReactNode }) => (
  <button disabled={busy} className="w-full rounded-full bg-blue py-3 text-[15px] font-semibold text-white transition hover:bg-navy disabled:opacity-60">{busy ? "…" : children}</button>
);

const fieldErrors = (e: unknown): Record<string, string> => (e instanceof ApiError ? Object.fromEntries(e.details.map((d) => [d.field, d.message])) : {});
const topError = (e: unknown): string => {
  if (!(e instanceof ApiError)) return "Something went wrong. Please try again.";
  if (e.code === "validation_error" && e.details.length) return "";
  if (e.code === "rate_limited") return "Too many attempts. Please wait a moment and try again.";
  return e.message;
};

function useRedirectIfSignedIn() {
  const { status } = useAuth();
  const router = useRouter();
  useEffect(() => { if (status === "authed") router.replace(safeNext(new URLSearchParams(window.location.search).get("next"))); }, [status, router]);
  return status;
}
const nextParam = () => (typeof window === "undefined" ? "" : new URLSearchParams(window.location.search).get("next") ?? "");
const withNext = (path: string, n: string) => (n ? `${path}?next=${encodeURIComponent(n)}` : path);
/** `?next=` is read after hydration (the pages are prerendered, so it cannot be known earlier). */
function useNext(): string { const [n, setN] = useState(""); useEffect(() => setN(nextParam()), []); return n; }

export function LoginForm() {
  const { login, verifyMfa } = useAuth();
  const next = useNext();
  const router = useRouter();
  useRedirectIfSignedIn();
  const [email, setEmail] = useState(""), [password, setPassword] = useState(""), [remember, setRemember] = useState(true);
  const [mfa, setMfa] = useState<string | null>(null), [code, setCode] = useState("");
  const [busy, setBusy] = useState(false), [error, setError] = useState(""), [fe, setFe] = useState<Record<string, string>>({});

  const done = () => router.replace(safeNext(nextParam()));
  const submit = async (e: FormEvent) => {
    e.preventDefault(); setBusy(true); setError(""); setFe({});
    try {
      if (mfa) { await verifyMfa(mfa, code, remember); done(); }
      else { const r = await login(email, password, remember); if ("mfaToken" in r) setMfa(r.mfaToken); else done(); }
    } catch (err) { setError(topError(err)); setFe(fieldErrors(err)); if (err instanceof ApiError && mfa && err.status === 401 && /expired/i.test(err.message)) setMfa(null); } finally { setBusy(false); }
  };

  return (
    <AuthShell title={mfa ? "Two-step verification" : "Welcome back"} subtitle={mfa ? "Enter the 6-digit code from your authenticator app, or one of your recovery codes." : "Sign in to your Freda Verify workspace."}
      footer={mfa ? <button type="button" onClick={() => { setMfa(null); setCode(""); setError(""); }} className="font-semibold text-blue">← Back</button> : <>No account yet? <Link href={withNext("/signup", next)} className="font-semibold text-blue">Create one</Link></>}>
      <form onSubmit={submit} className="space-y-4" noValidate>
        {error && <p role="alert" className="rounded-xl border border-[#f1b8b2] bg-[#FDECEA] p-3 text-sm text-[#B42318]">{error}</p>}
        {mfa ? (
          <Field label="Authentication code" value={code} onChange={(e) => setCode(e.target.value)} inputMode="text" autoComplete="one-time-code" autoFocus required placeholder="123456" />
        ) : (<>
          <Field label="Email" type="email" value={email} onChange={(e) => setEmail(e.target.value)} autoComplete="email" required error={fe.email} />
          <Field label="Password" type="password" value={password} onChange={(e) => setPassword(e.target.value)} autoComplete="current-password" required error={fe.password} />
          <div className="flex items-center justify-between text-sm">
            <label className="flex items-center gap-2"><input type="checkbox" checked={remember} onChange={(e) => setRemember(e.target.checked)} className="h-4 w-4 accent-blue" />Keep me signed in</label>
            <Link href="/forgot-password" className="font-medium text-blue">Forgot password?</Link>
          </div>
        </>)}
        <PrimaryButton busy={busy}>{mfa ? "Verify" : "Sign in"}</PrimaryButton>
      </form>
    </AuthShell>
  );
}

export function SignupForm() {
  const { register } = useAuth();
  const next = useNext();
  const router = useRouter();
  useRedirectIfSignedIn();
  const [v, setV] = useState({ full_name: "", organization_name: "", email: "", password: "" });
  const [busy, setBusy] = useState(false), [error, setError] = useState(""), [fe, setFe] = useState<Record<string, string>>({});
  const set = (k: keyof typeof v) => (e: React.ChangeEvent<HTMLInputElement>) => setV({ ...v, [k]: e.target.value });

  const submit = async (e: FormEvent) => {
    e.preventDefault(); setBusy(true); setError(""); setFe({});
    try { await register(v, true); router.replace(safeNext(nextParam())); }
    catch (err) { setError(topError(err)); setFe(fieldErrors(err)); } finally { setBusy(false); }
  };
  return (
    <AuthShell title="Create your account" subtitle="Set up your workspace in a minute." footer={<>Already have an account? <Link href={withNext("/login", next)} className="font-semibold text-blue">Sign in</Link></>}>
      <form onSubmit={submit} className="space-y-4" noValidate>
        {error && <p role="alert" className="rounded-xl border border-[#f1b8b2] bg-[#FDECEA] p-3 text-sm text-[#B42318]">{error}</p>}
        <Field label="Your name" value={v.full_name} onChange={set("full_name")} autoComplete="name" required error={fe.full_name} />
        <Field label="Company / organization" value={v.organization_name} onChange={set("organization_name")} autoComplete="organization" required error={fe.organization_name} />
        <Field label="Work email" type="email" value={v.email} onChange={set("email")} autoComplete="email" required error={fe.email} />
        <Field label="Password" type="password" value={v.password} onChange={set("password")} autoComplete="new-password" required error={fe.password} hint="At least 10 characters. Avoid common passwords and your email name." />
        <PrimaryButton busy={busy}>Create account</PrimaryButton>
        <p className="text-center text-xs text-navy/50">By creating an account you agree to the processing of your data to run the service.</p>
      </form>
    </AuthShell>
  );
}

export function ForgotForm() {
  const [email, setEmail] = useState(""), [busy, setBusy] = useState(false), [sent, setSent] = useState(false), [error, setError] = useState("");
  const submit = async (e: FormEvent) => {
    e.preventDefault(); setBusy(true); setError("");
    try { await api("/auth/password/forgot", { method: "POST", json: { email }, auth: false }); setSent(true); } catch (err) { setError(topError(err)); } finally { setBusy(false); }
  };
  return (
    <AuthShell title="Reset your password" subtitle="Enter your email and we will send you a reset link." footer={<Link href="/login" className="font-semibold text-blue">← Back to sign in</Link>}>
      {sent ? <p role="status" className="rounded-xl border border-[#b7e8cf] bg-[#E7F7EF] p-4 text-sm text-[#067647]">If an account exists for this email, a reset link has been sent.</p> : (
        <form onSubmit={submit} className="space-y-4" noValidate>
          {error && <p role="alert" className="rounded-xl border border-[#f1b8b2] bg-[#FDECEA] p-3 text-sm text-[#B42318]">{error}</p>}
          <Field label="Email" type="email" value={email} onChange={(e) => setEmail(e.target.value)} autoComplete="email" required />
          <PrimaryButton busy={busy}>Send reset link</PrimaryButton>
        </form>
      )}
    </AuthShell>
  );
}

export function ResetForm() {
  const router = useRouter();
  const [token, setToken] = useState(""), [pw, setPw] = useState(""), [busy, setBusy] = useState(false), [error, setError] = useState(""), [fe, setFe] = useState<Record<string, string>>({}), [ok, setOk] = useState(false);
  useEffect(() => setToken(new URLSearchParams(window.location.search).get("token") ?? ""), []);
  const submit = async (e: FormEvent) => {
    e.preventDefault(); setBusy(true); setError(""); setFe({});
    try { await api("/auth/password/reset", { method: "POST", json: { token, new_password: pw }, auth: false }); setOk(true); setTimeout(() => router.replace("/login"), 1800); }
    catch (err) { setError(topError(err)); setFe(fieldErrors(err)); } finally { setBusy(false); }
  };
  return (
    <AuthShell title="Choose a new password" footer={<Link href="/login" className="font-semibold text-blue">← Back to sign in</Link>}>
      {ok ? <p role="status" className="rounded-xl border border-[#b7e8cf] bg-[#E7F7EF] p-4 text-sm text-[#067647]">Password updated. Redirecting to sign in…</p> : !token ? <p role="alert" className="text-sm text-[#B42318]">This reset link is missing its token. Request a new one.</p> : (
        <form onSubmit={submit} className="space-y-4" noValidate>
          {error && <p role="alert" className="rounded-xl border border-[#f1b8b2] bg-[#FDECEA] p-3 text-sm text-[#B42318]">{error}</p>}
          <Field label="New password" type="password" value={pw} onChange={(e) => setPw(e.target.value)} autoComplete="new-password" required error={fe.new_password} hint="At least 10 characters." />
          <PrimaryButton busy={busy}>Update password</PrimaryButton>
        </form>
      )}
    </AuthShell>
  );
}
