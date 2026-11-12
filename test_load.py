import joblib, json
import pandas as pd
from features import make_features

model = joblib.load("models/logistic.joblib")
metrics = json.load(open("models/metrics.json"))

person = pd.DataFrame([{
    "monthly_income": 30000, "employment_type": "salaried", "employment_years": 3,
    "residence_years": 2, "is_new_to_credit": 0, "cibil_score": 720, "credit_age_years": 4,
    "credit_utilisation_pct": 40, "recent_enquiries_6m": 1, "missed_payments_12m": 0,
    "existing_loans_count": 1, "existing_emi_monthly": 3000,
    "loan_amount_requested": 150000, "loan_tenure_months": 36, "documents_complete": 1,
    "foir_current": 0, "foir_post_loan": 0, "loan_to_monthly_income": 0,
}])

X = make_features(person)
print("approval probability:", round(float(model.predict_proba(X)[0, 1]), 3))
print("model test AUC from metrics.json:", metrics["models"]["logistic"]["roc_auc_test"])