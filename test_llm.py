from inputs import form_to_applicant
from llm import build_payload, generate_explanation
import json

form = {
    "monthly_income": 30000, "employment_type": "salaried", "employment_years": 3,
    "residence_years": 2, "no_credit_history": False, "cibil_score": 720,
    "credit_age_years": 4, "credit_utilisation_pct": 85, "recent_enquiries_6m": 3,
    "missed_payments_12m": 1, "existing_loans_count": 2, "existing_emi_monthly": 6000,
    "loan_amount_requested": 300000, "loan_tenure_months": 36, "age": 35,
    "docs": {"id": True, "address": True, "income": False, "bank": True},
}
applicant, age, errors = form_to_applicant(form)

for lang in ["en", "hi"]:
    payload = build_payload(applicant, age, lang)
    print("=" * 40, lang, "| payload size:", len(json.dumps(payload, ensure_ascii=False)), "chars")
    print("--- template:")
    print(json.dumps(generate_explanation(payload, use_llm=False), indent=1, ensure_ascii=False))
    print("--- groq:")
    print(json.dumps(generate_explanation(payload, use_llm=True), indent=1, ensure_ascii=False))