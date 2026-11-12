from inputs import form_to_applicant
from common import prob
from explain import explain
from whatif import what_if, suggest_actions
from guidance import checklist, band

# pretend these came from the web form
form = {
    "monthly_income": 30000, "employment_type": "salaried", "employment_years": 3,
    "residence_years": 2, "no_credit_history": False, "cibil_score": 720,
    "credit_age_years": 4, "credit_utilisation_pct": 85, "recent_enquiries_6m": 3,
    "missed_payments_12m": 1, "existing_loans_count": 2, "existing_emi_monthly": 6000,
    "loan_amount_requested": 300000, "loan_tenure_months": 36, "age": 35,
    "docs": {"id": True, "address": True, "income": False, "bank": True},   # one missing
}

applicant, age, errors = form_to_applicant(form)
print("errors:", errors)
print("documents_complete:", applicant["documents_complete"])

p = prob(applicant)
print("probability:", round(p, 3), "|", band(p))

r = explain(applicant)
print("\nHURTING:", [(x["label"], x["push"]) for x in r["hurting"]])
print("HELPING:", [(x["label"], x["push"]) for x in r["helping"]])

s = suggest_actions(applicant, age=age)
print("\nACTIONS:")
for a in s["actions"]:
    print(" -", a["change"], "->", a["new_probability"])
print("if all done:", s["if_all_done"])

print("\nWHAT-IF docs complete:", what_if(applicant, {"documents_complete": 1}))

# bad input should give clear errors
_, _, errs = form_to_applicant({**form, "cibil_score": 950, "age": 58, "loan_tenure_months": 60})
print("\nbad input errors:", errs)