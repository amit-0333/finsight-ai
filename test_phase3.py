from common import prob
from explain import explain
from whatif import what_if, suggest_actions
from guidance import checklist, band
import json

base = {"monthly_income": 30000, "employment_type": "salaried", "employment_years": 3,
        "residence_years": 2, "is_new_to_credit": 0, "cibil_score": 720, "credit_age_years": 4,
        "credit_utilisation_pct": 85, "recent_enquiries_6m": 3, "missed_payments_12m": 1,
        "existing_loans_count": 2, "existing_emi_monthly": 6000,
        "loan_amount_requested": 300000, "loan_tenure_months": 36, "documents_complete": 0}

ntc = {**base, "is_new_to_credit": 1, "cibil_score": None, "credit_age_years": None,
       "credit_utilisation_pct": None, "recent_enquiries_6m": 0, "missed_payments_12m": 0,
       "existing_loans_count": 0, "existing_emi_monthly": 0}

for title, a in [("NORMAL APPLICANT", base), ("NEW-TO-CREDIT APPLICANT", ntc)]:
    p = prob(a)
    print("=" * 50, "\n", title, "| probability:", round(p, 3), "|", band(p))
    print(json.dumps(explain(a), indent=1))
    print(json.dumps(suggest_actions(a, age=35), indent=1))

print("\nWHAT-IF: pay card usage down to 30%")
print(what_if(base, {"credit_utilisation_pct": 30}))
print("WHAT-IF on new-to-credit (should be ignored):")
print(what_if(ntc, {"credit_utilisation_pct": 30}))
print("\nChecklist:", checklist("self_employed"))