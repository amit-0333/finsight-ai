import numpy as np
from common import MODEL, to_frame, is_ntc, CREDIT_FIELDS
from features import make_features

LABELS = {
    "monthly_income": "Monthly income", "employment_years": "Years in current job/business",
    "residence_years": "Years at current residence", "is_new_to_credit": "New to credit",
    "cibil_score": "CIBIL score", "credit_age_years": "Length of credit history",
    "credit_utilisation_pct": "Credit card usage", "recent_enquiries_6m": "Loan enquiries (6 months)",
    "missed_payments_12m": "Missed payments (12 months)", "existing_loans_count": "Existing loans",
    "existing_emi_monthly": "Existing monthly EMIs", "loan_amount_requested": "Loan amount asked",
    "loan_tenure_months": "Loan tenure", "foir_current": "Current EMI burden",
    "foir_post_loan": "EMI burden after this loan", "loan_to_monthly_income": "Loan size vs income",
    "documents_complete": "Documents",
}


def inr(x):
    """Indian number format: Rs 2,00,000"""
    x = int(round(x))
    s = str(abs(x))
    if len(s) > 3:
        head, tail = s[:-3], s[-3:]
        parts = []
        while len(head) > 2:
            parts.insert(0, head[-2:])
            head = head[:-2]
        if head:
            parts.insert(0, head)
        s = ",".join(parts + [tail])
    return "Rs " + ("-" if x < 0 else "") + s


def fmt(feature, v):
    if v is None or (isinstance(v, float) and np.isnan(v)):
        return "not given"
    if feature in ("monthly_income", "existing_emi_monthly", "loan_amount_requested"):
        return inr(v)
    if feature in ("foir_current", "foir_post_loan"):
        return f"{v * 100:.0f}% of income"
    if feature == "credit_utilisation_pct":
        return f"{v:.0f}% of limit used"
    if feature == "loan_to_monthly_income":
        return f"{v:.1f}x monthly income"
    if feature == "documents_complete":
        return "Complete" if v >= 1 else "Incomplete"
    if feature in ("employment_years", "residence_years", "credit_age_years"):
        return f"{v:.1f} years"
    if feature == "loan_tenure_months":
        return f"{int(v)} months"
    if feature == "is_new_to_credit":
        return "Yes" if v >= 1 else "No"
    return str(int(v)) if float(v).is_integer() else f"{v:.2f}"

def fmt_hi(feature, v):
    if v is None or (isinstance(v, float) and np.isnan(v)):
        return "दी नहीं गई"
    if feature in ("monthly_income", "existing_emi_monthly", "loan_amount_requested"):
        return inr(v)
    if feature in ("foir_current", "foir_post_loan"):
        return f"आय का {v * 100:.0f}%"
    if feature == "credit_utilisation_pct":
        return f"लिमिट का {v:.0f}% उपयोग"
    if feature == "loan_to_monthly_income":
        return f"मासिक आय का {v:.1f} गुना"
    if feature == "documents_complete":
        return "पूरे" if v >= 1 else "अधूरे"
    if feature in ("employment_years", "residence_years", "credit_age_years"):
        return f"{v:.1f} वर्ष"
    if feature == "loan_tenure_months":
        return f"{int(v)} महीने"
    if feature == "is_new_to_credit":
        return "हाँ" if v >= 1 else "नहीं"
    return str(int(v)) if float(v).is_integer() else f"{v:.2f}"


GROUP = ["foir_current", "foir_post_loan", "loan_to_monthly_income"]


def explain(applicant, top=3):
    """contribution = coefficient x scaled value (log-odds push vs an average applicant).
    The 3 correlated ratio features are merged into one factor so signs don't mislead."""
    X = make_features(to_frame(applicant))
    prep, lr = MODEL.named_steps["prep"], MODEL.named_steps["model"]
    Z = prep.transform(X)
    Z = np.asarray(Z.todense()) if hasattr(Z, "todense") else np.asarray(Z)
    names = prep.get_feature_names_out()
    contrib = Z[0] * lr.coef_[0]

    skip = set(CREDIT_FIELDS) if is_ntc(applicant) else set()
    if not is_ntc(applicant):
        skip.add("is_new_to_credit")      # "New to credit: No" is not a useful reason
    push = {}
    for name, c in zip(names, contrib):
        if name.startswith("num__"):          # employment_type is not centred, so not ranked
            f = name[len("num__"):]
            if f not in skip:
                push[f] = float(c)

    row = X.iloc[0]
    rows = []
    burden = sum(push.pop(f, 0.0) for f in GROUP)
    rows.append({"feature": "emi_burden", "label": "EMI burden and loan size vs income",
                 "value": f"{fmt('foir_post_loan', row['foir_post_loan'])} after this loan; "
                          f"loan is {fmt('loan_to_monthly_income', row['loan_to_monthly_income'])}",
                 "value_hi": f"लोन के बाद {fmt_hi('foir_post_loan', row['foir_post_loan'])}; "
                             f"लोन {fmt_hi('loan_to_monthly_income', row['loan_to_monthly_income'])}",
                 "push": round(burden, 3)})
    for f, c in push.items():
        rows.append({"feature": f, "label": LABELS[f], "value": fmt(f, row[f]),
                     "value_hi": fmt_hi(f, row[f]), "push": round(c, 3)})

    MIN_PUSH = 0.05          # ignore factors with almost no effect
    hurting = sorted([r for r in rows if r["push"] <= -MIN_PUSH], key=lambda r: r["push"])[:top]
    helping = sorted([r for r in rows if r["push"] >= MIN_PUSH], key=lambda r: -r["push"])[:top]
    for r in hurting:
        r["effect"] = "lowers your chances"
    for r in helping:
        r["effect"] = "improves your chances"
    return {"hurting": hurting, "helping": helping}