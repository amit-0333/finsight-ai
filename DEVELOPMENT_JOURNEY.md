# Development journey

How FinSight AI was built, phase by phase: what we did, what went wrong, and how we fixed it. See the [README](../README.md) for results and [ARCHITECTURE](ARCHITECTURE.md) for the design.

> All data is **synthetic**. Numbers quoted here come from runs that actually happened.

## Timeline at a glance

| Phase | Where | Outcome |
|---|---|---|
| 0 | Planning | Plan, tools and environment agreed |
| 1 | Colab | Data checks, EDA, shared `features.py` |
| 2 | Colab | Three models tuned and evaluated, logistic shipped |
| 3 | Laptop | Explanations, what-if, suggestions, checklist |
| 4 | Laptop | Groq layer with English / Hindi offline fallback |
| 5 | Laptop | `service.py` and the Flask API |
| 6 | Laptop | Streamlit borrower page |
| 7 | Laptop | Lender dashboard |
| 8 | Cloud | GitHub and Streamlit Community Cloud deployment |

---

## Phase 0: Planning and setup

**Goal:** agree what to build, with what, and where.

**Decisions**
- Laptop has 8 GB RAM, so **analysis and training run in Colab**. The models are saved as `.joblib` and only loaded locally.
- **Streamlit** for the UI, with a **thin Flask REST API** so the "Flask + REST" claim in the deck stays true.
- **Groq** as the LLM, with short prompts, and an offline template fallback.

| Problem | How it was solved |
|---|---|
| A Flask website with templates, CSS and JavaScript was too heavy for the time | Streamlit for the UI, Flask only for a small JSON API over the same `service.py` |
| A model pickled on Colab can fail on a different library version | Printed Colab's versions (pandas 2.2.3, numpy 2.4.6, scikit-learn 1.6.1) and pinned them in `requirements.txt` |
| Two datasets (20k sample and 100k) | 20k only for quick debugging, 100k for every reported number. The two files were never combined |

## Phase 1: Data checks, EDA and shared features (Colab)

**Goal:** trust the data, and build one feature function for training and serving.

**What we did:** checked shape, approval rate, split sizes and missing values against the data card, recomputed the engineered columns, looked at approval by segment, and checked correlations.

| Problem | How it was solved |
|---|---|
| Recomputed `foir_post_loan` differed from the CSV by up to 0.042, and 19,886 rows had a different interest rate | The CSV's rate has a random +/-0.75 jitter around each tier's base rate. The model trains on our own `make_features` output, so training and serving use the same formula and cannot drift. Only 41 of 20,000 rows differed by more than 0.01, all with FOIR above 1 |
| Correlated features (highest 0.82: existing loans with current EMI burden; 0.76: employment years with credit age) could distort coefficients | Kept the features (moderate correlation) and later merged the three EMI ratios into one displayed factor |
| New-to-credit applicants have empty credit fields | Median imputation plus the `is_new_to_credit` flag, and a rule that imputed values are never shown to the user |

## Phase 2: Model training and evaluation (Colab)

**Goal:** three models, honest metrics, and a defensible choice.

**What we did:** logistic regression, a depth-5 decision tree and gradient boosting in pipelines. Tuned with 3-fold cross-validation on the training set only. Evaluated on the test set once. Ran a feature-group test.

| Problem | How it was solved |
|---|---|
| Which boosting library? | Tried XGBoost on validation: 0.8946 against 0.892 for scikit-learn's boosting. A 0.003 difference is noise, so we stayed inside scikit-learn (no extra install, no pickle risk) |
| First run on the 20k sample looked worrying: boosting overfit (train-test gap 0.041) and logistic was under-confident in the mid-range (predicted 0.35, observed 0.43) | Tuned boosting, then re-ran on the full 100k. The gap fell to 0.007 and calibration agreed within about 0.03 in every decile. The 20k problems were small-sample noise. A calibration layer was tried and gave no real gain (Brier 0.1456 to 0.1455), so it is saved but unused |
| Temptation to pick the best-looking model after seeing results | Fixed the rule **before** the 100k run: ship logistic unless boosting beats it by 0.02 AUC. The gain was 0.0154, so logistic shipped |
| Notebook became messy and confusing (which cell, which dataset) | Rewrote it as 10 clean cells with a single `USE_FULL` switch |
| `pkg/models` not found when verifying the saved model | The saving cell had not run in that session. Ran it, then reloaded the model and confirmed the same test AUC (0.8712) |
| Was feature selection actually done? | No, honestly. Added a feature-group test: removing credit lost 0.0919 AUC, documents 0.0113, income and loan 0.0071, ratios 0.0024, employment 0.0007. All groups help, so all 18 features stay |

**Final result (100k, test set of 15,001 rows):** logistic AUC 0.8712, tree 0.8578, boosting 0.8866.

## Phase 3: Explainability, what-if and guidance (laptop)

**Goal:** turn the model into something a borrower can understand and act on.

| Problem | How it was solved |
|---|---|
| The factor list said "Loan size 10x monthly income **improves** your chances" | The three EMI ratios are correlated, so the model split one effect across them with mixed signs. They are now merged into one factor, "EMI burden and loan size vs income" |
| Near-zero factors (for example +0.011) were shown as "helping" | Added a minimum effect of 0.05 |
| "New to credit: No" as a reason was useless | Skipped for applicants with credit history |
| Credit values for new-to-credit applicants would be imputed medians | Credit factors are hidden for them, and credit sliders are ignored in the what-if |
| Suggestions must be realistic | Search only actionable features, cap tenure so the loan ends before age 60, and never suggest age, history or past missed payments |
| The card-usage what-if barely moved the estimate (85% to 30% gave about +2 points) because the CIBIL score was held fixed | Fitted a small linear helper on synthetic data (`score_rule.json`) that estimates the score change. In a test, 85% to 30% moved the estimate from 39.1% to 72.8%. The UI labels it "an assumption based on synthetic data, not a real bureau rule" |
| The form needs raw inputs, not model columns | Added `inputs.py`: validation, document checkboxes mapped to `documents_complete`, and `age` used only for the tenure limit |

## Phase 4: LLM layer (laptop)

**Goal:** plain-language wording that cannot invent facts, and that works offline.

| Problem | How it was solved |
|---|---|
| Groq JSON mode returned `json_validate_failed` with an empty generation | Dropped JSON mode and used a plain line format (`SUMMARY:` / `REASON:` / `STEP:`) |
| The small model produced broken JSON in English and no JSON in Hindi | The line format is much harder to break |
| Hindi replies timed out at 10 s | Longer timeout (25 s) and a larger token limit for Hindi |
| The reasoning model (`gpt-oss-20b`) spent its tokens thinking and returned little | Set low reasoning effort and a bigger token limit |
| The LLM merged reasons, dropped factors, and wrote English labels in Hindi mode | **Design change:** reasons are generated by code. The LLM writes only the summary and next steps |
| Hindi text mixed in English values ("Incomplete", "55% of income") | Added a Hindi formatter and Hindi label and effect text in the payload |
| LLM could invent numbers or promise approval | Validation: right shape, banned phrases, and every number must appear in the payload. Failures fall back to the template |

**Takeaway:** a free small model is fine for polishing wording, not for facts. The facts come from code.

## Phase 5: Service layer and Flask API (laptop)

**Goal:** one logic layer, two front doors.

| Problem | How it was solved |
|---|---|
| Opening `/` or `/api/` in the browser showed `NotFound` | Expected, since those routes did not exist. Added `/` and `/api/` endpoint listings and `/api/metrics` |
| The error handler reported a 404 as a 500 | Handle HTTP exceptions with their real status codes. Errors never echo applicant data |
| Offline test printed a long `ConnectionResetError` | Harmless Windows asyncio noise from a connection closing abruptly. Not a bug |

## Phase 6: Streamlit borrower page (laptop)

**Goal:** form, result, factors, steps, checklist and live what-if.

| Problem | How it was solved |
|---|---|
| The top bar was cut off | Increased the page's top padding |
| "Where is the submit button?" | It was below the three cards. Made it larger. A later patch deleted it by accident, and it was restored |
| CSS text appeared on the page | A line was pasted below `</style>`. Moved it inside the style block |
| The what-if felt flat for card usage | See Phase 3 (score estimate) |
| The "hurting" list showed income and job years, which the user cannot change | Added "Compared with a typical applicant in our synthetic data" so it is read as relative, not absolute |
| Theme | Palette taken from the logo (navy and sky blue) via `theme.py` and `.streamlit/config.toml`. No Paytm logo or name on our pages |

## Phase 7: Lender dashboard (laptop)

**Goal:** analyst view with computed sentences, fairness caveat and data-source label.

| Problem | How it was solved |
|---|---|
| Decision-tree rules were repeated and unreadable ("CIBIL score at or below 750.5 and at or below 694.5 and ...") | Merged repeated limits to the tightest one and wrote counts in plain words ("no missed payments in the last 12 months") |
| After the fix the page still showed the old rules | A stray line at the end of `rules.py` and a stale Streamlit process. Removed the line, restarted Streamlit, hard-refreshed |
| Dashboard only showed a sentence about the tree | Added highest and lowest approval groups as sentences |
| Fairness could be misread | The caveat is shown above the charts: the gender gap is zero **by construction**, and city and age gaps (0.157 and 0.456) are prompts to investigate |

## Phase 8: GitHub and Streamlit Cloud deployment

**Goal:** a public link, with the key kept secret.

| Problem | How it was solved |
|---|---|
| GitHub push protection blocked the push because `.env` (with the Groq key) was in the commit | The key never reached GitHub. Created `.gitignore`, removed `.env`, `.venv` and caches from the commit, amended it, and pushed |
| Commands were pasted into `.gitignore` instead of the terminal | Cleaned the file to the four ignore lines |
| The default Streamlit subdomain was taken | Chose a different app URL |
| The Secrets box showed "Invalid format: please enter valid TOML" and the AI toggle was disabled | Secrets must be TOML with values in quotes (`KEY = "value"`). The app disables the AI toggle when no key is found, which is how we spotted it |
| Needed to check that the notebook did not affect the app | It is only stored in the repo. Pushes trigger an automatic redeploy |
| Weak internet at a finale | Verified the borrower page, what-if, dashboard and API with Wi-Fi off |

## What we would do next

- Real, consented lender data with proper fairness testing.
- A stronger LLM, and a proper Hindi evaluation.
- A learned relationship between credit behaviour and score changes, instead of the synthetic-data assumption.
- Translate the remaining English form labels.

## Lessons

1. **Fix the decision rule before seeing the result.** It kept the model choice honest.
2. **Trust the full data, not the sample.** The 20k run raised alarms that disappeared on 100k.
3. **Don't let a small LLM state facts.** Code builds the facts, and the LLM only rewords.
4. **One feature function for training and serving.** It removes a whole class of bugs.
5. **Label assumptions in the UI.** Judges trust a clearly marked assumption more than a hidden one.