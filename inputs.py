def form_to_applicant(f):
    """f = dict of form values. Returns (applicant, age, errors)."""
    errors = []
    ntc = 1 if f.get("no_credit_history") else 0

    def need(key, lo, hi, label):
        v = f.get(key)
        if v is None or not (lo <= v <= hi):
            errors.append(f"{label} must be between {lo} and {hi}")
        return v

    income = need("monthly_income", 5000, 5_000_000, "Monthly income")
    amount = need("loan_amount_requested", 10_000, 10_000_000, "Loan amount")
    tenure = need("loan_tenure_months", 6, 84, "Tenure (months)")
    age = need("age", 21, 62, "Age")
    if ntc == 0:
        need("cibil_score", 300, 900, "CIBIL score")
        need("credit_utilisation_pct", 0, 100, "Card usage")

    # tenure must end before age 60
    if age is not None and tenure is not None and age + tenure / 12 > 60:
        errors.append("Loan must finish before age 60: choose a shorter tenure")

    docs = f.get("docs", {})            # e.g. {"id": True, "address": True, "income": True, "bank": True}
    documents_complete = 1 if docs and all(docs.values()) else 0

    applicant = {
        "monthly_income": income,
        "employment_type": f.get("employment_type", "salaried"),
        "employment_years": f.get("employment_years", 0),
        "residence_years": f.get("residence_years", 0),
        "is_new_to_credit": ntc,
        "cibil_score": None if ntc else f.get("cibil_score"),
        "credit_age_years": None if ntc else f.get("credit_age_years"),
        "credit_utilisation_pct": None if ntc else f.get("credit_utilisation_pct"),
        "recent_enquiries_6m": 0 if ntc else f.get("recent_enquiries_6m", 0),
        "missed_payments_12m": 0 if ntc else f.get("missed_payments_12m", 0),
        "existing_loans_count": f.get("existing_loans_count", 0),
        "existing_emi_monthly": f.get("existing_emi_monthly", 0),
        "loan_amount_requested": amount,
        "loan_tenure_months": tenure,
        "documents_complete": documents_complete,
    }
    return applicant, age, errors