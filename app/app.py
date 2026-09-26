import streamlit as st
import sys
import os

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from datetime import datetime, timezone
from app.components import market, watchlist, drilldown, dividends, fundamentals
from app.utils.data import get_conn
from main import run_daily, run_weekly, run_score


def get_system_status() -> dict:
    """Returns {stage: last_run_timestamp} from run_log. Empty dict if unavailable."""
    try:
        conn = get_conn()
        rows = conn.execute(
            "SELECT stage, MAX(timestamp) as last_run FROM run_log GROUP BY stage"
        ).fetchall()
        conn.close()
        return {r["stage"]: r["last_run"] for r in rows}
    except Exception:
        return {}


def _status_date(status: dict, stage: str) -> str:
    """Extracts YYYY-MM-DD from a run_log timestamp, or '—' if absent."""
    ts = status.get(stage)
    if not ts:
        return "—"
    return str(ts)[:10]


def render_operations_panel():
    """Sidebar pipeline controls + system status. Runs before tab content
    so it appears above the Watchlist filters in the sidebar."""
    with st.sidebar:
        st.markdown("<div class='section-header'>Operations</div>", unsafe_allow_html=True)

        if st.button("▶ Daily Update"):
            try:
                run_daily()
                st.sidebar.success("Done.")
                st.rerun()
            except Exception as e:
                st.sidebar.error(str(e))

        if st.button("↻ Weekly Refresh"):
            try:
                run_weekly()
                st.sidebar.success("Done.")
                st.rerun()
            except Exception as e:
                st.sidebar.error(str(e))

        if st.button("⟳ Recalculate Scores"):
            try:
                run_score()
                st.sidebar.success("Done.")
                st.rerun()
            except Exception as e:
                st.sidebar.error(str(e))

        st.markdown("<div class='section-header' style='margin-top:16px'>Status</div>",
                    unsafe_allow_html=True)

        status = get_system_status()
        items = [
            ("LAST MARKET UPDATE", _status_date(status, "insert_prices")),
            ("LAST DIVIDEND REFRESH", _status_date(status, "dividend_collection_run")),
            ("LAST SCORING RUN", _status_date(status, "ranker")),
            ("LAST REPORT", _status_date(status, "report")),
        ]
        for label, value in items:
            st.sidebar.markdown(
                f"<div style=\"font-family:'DM Mono',monospace; font-size:10px; "
                f"color:#8899aa; margin-bottom:8px;\">{label}<br>{value}</div>",
                unsafe_allow_html=True,
            )

        st.sidebar.divider()

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

# ── Sidebar operations (above Watchlist filters) ──
render_operations_panel()

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