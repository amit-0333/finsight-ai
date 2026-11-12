import numpy as np
import pandas as pd

NUMERIC = ["monthly_income", "employment_years", "residence_years", "is_new_to_credit",
           "cibil_score", "credit_age_years", "credit_utilisation_pct",
           "recent_enquiries_6m", "missed_payments_12m", "existing_loans_count",
           "existing_emi_monthly", "loan_amount_requested", "loan_tenure_months",
           "foir_current", "foir_post_loan", "loan_to_monthly_income", "documents_complete"]
CATEGORICAL = ["employment_type"]
FEATURES = NUMERIC + CATEGORICAL
SENSITIVE = ["gender", "city_tier", "age"]


def get_rate(score, is_ntc):
    rate = np.select([score <= 670, score <= 730, score <= 800, score <= 850],
                     [19, 15.5, 13, 11.5], default=10.75)
    return np.where(is_ntc == 1, 17, rate)


def get_emi(amount, rate, months):
    r = rate / 1200
    return amount * r * (1 + r) ** months / ((1 + r) ** months - 1)


def make_features(df):
    d = df.copy()
    rate = get_rate(d["cibil_score"].fillna(0), d["is_new_to_credit"])
    emi = get_emi(d["loan_amount_requested"], rate, d["loan_tenure_months"])
    d["foir_current"] = d["existing_emi_monthly"] / d["monthly_income"]
    d["foir_post_loan"] = (d["existing_emi_monthly"] + emi) / d["monthly_income"]
    d["loan_to_monthly_income"] = d["loan_amount_requested"] / d["monthly_income"]
    return d[FEATURES]
