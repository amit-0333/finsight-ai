from flask import Flask, request, jsonify
from service import predict_applicant, whatif_applicant, dashboard_summary
from werkzeug.exceptions import HTTPException
app = Flask(__name__)
app.json.ensure_ascii = False          # keep Hindi readable

ALLOWED = {"monthly_income", "employment_type", "employment_years", "residence_years",
           "is_new_to_credit", "cibil_score", "credit_age_years", "credit_utilisation_pct",
           "recent_enquiries_6m", "missed_payments_12m", "existing_loans_count",
           "existing_emi_monthly", "loan_amount_requested", "loan_tenure_months",
           "documents_complete"}




@app.get("/")
def index():
    return jsonify({"app": "FinSight AI API",
                    "endpoints": ["GET /api/health", "POST /api/predict",
                                  "POST /api/whatif", "GET /api/dashboard/summary"]})


@app.errorhandler(Exception)
def on_error(e):                       # never echo or log applicant data
    if isinstance(e, HTTPException):
        return jsonify({"errors": [e.name]}), e.code
    return jsonify({"errors": ["Something went wrong: " + type(e).__name__]}), 500

@app.get("/api/health")
def health():
    return jsonify({"status": "ok", "model": "logistic"})

@app.get("/api/")
def api_index():
    return jsonify({"app": "FinSight AI API",
                    "endpoints": ["GET /api/health", "GET /api/metrics", "POST /api/predict",
                                  "POST /api/whatif", "GET /api/dashboard/summary"]})


@app.get("/api/metrics")
def metrics():
    from service import dashboard_summary
    d = dashboard_summary()
    return jsonify({"metrics": d["metrics"], "data_source": d["data_source"],
                    "disclaimer": d["disclaimer"]})


@app.post("/api/predict")
def predict():
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return jsonify({"errors": ["Send a JSON body"]}), 400
    form = data.get("form", data)
    result = predict_applicant(form, language=data.get("language", "en"),
                               use_llm=data.get("use_llm", True))
    return jsonify(result), (400 if "errors" in result else 200)


@app.post("/api/whatif")
def whatif():
    data = request.get_json(silent=True)
    if not isinstance(data, dict) or "applicant" not in data or "changes" not in data:
        return jsonify({"errors": ["Send {applicant, changes}"]}), 400
    bad = [k for k in data["changes"] if k not in ALLOWED]
    if bad:
        return jsonify({"errors": [f"Cannot change: {', '.join(bad)}"]}), 400
    return jsonify(whatif_applicant(data["applicant"], data["changes"]))


@app.get("/api/dashboard/summary")
def dashboard():
    return jsonify(dashboard_summary())


@app.errorhandler(Exception)
def on_error(e):                       # never echo or log applicant data
    return jsonify({"errors": ["Something went wrong: " + type(e).__name__]}), 500


if __name__ == "__main__":
    app.run(port=5000, debug=False)
