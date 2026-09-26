import streamlit as st
import pandas as pd
import sys
import os

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from app.utils.data import get_latest_scores, get_sectors, safe_num

OVERRIDES = {
    "WAPCO":       "Trading 42% above analyst target (Cordros ₦240.54)",
    "OANDO":       "Zero dividend history — momentum play only",
    "FIRSTHOLDCO": "Profit down 79% YoY per FY2025 report",
    "DANGSUGAR":   "Still loss-making despite revenue recovery",
}

def score_badge(score: float) -> str:
    score = safe_num(score)
    if score >= 55:
        return f'<span class="score-badge score-high">{score:.1f}</span>'
    elif score >= 40:
        return f'<span class="score-badge score-mid">{score:.1f}</span>'
    elif score >= 25:
        return f'<span class="score-badge score-low">{score:.1f}</span>'
    else:
        return f'<span class="score-badge score-warn">{score:.1f}</span>'


def render():
    st.markdown("<div class='section-header'>Ranked Watchlist</div>", unsafe_allow_html=True)

    df = get_latest_scores()
    if df.empty:
        st.warning("No scores found. Run `python main.py --mode daily` first.")
        return

    # Sidebar filters
    with st.sidebar:
        st.markdown("### Filters")
        sectors = ["All"] + get_sectors()
        selected_sector = st.selectbox("Sector", sectors)
        min_score = st.slider("Min Combined Score", 0, 100, 0, step=5)
        show_warnings = st.checkbox("Show warning flags", value=True)

    # Apply filters
    if selected_sector != "All":
        df = df[df["sector"] == selected_sector]
    df = df[df["combined_score"] >= min_score]

    if df.empty:
        st.info("No stocks match current filters.")
        return

    # Summary strip
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.markdown(f"""<div class="metric-card">
            <div class="metric-label">Eligible Stocks</div>
            <div class="metric-value">{len(df)}</div>
        </div>""", unsafe_allow_html=True)
    with col2:
        high_conv = df[df["combined_score"] >= 55]
        st.markdown(f"""<div class="metric-card">
            <div class="metric-label">High Conviction</div>
            <div class="metric-value green">{len(high_conv)}</div>
        </div>""", unsafe_allow_html=True)
    with col3:
        mom_valid = df[df["momentum_score"].notna()]
        top_mom = df.loc[mom_valid["momentum_score"].idxmax(), "symbol"] if not mom_valid.empty else "—"
        st.markdown(f"""<div class="metric-card blue">
            <div class="metric-label">Top Momentum</div>
            <div class="metric-value blue" style="font-size:22px">{top_mom}</div>
        </div>""", unsafe_allow_html=True)
    with col4:
        div_valid = df[df["dividend_score"].notna()]
        top_div = df.loc[div_valid["dividend_score"].idxmax(), "symbol"] if not div_valid.empty else "—"
        st.markdown(f"""<div class="metric-card">
            <div class="metric-label">Top Dividend</div>
            <div class="metric-value" style="font-size:22px">{top_div}</div>
        </div>""", unsafe_allow_html=True)

    st.markdown("<div style='margin-top:20px'></div>", unsafe_allow_html=True)

    # Ranked table
    for i, row in enumerate(df.itertuples(), 1):
        symbol = row.symbol
        price = safe_num(row.price)
        mom = safe_num(row.momentum_score)
        div = safe_num(row.dividend_score)
        combined = safe_num(row.combined_score)
        sector = row.sector or "—"
        chg = safe_num(row.change_pct)
        chg_7d = safe_num(row.change_7d_pct)

        is_high = combined >= 55
        has_warning = symbol in OVERRIDES
        border_color = "#c8ff3e" if is_high else ("#ffb83e" if has_warning else "#1e2430")

        chg_color = "#c8ff3e" if chg >= 0 else "#ff4d4d"
        chg_sign = "+" if chg >= 0 else ""
        chg7d_color = "#c8ff3e" if chg_7d >= 0 else "#ff4d4d"
        chg7d_sign = "+" if chg_7d >= 0 else ""

        conviction_star = "★ " if is_high else ""

        warning_html = ""
        if show_warnings and has_warning:
            warning_html = f'<div style="margin-top:6px"><span class="warn-pill">⚠ {OVERRIDES[symbol]}</span></div>'

        st.markdown(f"""
        <div style="background:#111318; border:1px solid {border_color};
                    border-left:3px solid {border_color}; padding:14px 18px;
                    margin-bottom:8px; border-radius:2px;">
            <div style="display:flex; justify-content:space-between; align-items:center;">
                <div style="display:flex; align-items:center; gap:16px;">
                    <div style="font-family:'DM Mono',monospace; font-size:11px;
                                color:#8899aa; width:24px">#{i}</div>
                    <div>
                        <div style="font-family:'DM Sans',sans-serif; font-weight:600;
                                    font-size:16px; color:#e2e8f0;">
                            <span style="color:#c8ff3e">{conviction_star}</span>{symbol}
                        </div>
                        <div style="font-family:'DM Mono',monospace; font-size:10px;
                                    color:#8899aa; margin-top:2px">{sector}</div>
                    </div>
                </div>
                <div style="display:flex; align-items:center; gap:24px;">
                    <div style="text-align:right">
                        <div style="font-family:'DM Mono',monospace; font-size:16px;
                                    color:#e2e8f0;">₦{price:.2f}</div>
                        <div style="font-family:'DM Mono',monospace; font-size:10px;">
                            <span style="color:{chg_color}">{chg_sign}{chg:.2f}%</span>
                            <span style="color:#4a5568; margin:0 4px">·</span>
                            <span style="color:{chg7d_color}">{chg7d_sign}{chg_7d:.1f}% 7d</span>
                        </div>
                    </div>
                    <div style="display:flex; gap:8px; align-items:center;">
                        <div style="text-align:center">
                            <div style="font-family:'DM Mono',monospace; font-size:9px;
                                        color:#8899aa; letter-spacing:1px">MOM</div>
                            <div style="font-family:'DM Mono',monospace; font-size:13px;
                                        color:#ffb83e">{mom:.0f}</div>
                        </div>
                        <div style="text-align:center">
                            <div style="font-family:'DM Mono',monospace; font-size:9px;
                                        color:#8899aa; letter-spacing:1px">DIV</div>
                            <div style="font-family:'DM Mono',monospace; font-size:13px;
                                        color:#3ecfff">{div:.0f}</div>
                        </div>
                        <div style="margin-left:8px">{score_badge(combined)}</div>
                    </div>
                </div>
            </div>
            {warning_html}
        </div>
        """, unsafe_allow_html=True)