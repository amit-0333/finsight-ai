from pathlib import Path
import joblib
import pandas as pd
from features import make_features, NUMERIC

BASE = Path(__file__).parent
MODEL = joblib.load(BASE / "models" / "logistic.joblib")

CREDIT_FIELDS = ["cibil_score", "credit_age_years", "credit_utilisation_pct"]


def to_frame(applicant):
    """One applicant (dict of raw inputs) -> DataFrame with numeric columns."""
    df = pd.DataFrame([applicant])
    for c in NUMERIC:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce")
    return df


def prob(applicant):
    """Approval probability for one applicant."""
    X = make_features(to_frame(applicant))
    return float(MODEL.predict_proba(X)[0, 1])


def is_ntc(applicant):
    return int(applicant.get("is_new_to_credit", 0)) == 1