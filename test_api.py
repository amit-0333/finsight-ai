import json
from api import app

c = app.test_client()
form = {
    "monthly_income": 30000, "employment_type": "salaried", "employment_years": 3,
    "residence_years": 2, "no_credit_history": False, "cibil_score": 720,
    "credit_age_years": 4, "credit_utilisation_pct": 85, "recent_enquiries_6m": 3,
    "missed_payments_12m": 1, "existing_loans_count": 2, "existing_emi_monthly": 6000,
    "loan_amount_requested": 300000, "loan_tenure_months": 36, "age": 35,
    "docs": {"id": True, "address": True, "income": False, "bank": True},
}

print("HEALTH:", c.get("/api/health").get_json())

r = c.post("/api/predict", json={"form": form, "language": "en", "use_llm": False})
res = r.get_json()
print("PREDICT:", r.status_code, "| percent:", res["approval_percent"], "| band:", res["band"],
      "| source:", res["explanation"]["source"])

r2 = c.post("/api/whatif", json={"applicant": res["applicant"], "changes": {"documents_complete": 1}})
print("WHATIF:", r2.status_code, r2.get_json())

r3 = c.get("/api/dashboard/summary")
d = r3.get_json()
print("DASHBOARD:", r3.status_code, "| rows:", d["stats"]["rows_used"],
      "| shipped:", d["metrics"]["shipped_model"])

bad = c.post("/api/predict", json={"form": {**form, "cibil_score": 950}})
print("BAD INPUT:", bad.status_code, bad.get_json())

bad2 = c.post("/api/whatif", json={"applicant": res["applicant"], "changes": {"age": 20}})
print("BAD WHATIF:", bad2.status_code, bad2.get_json())