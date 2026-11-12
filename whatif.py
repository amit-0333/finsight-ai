import json
from pathlib import Path
from common import prob, is_ntc, CREDIT_FIELDS
from explain import inr

_RULE_PATH = Path(__file__).parent / "models" / "score_rule.json"
RULE = json.load(open(_RULE_PATH)) if _RULE_PATH.exists() else None


def with_score(applicant, new):
    """If card usage changed, estimate the new CIBIL score.
    Assumption fitted on synthetic data (see score_rule.json), not a real bureau rule."""
    if RULE is None or RULE["per_utilisation_point"] >= 0 or is_ntc(applicant):
        return new
    old_u, new_u = applicant.get("credit_utilisation_pct"), new.get("credit_utilisation_pct")
    old_s = applicant.get("cibil_score")
    if old_u is None or new_u is None or old_s is None or old_u == new_u:
        return new
    est = old_s + RULE["per_utilisation_point"] * (new_u - old_u)
    new = dict(new)
    new["cibil_score"] = int(round(min(RULE["max_score"], max(300, est))))
    return new


def what_if(applicant, changes):
    """Apply changes, features are recomputed inside prob(). Returns old/new probability."""
    changes = dict(changes)
    ignored = []
    if is_ntc(applicant):                       # no credit history -> credit sliders do nothing
        for k in CREDIT_FIELDS:
            if k in changes:
                changes.pop(k)
                ignored.append(k)
    new = {**applicant, **changes}
    if "cibil_score" not in changes:
        new = with_score(applicant, new)
    old_p, new_p = prob(applicant), prob(new)

    old_s, new_s = applicant.get("cibil_score"), new.get("cibil_score")
    if old_s is not None and new_s is not None and old_s != new_s:
        note = (f"Estimated CIBIL score change: {int(old_s)} to {int(new_s)} "
                "(an assumption based on synthetic data, not a real bureau rule).")
    else:
        note = "Your CIBIL score is held the same in this estimate."
    return {"old_probability": round(old_p, 3), "new_probability": round(new_p, 3),
            "change": round(new_p - old_p, 3), "ignored": ignored, "note": note}


def _steps(a, age):
    """Candidate changes per action, from smallest to largest. Actionable features only."""
    acts = {}
    util = a.get("credit_utilisation_pct")
    if not is_ntc(a) and util is not None and util == util and util > 30:
        acts["util"] = [(f"Pay down card balances so usage is about {v}% of the limit",
                         {"credit_utilisation_pct": v}) for v in (60, 50, 40, 30, 20) if v < util]

    emi, cnt = a.get("existing_emi_monthly", 0), a.get("existing_loans_count", 0)
    if emi and emi > 0:
        steps = []
        for f in (0.75, 0.5, 0.25, 0.0):
            steps.append((f"Close or prepay existing loans so monthly EMIs fall to {inr(emi * f)}",
                          {"existing_emi_monthly": round(emi * f),
                           "existing_loans_count": max(0, round(cnt * f))}))
        acts["emi"] = steps

    amt = a.get("loan_amount_requested", 0)
    acts["amount"] = [(f"Ask for a smaller loan of {inr(round(amt * f, -3))}",
                       {"loan_amount_requested": int(round(amt * f, -3))})
                      for f in (0.9, 0.8, 0.7, 0.6, 0.5)]

    ten = int(a.get("loan_tenure_months", 36))
    max_ten = 84 if age is None else min(84, max(0, (60 - age) * 12))   # tenure must end before age 60
    acts["tenure"] = [(f"Choose a longer tenure of {t} months (lower EMI, more total interest)",
                       {"loan_tenure_months": t}) for t in range(ten + 12, max_ten + 1, 12)]

    if a.get("documents_complete", 1) == 0:
        acts["docs"] = [("Complete all required documents before applying", {"documents_complete": 1})]
    return acts


def suggest_actions(applicant, age=None, target=0.60, max_actions=3):
    base = prob(applicant)
    picks = []
    for key, steps in _steps(applicant, age).items():
        best = None
        for text, ch in steps:
            p = prob(with_score(applicant, {**applicant, **ch}))
            if best is None or p > best["new_probability"]:
                best = {"change": text, "changes": ch, "new_probability": round(p, 3)}
            if p >= target:                      # smallest step that reaches the target
                best = {"change": text, "changes": ch, "new_probability": round(p, 3)}
                break
        if best and best["new_probability"] - base >= 0.01:
            best["reaches_target"] = best["new_probability"] >= target
            picks.append(best)

    picks.sort(key=lambda r: (not r["reaches_target"], -r["new_probability"]))
    picks = picks[:max_actions]

    combined = None
    if len(picks) > 1:
        allch = {}
        for r in picks:
            allch.update(r["changes"])
        combined = round(prob(with_score(applicant, {**applicant, **allch})), 3)

    return {"current_probability": round(base, 3), "target": target,
            "actions": picks, "if_all_done": combined}