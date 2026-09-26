import streamlit as st
import sys
import os

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from datetime import datetime, timezone
from app.components import market, watchlist, drilldown, dividends, fundamentals

# ── Page config ──
st.set_page_config(
    page_title="NGX Screener",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ── Inject CSS theme ──
css_path = os.path.join(os.path.dirname(__file__), "styles", "theme.css")
try:
    with open(css_path, encoding="utf-8") as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)
except FileNotFoundError:
    pass

# ── App header ──
now = datetime.now(timezone.utc)
st.markdown(f"""
<div class="app-header">
    <div>
        <div class="app-title">NGX <span>SCREENER</span></div>
        <div class="app-subtitle">Nigerian Exchange Intelligence System · Phase 3</div>
    </div>
    <div class="app-date">
        <div>{now.strftime('%A, %d %B %Y')}</div>
        <div style="margin-top:4px; color:#4a5568">{now.strftime('%H:%M UTC')}</div>
    </div>
</div>
""", unsafe_allow_html=True)

# ── Tabs ──
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "📊  Market",
    "🏆  Watchlist",
    "🔍  Drilldown",
    "💰  Dividends",
    "📑  Fundamentals"
])

with tab1:
    market.render()

with tab2:
    watchlist.render()

with tab3:
    drilldown.render()

with tab4:
    dividends.render()

with tab5:
    fundamentals.render()