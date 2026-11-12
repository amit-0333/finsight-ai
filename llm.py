import json, os, re
from dotenv import load_dotenv
from common import prob
from explain import explain
from whatif import suggest_actions
from guidance import band, checklist
from templates import template_explanation, LABELS_HI

load_dotenv()
MODEL = os.getenv("GROQ_MODEL", "llama-3.1-8b-instant")
BANNED = re.compile(r"will be approved|guarantee|definitely|certainly", re.I)

SYSTEM = ("You rewrite a loan-estimate result for an Indian borrower in simple, kind, jargon-free language. "
          "Use ONLY the facts in the JSON. Do not invent reasons, numbers or promises. "
          "Never say the loan will be approved. Copy numbers exactly as given, using digits 0-9. "
          "Write in Hindi (Devanagari) if language is 'hi', else English. In Hindi, write every word in Hindi; "
          "keep only numbers, Rs, CIBIL and EMI as they are. "
          "Reply in exactly this plain-text format. Keep the English labels SUMMARY:, REASON:, STEP:. "
          "One item per line, no other text.\n"
          "SUMMARY: <2 short sentences>\n"
          "REASON: <exactly one factor per line, never combine factors>\n"
          "STEP: <one next step per line, 2 to 3 lines>")


def build_payload(applicant, age=None, language="en"):
    p = prob(applicant)
    ex, sa = explain(applicant), suggest_actions(applicant, age=age)
    hi = language == "hi"

    def factor(r):
        effect = r["effect"]
        if hi:
            effect = "आपकी संभावना घटाता है" if "lowers" in effect else "आपकी संभावना बढ़ाता है"
        return {"key": r["feature"],
                "feature": LABELS_HI.get(r["feature"], r["label"]) if hi else r["label"],
                "value": r["value_hi"] if hi else r["value"],
                "effect": effect}

    def action(a):
        k = list(a["changes"])[0]
        return {"key": k, "value": a["changes"][k], "change": a["change"],
                "new_percent": round(a["new_probability"] * 100)}

    return {
        "approval_percent": round(p * 100), "decision_band": band(p),
        "factors_hurting": [factor(r) for r in ex["hurting"]],
        "factors_helping": [factor(r) for r in ex["helping"]],
        "suggested_actions": [action(a) for a in sa["actions"]],
        "if_all_done_percent": round(sa["if_all_done"] * 100) if sa["if_all_done"] is not None else None,
        "document_checklist": checklist(applicant.get("employment_type", "salaried")),
        "language": language,
    }


def _nums(text):
    return {n.replace(",", "").rstrip(".") for n in re.findall(r"\d[\d,]*\.?\d*", text)}


def valid(out, payload):
    """Reject anything that is not the right shape, promises approval, or has a number not in the payload."""
    if not isinstance(out, dict) or not isinstance(out.get("summary"), str):
        return False
    for k in ("reasons", "next_steps"):
        if not isinstance(out.get(k), list) or not all(isinstance(x, str) for x in out[k]):
            return False
    text = " ".join([out["summary"]] + out["reasons"] + out["next_steps"])
    if BANNED.search(text):
        return False
    allowed = _nums(json.dumps(payload, ensure_ascii=False)) | {"1", "2", "3"}
    return all(n in allowed for n in _nums(text))


def call_groq(payload, key):
    from groq import Groq
    hi = payload.get("language") == "hi"
    client = Groq(api_key=key, timeout=25.0 if hi else 12.0, max_retries=0)
    kwargs = dict(
        model=MODEL, temperature=0.2, max_tokens=1200 if hi else 600,
        messages=[{"role": "system", "content": SYSTEM},
                  {"role": "user", "content": json.dumps(payload, ensure_ascii=False)}])
    if "gpt-oss" in MODEL:                       # reasoning model: keep thinking short
        kwargs["reasoning_effort"] = "low"
        kwargs["max_tokens"] = 2000 if hi else 1200
    r = client.chat.completions.create(**kwargs)
    text = r.choices[0].message.content or ""
    out = {"summary": "", "reasons": [], "next_steps": []}
    for line in text.splitlines():
        line = line.strip().lstrip("-*• ").strip()
        up = line.upper()
        if up.startswith("SUMMARY:"):
            out["summary"] = line.split(":", 1)[1].strip()
        elif up.startswith("REASON:"):
            out["reasons"].append(line.split(":", 1)[1].strip())
        elif up.startswith("STEP:"):
            out["next_steps"].append(line.split(":", 1)[1].strip())
    if not out["summary"] or not out["reasons"] or not out["next_steps"]:
        raise ValueError("reply not in expected format")
    return out


def generate_explanation(payload, use_llm=True):
    """The one provider-agnostic function. Always returns summary, reasons, next_steps, source."""
    key = os.getenv("GROQ_API_KEY")
    if use_llm and key:
        try:
            out = call_groq(payload, key)
            if valid(out, payload):
                return {"summary": out["summary"], "reasons": out["reasons"],
                        "next_steps": out["next_steps"][:3], "source": "groq"}
            print("LLM output failed checks, using template")
        except Exception as e:                    # never log the payload (personal data)
            print("LLM unavailable, using template:", type(e).__name__, str(e)[:300])
    out = template_explanation(payload)
    out["source"] = "template"
    return out