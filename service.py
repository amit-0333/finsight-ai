import json
from pathlib import Path
from inputs import form_to_applicant
from common import prob
from explain import explain
from whatif import what_if, suggest_actions
from guidance import checklist, band
from llm import build_payload, generate_explanation

BASE = Path(__file__).parent
DISCLAIMER = "Estimate only - not financial advice or a lending decision."
DATA_SOURCE = "Synthetic data calibrated to TransUnion CIBIL published aggregates"


def predict_applicant(form, language="en", use_llm=True):
    applicant, age, errors = form_to_applicant(form)
    if errors:
        return {"errors": errors}
    p = prob(applicant)
    sa = suggest_actions(applicant, age=age)
    ex = explain(applicant)
    payload = build_payload(applicant, age, language)
    return {
        "probability": round(p, 3),
        "approval_percent": round(p * 100),
        "band": band(p),
        "factors_hurting": ex["hurting"],
        "factors_helping": ex["helping"],
        "suggested_actions": sa["actions"],
        "if_all_done": sa["if_all_done"],
        "explanation": generate_explanation(payload, use_llm=use_llm),
        "checklist": checklist(applicant["employment_type"]),
        "applicant": applicant,          # sent back so the UI can call what-if; never stored
        "age": age,
        "language": language,
        "disclaimer": DISCLAIMER,
        "data_source": DATA_SOURCE,
    }


def whatif_applicant(applicant, changes):
    out = what_if(applicant, changes)
    out["disclaimer"] = DISCLAIMER
    return out


def dashboard_summary():
    stats = json.load(open(BASE / "models" / "dashboard_stats.json", encoding="utf-8"))
    metrics = json.load(open(BASE / "models" / "metrics.json", encoding="utf-8"))
    return {"stats": stats, "metrics": metrics, "data_source": DATA_SOURCE, "disclaimer": DISCLAIMER}