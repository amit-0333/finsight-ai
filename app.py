import os
import streamlit as st
import plotly.graph_objects as go
from service import predict_applicant, whatif_applicant
from explain import inr
from templates import LABELS_HI
import theme

st.set_page_config(page_title="FinSight AI", page_icon="💙", layout="wide")
st.markdown(theme.CSS, unsafe_allow_html=True)
st.markdown('<div class="topbar"><b>FinSight <span>AI</span></b>'
            '<div>Know why. Fix it. Get approved.</div></div>', unsafe_allow_html=True)
st.session_state.setdefault("rid", 0)

# ---------------- sidebar ----------------
with st.sidebar:
    st.header("Settings")
    lang_label = st.radio("Language / भाषा", ["English", "हिन्दी"])
    language = "hi" if lang_label == "हिन्दी" else "en"
    has_key = bool(os.getenv("GROQ_API_KEY"))
    use_llm = st.toggle("AI wording (Groq)", value=has_key, disabled=not has_key)
    st.caption("If off or offline, built-in wording is used. Press the button again after changing language.")

# ---------------- form ----------------
st.subheader("Your details")
c1, c2, c3 = st.columns(3)

with c1:
    with st.container(border=True):
        st.markdown("##### 👤 About you")
        age = st.number_input("Age", 21, 62, 30)
        employment_type = st.selectbox("Job type", ["salaried", "self_employed"],
                                       format_func=lambda x: "Salaried" if x == "salaried" else "Self-employed")
        monthly_income = st.number_input("Monthly income (Rs)", 5000, 5_000_000, 30000, step=1000)
        st.caption(inr(monthly_income))
        employment_years = st.number_input("Years in current job/business", 0.0, 50.0, 3.0, step=0.5)
        residence_years = st.number_input("Years at current residence", 0.0, 50.0, 2.0, step=0.5)

with c2:
    with st.container(border=True):
        st.markdown("##### 💳 Credit profile")
        no_hist = st.checkbox("I have no credit history")
        if no_hist:
            st.info("No problem. We will estimate without a CIBIL score.")
            cibil, credit_age, util, enquiries, missed = None, None, None, 0, 0
        else:
            cibil = st.number_input("CIBIL score (300-900)", 300, 900, 720)
            credit_age = st.number_input("Credit history length (years)", 0.0, 40.0, 4.0, step=0.5)
            util = st.slider("Credit card usage (% of limit)", 0, 100, 30)
            enquiries = st.number_input("Loan enquiries in last 6 months", 0, 20, 1)
            missed = st.number_input("Missed payments in last 12 months", 0, 12, 0)
        loans = st.number_input("Number of existing loans", 0, 10, 0)
        emi = st.number_input("Existing monthly EMIs (Rs)", 0, 500_000, 0, step=500)

with c3:
    with st.container(border=True):
        st.markdown("##### 🏦 Loan you want")
        amount = st.number_input("Loan amount needed (Rs)", 10_000, 10_000_000, 150_000, step=5000)
        st.caption(inr(amount))
        tenure = st.slider("Loan tenure (months)", 6, 84, 36, step=6)
        st.markdown("**Documents you have ready**")
        d_id = st.checkbox("ID proof (Aadhaar / PAN)", True)
        d_addr = st.checkbox("Address proof", True)
        d_inc = st.checkbox("Income proof (salary slips / ITR)", True)
        d_bank = st.checkbox("Last 6 months bank statements", True)

# ---------------- submit ----------------
st.markdown("---")
st.markdown("##### 👇 Fill in your details above, then click:")

if st.button("Check my chances", type="primary"):
    form = {
        "age": age, "employment_type": employment_type, "monthly_income": monthly_income,
        "employment_years": employment_years, "residence_years": residence_years,
        "no_credit_history": no_hist, "cibil_score": cibil, "credit_age_years": credit_age,
        "credit_utilisation_pct": util, "recent_enquiries_6m": enquiries,
        "missed_payments_12m": missed, "existing_loans_count": loans, "existing_emi_monthly": emi,
        "loan_amount_requested": amount, "loan_tenure_months": tenure,
        "docs": {"id": d_id, "address": d_addr, "income": d_inc, "bank": d_bank},
    }
    with st.spinner("Calculating..."):
        out = predict_applicant(form, language=language, use_llm=use_llm)
    if "errors" in out:
        for e in out["errors"]:
            st.error(e)
        st.session_state.pop("result", None)
    else:
        st.session_state["result"] = out
        st.session_state["rid"] += 1

# ---------------- result ----------------
res = st.session_state.get("result")
if res:
    st.divider()
    st.subheader("Your estimate")
    color = theme.BAND_COLOR[res["band"]]
    g, t = st.columns([1, 2])
    with g:
        fig = go.Figure(go.Indicator(
            mode="gauge+number", value=res["approval_percent"], number={"suffix": "%"},
            gauge={"axis": {"range": [0, 100]}, "bar": {"color": color}, "bgcolor": "#E8F7FE"}))
        fig.update_layout(height=230, margin=dict(l=20, r=20, t=20, b=10), paper_bgcolor="rgba(0,0,0,0)")
        st.plotly_chart(fig, width="stretch")
        st.markdown(f'<span class="pill" style="background:{color}">{res["band"]}</span>',
                    unsafe_allow_html=True)
    with t:
        ex = res["explanation"]
        st.markdown(f'<div class="card"><b>{ex["summary"]}</b></div>', unsafe_allow_html=True)
        st.markdown("**Why**")
        for r in ex["reasons"]:
            st.markdown(f"- {r}")
        st.markdown("**What you can do**")
        for s in ex["next_steps"]:
            st.markdown(f"- {s}")
        st.caption("Wording by AI (Groq)" if ex["source"] == "groq" else "Built-in wording (offline-safe)")

    def factor_line(f):
        if res.get("language") == "hi":
            return f"- {LABELS_HI.get(f['feature'], f['label'])}: {f['value_hi']}"
        return f"- {f['label']}: {f['value']}"

    h, p = st.columns(2)
    with h:
        st.markdown("**Hurting your chances**")
        st.caption("Compared with a typical applicant in our synthetic data.")
        if res["factors_hurting"]:
            for f in res["factors_hurting"]:
                st.markdown(factor_line(f))
        else:
            st.caption("No strong factors.")
    with p:
        st.markdown("**Helping your chances**")
        st.caption("Compared with a typical applicant in our synthetic data.")
        if res["factors_helping"]:
            for f in res["factors_helping"]:
                st.markdown(factor_line(f))
        else:
            st.caption("No strong factors.")

    st.markdown("**Suggested steps and their estimated effect**")
    if res["suggested_actions"]:
        for a in res["suggested_actions"]:
            st.markdown(f"- {a['change']} → about **{a['new_probability'] * 100:.0f}%**")
        if res["if_all_done"] is not None:
            msg = f"All of these together: about **{res['if_all_done'] * 100:.0f}%**."
            if res["if_all_done"] < 0.60:
                msg += " These steps help but may not be enough yet."
            st.markdown(msg)
    else:
        st.caption("No single change makes a clear difference.")

    with st.expander("Document checklist", expanded=True):
        for item in res["checklist"]:
            st.markdown(f"- {item}")

    # ---------------- what-if ----------------
    st.divider()
    st.subheader("What if...?")
    a, rid = res["applicant"], st.session_state["rid"]
    changes = {}
    w1, w2 = st.columns(2)
    with w1:
        if a["is_new_to_credit"] == 0:
            changes["credit_utilisation_pct"] = st.slider(
                "Credit card usage (%)", 0, 100, int(round(a["credit_utilisation_pct"])), key=f"u{rid}")
        else:
            st.caption("Credit card usage does not apply without credit history.")
        changes["loan_amount_requested"] = st.slider(
            "Loan amount (Rs)", 10_000, int(max(a["loan_amount_requested"] * 1.5, 50_000)),
            int(a["loan_amount_requested"]), step=5000, key=f"a{rid}")
        st.caption(inr(changes["loan_amount_requested"]))
    with w2:
        max_ten = int(min(84, max(6, (60 - res["age"]) * 12)))
        changes["loan_tenure_months"] = st.slider(
            "Tenure (months)", 6, max_ten, min(int(a["loan_tenure_months"]), max_ten), step=6, key=f"t{rid}")
        if a["existing_emi_monthly"] > 0:
            new_emi = st.slider("Existing monthly EMIs (Rs)", 0, int(a["existing_emi_monthly"]),
                                int(a["existing_emi_monthly"]), step=500, key=f"e{rid}")
            changes["existing_emi_monthly"] = new_emi
            changes["existing_loans_count"] = max(
                0, round(a["existing_loans_count"] * new_emi / a["existing_emi_monthly"]))
        changes["documents_complete"] = 1 if st.toggle(
            "All documents ready", value=bool(a["documents_complete"]), key=f"d{rid}") else 0

    wi = whatif_applicant(a, changes)
    m1, m2 = st.columns(2)
    m1.metric("Current estimate", f"{wi['old_probability'] * 100:.1f}%")
    m2.metric("With these changes", f"{wi['new_probability'] * 100:.1f}%",
              f"{wi['change'] * 100:+.1f} points")
    st.markdown(f'<div class="note">{wi["note"]}</div>', unsafe_allow_html=True)

st.markdown('<div class="disclaimer">Estimate only - not financial advice or a lending decision.</div>',
            unsafe_allow_html=True)