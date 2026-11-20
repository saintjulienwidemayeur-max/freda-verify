"""Automatic KYC decision (opt-in per organization). A PURE function over the machine checks, so it can be tested and audited; the policy is the organization's own.

Rules (conservative on purpose; none of the underlying checks is certified, see CLAUDE.md):
- APPROVE only if the machine-readable zone was read with EVERY check digit valid and at least two independent readings agree, the document is not expired, the face comparison
  ran and reached the organization's minimum score, and (if the organization requires it) the experimental live-capture score is not low.
- REJECT automatically only for an OBJECTIVE failure: the document is expired and its expiry-date check digit is valid (so the date was read correctly).
- Everything else is UNCERTAIN: left for a person (policy `review`, the default) or rejected (policy `reject`, an explicit choice of the organization that WILL turn away some real people).
Reason codes carry no personal data.
"""
from dataclasses import dataclass, field


@dataclass
class Verdict:
    decision: str | None                 # APPROVED | REJECTED | None (needs a person)
    codes: list[str] = field(default_factory=list)


def decide(*, face_min: float, require_pad: bool, uncertain: str, mrz: dict | None, agreeing: int, face: dict | None, pad: dict | None, doc_type: str | None,
           id_cards: str = "review", idtext: dict | None = None) -> Verdict:
    hard: list[str] = []
    unc: list[str] = []
    is_card = doc_type in ("id", "license")
    if is_card:
        # ID cards / licences have no machine-readable zone. `face_only` (organization's explicit risk choice): no document check at all. `face_and_data`: the printed text must agree with the data
        # the customer declared (>= 2 declared fields, name among them). Anything else goes to a person.
        if id_cards == "face_only":
            pass
        elif id_cards == "face_and_data":
            ok = bool(idtext) and idtext.get("status") == "compared" and idtext.get("fields", 0) >= 2 and idtext.get("matched", 0) >= 2 and idtext.get("name", 0) >= 0.8
            if not ok:
                unc.append("id_data_" + (idtext.get("status", "missing") if idtext else "missing") if not (idtext and idtext.get("status") == "compared") else "id_data_mismatch")
        else:
            unc.append("no_mrz_for_id")
    elif not mrz:
        unc.append("mrz_unreadable")
    else:
        checks = mrz.get("checks", {})
        if mrz.get("expired") and checks.get("expiry_date"):
            hard.append("document_expired")
        if mrz.get("all_checks_passed"):
            if agreeing < 2:
                unc.append("single_reading")
        elif all(checks.get(k) for k in ("document_number", "birth_date", "expiry_date")):
            unc.append("mrz_partial")
        else:
            unc.append("mrz_invalid")
    if not face or face.get("status") != "compared" or face.get("score") is None:
        unc.append("face_" + (face.get("status", "missing") if face else "missing"))
    elif face["score"] < face_min:
        unc.append("face_low")
    if require_pad:
        if not pad or pad.get("status") != "scored" or pad.get("real_probability") is None:
            unc.append("pad_" + (pad.get("status", "missing") if pad else "missing"))
        elif pad.get("band") == "low" or pad["real_probability"] < 0.5:
            unc.append("pad_low")
    if hard:
        return Verdict("REJECTED", hard)
    if not unc:
        return Verdict("APPROVED", ["all_checks_passed"])
    return Verdict("REJECTED" if uncertain == "reject" else None, unc)
