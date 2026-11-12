# Architecture and workflow

How FinSight AI is put together and how data flows through it. See the [README](../README.md) for the overview, results and run steps.

> All data is **synthetic**, calibrated to TransUnion CIBIL published aggregates. Estimate only - not financial advice or a lending decision.

## 1. System architecture

One shared logic layer (`service.py`) serves two front doors: the Streamlit pages and the Flask REST API. The Streamlit pages call `service.py` directly, so the demo needs only one process.

```mermaid
flowchart TB
    B["Borrower"] --> APP["Streamlit borrower page<br/>app.py"]
    A["Lender analyst"] --> DASH["Streamlit lender dashboard<br/>pages/1_Lender_Dashboard.py"]
    API["Flask REST API<br/>api.py"] --> SV

    APP --> SV["service.py<br/>shared logic"]
    DASH --> SV

    SV --> IN["inputs.py<br/>validate form"]
    SV --> FE["features.py<br/>shared feature engineering"]
    SV --> MD[("models/logistic.joblib")]
    SV --> EX["explain.py<br/>per-applicant factors"]
    SV --> WI["whatif.py<br/>what-if and suggestions"]
    SV --> GD["guidance.py<br/>checklist and bands"]
    SV --> LL["llm.py<br/>explanation layer"]
    SV --> ST[("dashboard_stats.json<br/>metrics.json")]

    LL --> GQ["Groq API"]
    LL --> TP["templates.py<br/>offline English / Hindi"]
```

| Layer | Files | Role |
|---|---|---|
| Presentation | `app.py`, `pages/1_Lender_Dashboard.py`, `theme.py` | Streamlit UI, Paytm-inspired navy and sky-blue theme |
| API | `api.py` | Thin REST wrapper: `/api/health`, `/api/metrics`, `/api/predict`, `/api/whatif`, `/api/dashboard/summary` |
| Service | `service.py` | `predict_applicant`, `whatif_applicant`, `dashboard_summary` |
| Domain | `inputs.py`, `features.py`, `explain.py`, `whatif.py`, `guidance.py`, `rules.py` | Validation, features, explanation, what-if, checklist, tree rules |
| LLM | `llm.py`, `templates.py` | Grounded rewrite with validation and offline fallback |
| Artifacts | `models/` | Saved models, metrics, dashboard statistics, score rule |
| Training | `finsight_training.ipynb` | Colab notebook that produces everything in `models/` |

## 2. Two workflows

### 2.1 Offline: training (Colab)

Training is done in Google Colab because the laptop is a modest machine (8 GB RAM). The app only loads the saved models.

```mermaid
flowchart LR
    CSV["Synthetic CSV<br/>100,000 rows"] --> CHK["Checks vs<br/>data card"]
    CHK --> FEAT["features.py<br/>18 model inputs"]
    FEAT --> SPLIT["Use provided split<br/>train / val / test"]
    SPLIT --> TRAIN["Train 3 models<br/>logistic, tree, boosting"]
    TRAIN --> TUNE["Tune with 3-fold CV<br/>on train only"]
    TUNE --> VAL["Compare on val"]
    VAL --> TEST["Test set<br/>evaluated once"]
    TEST --> OUT["models/*.joblib<br/>metrics.json"]
    FEAT --> STATS["dashboard_stats.json<br/>segments, importance, rules, fairness"]
    CSV --> RULE["score_rule.json<br/>card usage vs CIBIL score"]
```

Discipline kept: the test set is touched once, after tuning, and the ship decision rule (boosting must beat logistic by 0.02 AUC) was fixed before seeing the 100k results.

### 2.2 Online: a borrower request

```mermaid
sequenceDiagram
    participant U as Borrower
    participant UI as Streamlit app
    participant SV as service.py
    participant ML as Logistic model
    participant LL as Groq / template

    U->>UI: Fill form, click "Check my chances"
    UI->>SV: predict_applicant(form, language)
    SV->>SV: Validate inputs, map documents to 0/1
    SV->>ML: Compute features, get probability
    SV->>SV: Factors, suggested steps, checklist
    SV->>LL: Structured payload only (no names, no contact data)
    LL-->>SV: Summary and steps, or built-in fallback
    SV-->>UI: Result
    U->>UI: Move a what-if slider
    UI->>SV: whatif_applicant(applicant, changes)
    SV->>ML: Recompute features, new probability
    SV-->>UI: Old and new estimate
```

### 2.3 Deployment

```mermaid
flowchart LR
    DEV["Local project"] --> GIT["GitHub repo<br/>finsight-ai"]
    GIT --> CLOUD["Streamlit Community Cloud<br/>app.py"]
    SEC["Secrets (TOML)<br/>GROQ_API_KEY"] --> CLOUD
```

The key lives only in the Streamlit Secrets box and the local `.env`. Both are kept out of the repository.

## 3. Key components

### Feature engineering (`features.py`)
- One function for training **and** serving, so there is no drift.
- Recomputes `foir_current`, `foir_post_loan` and `loan_to_monthly_income` from raw inputs. The interest rate depends on the CIBIL tier: 19 / 15.5 / 13 / 11.5 / 10.75, and 17 for new-to-credit.
- Model inputs: 17 numeric features plus employment type (18 in all). `gender`, `city_tier` and `age` are never inputs, and the training notebook asserts it.

### Model
- Pipeline: median imputation, scaling and one-hot encoding, then logistic regression.
- The same coefficients give the probability, the factor explanations and the what-if.

### Explanations (`explain.py`)
- Contribution = coefficient x scaled value (log-odds push relative to an average applicant).
- The three correlated EMI ratio features are merged into one factor.
- Factors with almost no effect are hidden. New-to-credit applicants never see CIBIL-based factors, because their values are imputed.

### What-if and suggestions (`whatif.py`)
- Copies the applicant, applies the changes, recomputes features and the probability.
- Suggestions search **actionable** features only: card usage, existing EMIs, loan amount, tenure (capped so the loan ends before age 60) and documents.
- A small linear rule (`score_rule.json`) estimates how the CIBIL score moves when card usage changes. It is an assumption fitted on synthetic data and is labelled as such.

### LLM layer (`llm.py`)
- Sees only the structured payload and decides nothing.
- Output is validated: right shape, no promise of approval, and every number must exist in the payload. Failures fall back to `templates.py`.
- Reasons are generated by code. The LLM writes only the summary and next steps.
- Timeouts: 12 s for English, 25 s for Hindi.

### Lender dashboard
- Reads precomputed statistics, so it is fast and works offline.
- Every sentence under a chart is filled in by code from the numbers. The page shows the data-source label and the fairness caveat.

## 4. Design decisions

| Decision | Why |
|---|---|
| Train in Colab, run locally | 8 GB laptop. The saved pipeline contains the preprocessing, so the app needs no separate scaler |
| Ship logistic regression | Boosting gained only 0.0154 AUC, and logistic is explainable end to end |
| Streamlit UI plus thin Flask API | A Flask website with templates and CSS was too heavy for the time. The deck still names Flask + REST, and the API exists |
| Streamlit calls `service.py` directly | One process for the demo, so a stopped API cannot break the screens |
| Template fallback | The demo must work with weak or no internet |
| Reasons built by code | A small free LLM drops factors and mixes languages. Code keeps them exact |
| Pinned scikit-learn 1.6.1 | Pickled models can break across versions |
| Estimates, never decisions | Guardrail, repeated on every page |

## 5. Guardrails

- No fabricated numbers, and synthetic data is always labelled.
- Sensitive attributes are audited on the dashboard but never used by the model.
- No applicant data is stored or logged. Inputs live only in the browser session.
- The LLM sees only the structured payload, and its output is validated.
- Everything important works offline.