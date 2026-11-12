import re
import pandas as pd
import streamlit as st
import plotly.graph_objects as go
from service import dashboard_summary
from explain import LABELS
import theme
from rules import leaf_rules

st.set_page_config(page_title="FinSight AI - Lender view", page_icon="💙", layout="wide")
st.markdown(theme.CSS, unsafe_allow_html=True)
st.markdown('<div class="topbar"><b>FinSight <span>AI</span> · Lender view</b>'
            '<div>What drives approvals and rejections</div></div>', unsafe_allow_html=True)


@st.cache_data
def load():
    return dashboard_summary()


D = load()
S, M = D["stats"], D["metrics"]
LABELS["employment_type"] = "Employment type"


def inference(text):
    st.markdown(f'<div class="note">{text}</div>', unsafe_allow_html=True)


def style(fig, h=340):
    fig.update_layout(**theme.plotly_layout(), height=h)
    return fig


# ---------- header ----------
st.markdown(f'<div class="note"><b>Data source:</b> {D["data_source"]}. '
            'Results describe this synthetic data, not real lending.</div>', unsafe_allow_html=True)
k1, k2, k3 = st.columns(3)
k1.metric("Applications analysed", f"{S['rows_used']:,}")
k2.metric("Overall approval rate", f"{S['overall_approval_rate'] * 100:.1f}%")
k3.metric("Model in use", M["shipped_model"])

# ---------- 1. approval by segment ----------
st.subheader("Approval vs rejection by segment")
NAMES = {"income_band": "Income band (Rs/month)", "cibil_tier": "CIBIL tier",
         "employment_type": "Employment type", "foir_bucket": "EMI burden after loan (FOIR)",
         "city_tier": "City tier", "age_band": "Age band"}
ORDER = {"cibil_tier": ["Subprime", "Near prime", "Prime", "Prime plus", "Super prime", "New-to-credit"]}

tabs = st.tabs(list(NAMES.values()))
for tab, col in zip(tabs, NAMES):
    with tab:
        d = S["segments"][col]
        keys = [k for k in ORDER[col] if k in d] if col in ORDER else list(d)
        rates = [d[k]["approval_rate"] for k in keys]
        ns = [d[k]["n"] for k in keys]
        fig = go.Figure()
        fig.add_bar(x=keys, y=rates, name="Approved", marker_color=theme.SKY,
                    text=[f"{r:.0%}" for r in rates], textposition="inside")
        fig.add_bar(x=keys, y=[1 - r for r in rates], name="Rejected", marker_color=theme.NAVY)
        fig.update_layout(barmode="stack", yaxis_tickformat=".0%", title=NAMES[col])
        st.plotly_chart(style(fig), width="stretch")
        hi, lo = max(range(len(keys)), key=lambda i: rates[i]), min(range(len(keys)), key=lambda i: rates[i])
        inference(f"Approval is highest for <b>{keys[hi]}</b> ({rates[hi]:.0%}, n={ns[hi]:,}) and lowest for "
                  f"<b>{keys[lo]}</b> ({rates[lo]:.0%}, n={ns[lo]:,}), a gap of {(rates[hi] - rates[lo]) * 100:.0f} points.")

# ---------- 2. importance ----------
st.subheader("What drives the decision (permutation importance)")
imp = sorted(S["permutation_importance"].items(), key=lambda kv: -kv[1])[:10]
names = [LABELS.get(k, k) for k, _ in imp][::-1]
vals = [v for _, v in imp][::-1]
fig = go.Figure(go.Bar(x=vals, y=names, orientation="h", marker_color=theme.NAVY))
fig.update_layout(title="Drop in test AUC when a feature is shuffled")
st.plotly_chart(style(fig, 380), width="stretch")
top = imp[:3]
inference(f"Shuffling <b>{LABELS.get(top[0][0], top[0][0])}</b> lowers AUC by {top[0][1]:.3f}, the most of any feature, "
          f"followed by {LABELS.get(top[1][0], top[1][0])} ({top[1][1]:.3f}) and "
          f"{LABELS.get(top[2][0], top[2][0])} ({top[2][1]:.3f}).")

# ---------- 3. rejection reasons ----------
st.subheader("Primary rejection reasons")
rr = sorted(S["rejection_reasons"].items(), key=lambda kv: -kv[1])
fig = go.Figure(go.Bar(x=[v for _, v in rr][::-1], y=[k for k, _ in rr][::-1],
                       orientation="h", marker_color=theme.SKY,
                       text=[f"{v:.0%}" for _, v in rr][::-1], textposition="outside"))
fig.update_layout(title="Share of rejected applications", xaxis_tickformat=".0%")
st.plotly_chart(style(fig, 380), width="stretch")
inference(f"<b>{rr[0][0]}</b> is the main reason for {rr[0][1]:.0%} of rejections; the top three reasons together "
          f"account for {sum(v for _, v in rr[:3]):.0%}.")

# ---------- 4. tree rules ----------
st.subheader("Plain-language rules from a small decision tree")
rules = S["tree_rules_text"]
feats = []
for f in re.findall(r"\|--- (\w+) [<>]", rules):
    if f not in feats:
        feats.append(f)
first = re.search(r"\|--- (\w+) <= ([\d.]+)", rules)
inference(f"The tree splits first on <b>{LABELS.get(first.group(1), first.group(1))}</b> at {first.group(2)}, then uses "
          + ", ".join(LABELS.get(f, f) for f in feats[1:5]) + ".")

best, worst = leaf_rules()
r1, r2 = st.columns(2)
with r1:
    st.markdown("**Groups with the highest approval**")
    for s, rate, n in best:
        st.markdown(f"- {s} (n={n:,})")
with r2:
    st.markdown("**Groups with the lowest approval**")
    for s, rate, n in worst:
        st.markdown(f"- {s} (n={n:,})")
with st.expander("Show the raw tree (top 3 levels)"):
    st.code(rules)

# ---------- 5. fairness ----------
st.subheader("Fairness check")
st.markdown('<div class="note"><b>Read this first:</b> gender was generated independently of every other field, so a '
            'near-zero gender gap is <b>by construction</b>, not proof of fairness. City and age gaps arise through '
            'income and credit history. A gap is a prompt to investigate, not proof of bias.</div>',
            unsafe_allow_html=True)
rows, f1 = [], st.columns(3)
for c, (grp, label) in zip(f1, [("gender", "Gender"), ("city_tier", "City tier"), ("age_band", "Age band")]):
    d = S["fairness"][grp]
    ks, rs = list(d), [d[k]["approval_rate"] for k in d]
    gap = max(rs) - min(rs)
    for k in ks:
        rows.append({"Group": label, "Segment": k, "Approval rate": f"{d[k]['approval_rate']:.1%}", "n": f"{d[k]['n']:,}"})
    with c:
        fig = go.Figure(go.Bar(x=ks, y=rs, marker_color=theme.WARN if gap >= 0.10 else theme.SKY,
                               text=[f"{r:.0%}" for r in rs], textposition="outside"))
        fig.update_layout(title=label, yaxis_tickformat=".0%", yaxis_range=[0, 1])
        st.plotly_chart(style(fig, 300), width="stretch")
        inference(f"{label}: approval ranges from {min(rs):.0%} to {max(rs):.0%}, a gap of {gap * 100:.0f} points.")
st.dataframe(pd.DataFrame(rows), hide_index=True, width="stretch")

# ---------- 6. model quality ----------
st.subheader("Model performance (test set, synthetic data)")
mt = pd.DataFrame([{"Model": k, "Test AUC": v["roc_auc_test"], "Train-test gap": v["train_test_gap"],
                    "Accuracy": v["accuracy"], "Brier": v["brier"]} for k, v in M["models"].items()])
st.dataframe(mt, hide_index=True, width="stretch")
inference(f"Boosting scores {M['boosting_auc_gain_over_logistic']:.3f} AUC above logistic regression, so we ship "
          f"<b>{M['shipped_model']}</b> because it is explainable. These numbers describe synthetic data, "
          "not real-world performance.")

st.markdown('<div class="disclaimer">Estimate only - not financial advice or a lending decision.</div>',
            unsafe_allow_html=True)