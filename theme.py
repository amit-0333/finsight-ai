NAVY, SKY, BG, CARD = "#002E6E", "#00B9F5", "#F5F9FF", "#FFFFFF"
INK, MUTED = "#0B1F3A", "#5B6B82"
GOOD, WARN, BAD = "#1FA971", "#F5A623", "#E5484D"
BAND_COLOR = {"Good chance": GOOD, "Moderate chance": WARN, "Low chance": BAD}
DISCLAIMER = "Estimate only - not financial advice or a lending decision."

CSS = f"""
<style>
.block-container {{ padding-top: 4rem; max-width: 1150px; }}
[data-testid="stVerticalBlockBorderWrapper"] {{ background:{CARD}; border-radius:14px; }}
.topbar {{ background:{NAVY}; color:white; padding:14px 22px; border-radius:14px;
          display:flex; justify-content:space-between; align-items:center; margin-bottom:18px; }}
.topbar b {{ font-size:1.25rem; }} .topbar span {{ color:{SKY}; font-weight:600; }}
.card {{ background:{CARD}; border:1px solid #E1EAF5; border-radius:14px; padding:16px 18px;
        margin-bottom:14px; box-shadow:0 1px 3px rgba(0,46,110,.06); }}
.muted {{ color:{MUTED}; font-size:.9rem; }}
.pill {{ display:inline-block; padding:3px 12px; border-radius:999px; color:white; font-weight:600; }}
.note {{ background:#E8F7FE; border-left:4px solid {SKY}; padding:8px 12px; border-radius:6px;
        color:{INK}; font-size:.92rem; }}
.disclaimer {{ color:{MUTED}; font-size:.8rem; text-align:center; margin-top:18px; }}
.stButton > button[kind="primary"] {{ padding:.75rem 2.5rem; font-size:1.1rem; font-weight:600; border-radius:10px; }}
</style>
"""


def plotly_layout():
    return dict(paper_bgcolor=CARD, plot_bgcolor=CARD, font=dict(color=INK, family="sans-serif"),
                margin=dict(l=10, r=10, t=40, b=10), colorway=[SKY, NAVY, "#7FD8F9", "#4A6FA5", WARN])