from explain import inr

LABELS_HI = {
    "emi_burden": "EMI का बोझ और आय के मुकाबले लोन का आकार",
    "monthly_income": "मासिक आय", "employment_years": "नौकरी/व्यवसाय के वर्ष",
    "residence_years": "वर्तमान निवास के वर्ष", "is_new_to_credit": "क्रेडिट हिस्ट्री नहीं है",
    "cibil_score": "CIBIL स्कोर", "credit_age_years": "क्रेडिट हिस्ट्री की लंबाई",
    "credit_utilisation_pct": "क्रेडिट कार्ड का उपयोग", "recent_enquiries_6m": "हाल की लोन पूछताछ",
    "missed_payments_12m": "छूटी हुई किस्तें (12 महीने)", "existing_loans_count": "मौजूदा लोन",
    "existing_emi_monthly": "मौजूदा मासिक EMI", "loan_amount_requested": "माँगी गई लोन राशि",
    "loan_tenure_months": "लोन की अवधि", "documents_complete": "दस्तावेज़",
}
BAND_HI = {"Good chance": "अच्छी संभावना", "Moderate chance": "मध्यम संभावना", "Low chance": "कम संभावना"}


def _action_hi(a):
    k, v = a["key"], a["value"]
    if k == "documents_complete":
        return "सभी ज़रूरी दस्तावेज़ पूरे करें"
    if k == "loan_tenure_months":
        return f"लोन की अवधि {int(v)} महीने रखें (EMI कम, कुल ब्याज ज़्यादा)"
    if k == "credit_utilisation_pct":
        return f"क्रेडिट कार्ड का उपयोग लगभग {int(v)}% तक घटाएँ"
    if k == "existing_emi_monthly":
        return f"मौजूदा लोन चुकाकर मासिक EMI लगभग {inr(v)} तक लाएँ"
    if k == "loan_amount_requested":
        return f"कम राशि का लोन माँगें: {inr(v)}"
    return a["change"]


def template_explanation(payload):
    hi = payload.get("language") == "hi"
    pct, band = payload["approval_percent"], payload["decision_band"]
    hurting, helping = payload["factors_hurting"], payload["factors_helping"]
    actions = payload["suggested_actions"]

    if hi:
        summary = (f"आपके लोन के मंज़ूर होने की अनुमानित संभावना लगभग {pct}% है ({BAND_HI[band]}). "
                   "यह सिर्फ़ एक अनुमान है, बैंक का फ़ैसला नहीं।")
        reasons = [f"{LABELS_HI.get(r['key'], r['feature'])} ({r['value']}) आपकी संभावना घटाता है।" for r in hurting]
        reasons += [f"{LABELS_HI.get(r['key'], r['feature'])} ({r['value']}) आपकी संभावना बढ़ाता है।" for r in helping]
        steps = [f"{_action_hi(a)} (अनुमानित संभावना लगभग {a['new_percent']}%)" for a in actions]
        if payload.get("if_all_done_percent"):
            steps.append(f"ये सभी कदम साथ में उठाने पर संभावना लगभग {payload['if_all_done_percent']}% हो सकती है।")
        if not reasons:
            reasons = ["कोई एक कारण बहुत बड़ा असर नहीं डाल रहा।"]
        if not steps:
            steps = ["दस्तावेज़ तैयार रखें और उतनी ही राशि माँगें जितनी आप आराम से चुका सकें।"]
    else:
        summary = (f"Your estimated chance of approval is about {pct}% ({band.lower()}). "
                   "This is an estimate, not a lending decision.")
        reasons = [f"{r['feature']} ({r['value']}) lowers your chances." for r in hurting]
        reasons += [f"{r['feature']} ({r['value']}) improves your chances." for r in helping]
        steps = [f"{a['change']} (estimated chance about {a['new_percent']}%)" for a in actions]
        if payload.get("if_all_done_percent"):
            steps.append(f"Doing all of these together could raise it to about {payload['if_all_done_percent']}%.")
        if not reasons:
            reasons = ["No single factor has a strong effect."]
        if not steps:
            steps = ["Keep your documents ready and ask only for an amount you can repay comfortably."]

    return {"summary": summary, "reasons": reasons, "next_steps": steps}