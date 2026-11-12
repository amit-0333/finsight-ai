import math
import joblib
from pathlib import Path
from explain import LABELS, inr

BASE = Path(__file__).parent
MONEY = {"monthly_income", "existing_emi_monthly", "loan_amount_requested"}
RATIO = {"foir_current", "foir_post_loan"}
WHOLE = {"cibil_score", "missed_payments_12m", "recent_enquiries_6m", "existing_loans_count",
         "loan_tenure_months"}


def _val(f, x):
    if f in MONEY:
        return inr(x)
    if f in RATIO:
        return f"{x * 100:.0f}% of income"
    return f"{x:.1f}"


def _text(f, lo, hi):
    """lo = value must be above lo, hi = value must be at or below hi."""
    if f == "documents_complete":
        return "documents are complete" if lo is not None else "documents are incomplete"
    if f == "is_new_to_credit":
        return "new to credit" if lo is not None else "has credit history"
    if f.startswith("employment_type_"):
        kind = "salaried" if f.endswith("salaried") else "self-employed"
        return kind if lo is not None else "not " + kind

    label = LABELS.get(f, f)
    if f in WHOLE:
        a = None if lo is None else math.floor(lo) + 1      # "above 694.5" means 695 or more
        b = None if hi is None else math.floor(hi)
        if f == "missed_payments_12m":
            if b == 0:
                return "no missed payments in the last 12 months"
            if a is not None and b is None:
                return f"{a} or more missed payments in the last 12 months"
        if a is not None and b is not None:
            return f"{label} between {a} and {b}"
        return f"{label} {a} or more" if a is not None else f"{label} {b} or less"

    if lo is not None and hi is not None:
        return f"{label} between {_val(f, lo)} and {_val(f, hi)}"
    if lo is not None:
        return f"{label} above {_val(f, lo)}"
    return f"{label} at or below {_val(f, hi)}"


def _merge(path):
    """path = [(feature, op, threshold)] -> one sentence part per feature, tightest limits only."""
    order, lo, hi = [], {}, {}
    for f, op, thr in path:
        if f not in order:
            order.append(f)
        if op == ">":
            lo[f] = max(lo.get(f, thr), thr)
        else:
            hi[f] = min(hi.get(f, thr), thr)
    return [_text(f, lo.get(f), hi.get(f)) for f in order]


def leaf_rules(top=3, min_n=500):
    """Returns (most_approved, least_approved): lists of (sentence, approval_rate, n)."""
    pipe = joblib.load(BASE / "models" / "tree.joblib")
    names = [n.split("__", 1)[1] for n in pipe.named_steps["prep"].get_feature_names_out()]
    t = pipe.named_steps["model"].tree_
    leaves = []

    def walk(node, path):
        if t.children_left[node] == -1:
            v = t.value[node][0]
            leaves.append((int(t.n_node_samples[node]), float(v[1] / v.sum()), path))
            return
        f, thr = names[t.feature[node]], float(t.threshold[node])
        walk(t.children_left[node], path + [(f, "<=", thr)])
        walk(t.children_right[node], path + [(f, ">", thr)])

    walk(0, [])
    leaves = [x for x in leaves if x[0] >= min_n]
    fmt = lambda x: ("If " + ", ".join(_merge(x[2])) + f": about {x[1]:.0%} were approved", x[1], x[0])
    best = [fmt(x) for x in sorted(leaves, key=lambda x: -x[1])[:top]]
    worst = [fmt(x) for x in sorted(leaves, key=lambda x: x[1])[:top]]
    return best, worst