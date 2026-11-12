def checklist(employment_type):
    if employment_type == "self_employed":
        return ["Photo ID (Aadhaar / PAN)", "Address proof",
                "Last 2 years' ITR", "Business proof (GST / registration)",
                "Last 6 months' bank statements"]
    return ["Photo ID (Aadhaar / PAN)", "Address proof",
            "Last 3-6 months' salary slips", "Last 6 months' bank statements",
            "Form 16 or ITR"]


def band(p):
    """Demo setting, not learned from data."""
    if p >= 0.70:
        return "Good chance"
    if p >= 0.45:
        return "Moderate chance"
    return "Low chance"