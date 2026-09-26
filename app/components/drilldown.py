import streamlit as st
import pandas as pd
import sys
import os

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from app.utils.data import (
    get_latest_scores, get_price_history, get_score_history,
    get_dividend_history, get_all_symbols, safe_num
)
from app.utils.charts import (
    price_history_chart, score_breakdown_chart,
    score_history_chart, volume_chart
)


def render():
    st.markdown("<div class='section-header'>Stock Drilldown</div>", unsafe_allow_html=True)

    symbols = get_all_symbols()
    if not symbols:
        st.warning("No data yet. Run `python main.py --mode daily` first.")
        return

    selected = st.selectbox("Select Stock", symbols, key="drilldown_select")
    if not selected:
        return

    # Pull data
    scores_df = get_latest_scores()
    stock_row = scores_df[scores_df["symbol"] == selected]
    price_df = get_price_history(selected, days=60)
    score_df = get_score_history(selected)
    div_df = get_dividend_history(selected)

    if stock_row.empty:
        st.info(f"No score data for {selected}.")
        return

    row = stock_row.iloc[0]
    price = safe_num(row.get("price"))
    mom = safe_num(row.get("momentum_score"))
    div = safe_num(row.get("dividend_score"))
    combined = safe_num(row.get("combined_score"))
    sector = row.get("sector") or "—"
    market = row.get("market") or "—"
    chg = safe_num(row.get("change_pct"))
    eps = row.get("eps")
    roe = row.get("roe")
    rev_growth = row.get("revenue_growth")
    pat_growth = row.get("profit_growth")
    db_fund_flag = safe_num(row.get("has_fundamentals"))
    has_fundamentals = bool(db_fund_flag) or any(
        v is not None and pd.notna(v) for v in [eps, roe, rev_growth, pat_growth])
    fund_raw = row.get("fundamentals_score")
    fund_label = f"{fund_raw:.0f}" if pd.notna(fund_raw) else "—"

    chg_color = "#c8ff3e" if chg >= 0 else "#ff4d4d"
    chg_sign = "+" if chg >= 0 else ""

    # Stock header
    st.markdown(f"""
    <div style="background:#111318; border:1px solid #1e2430; padding:20px 24px;
                margin-bottom:20px; border-left:3px solid #3ecfff;">
        <div style="display:flex; justify-content:space-between; align-items:flex-start;">
            <div>
                <div style="font-family:'Bebas Neue',sans-serif; font-size:36px;
                            letter-spacing:2px; color:#e2e8f0; line-height:1">{selected}</div>
                <div style="font-family:'DM Mono',monospace; font-size:10px;
                            color:#8899aa; margin-top:4px; letter-spacing:1px">
                    {sector} &nbsp;·&nbsp; {market}
                </div>
            </div>
            <div style="text-align:right;">
                <div style="font-family:'DM Mono',monospace; font-size:28px;
                            color:#e2e8f0">₦{price:.2f}</div>
                <div style="font-family:'DM Mono',monospace; font-size:12px;
                            color:{chg_color}">{chg_sign}{chg:.2f}% today</div>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Score cards
    c1, c2, c3, c4 = st.columns(4)
    cards = [
        ("Momentum", f"{mom:.0f}", "#ffb83e", "blue"),
        ("Dividend", f"{div:.0f}", "#3ecfff", "blue"),
        ("Fundamentals", fund_label, "#c8ff3e" if has_fundamentals else "#4a5568", ""),
        ("Combined Score", f"{combined:.1f}", "#c8ff3e", ""),
    ]
    for col, (label, value, color, card_class) in zip([c1, c2, c3, c4], cards):
        with col:
            st.markdown(f"""
            <div class="metric-card {card_class}">
                <div class="metric-label">{label}</div>
                <div class="metric-value" style="color:{color}">{value}</div>
                <div class="metric-sub">out of 100</div>
            </div>""", unsafe_allow_html=True)

    st.markdown("<div style='margin-top:20px'></div>", unsafe_allow_html=True)

    # Charts row
    col_left, col_right = st.columns([3, 2])
    with col_left:
        if not price_df.empty:
            st.plotly_chart(price_history_chart(price_df, selected), width="stretch")
            st.plotly_chart(volume_chart(price_df, selected), width="stretch")
        else:
            st.info("Price history builds up after daily runs.")

    with col_right:
        fund_score = fund_raw if has_fundamentals and pd.notna(fund_raw) else None
        st.plotly_chart(score_breakdown_chart(mom, div, fund_score), width="stretch")
        if not score_df.empty:
            st.plotly_chart(score_history_chart(score_df, selected), width="stretch")

    # Dividend history
    st.markdown("<div class='section-header' style='margin-top:20px'>Dividend History</div>",
                unsafe_allow_html=True)
    if not div_df.empty:
        div_display = div_df.copy()
        div_display["amount"] = div_display["amount"].apply(
            lambda x: f"₦{x:.4f}" if pd.notna(x) and x else "—")
        div_display.columns = ["Ex-Date", "Record Date", "Pay Date", "Amount", "Currency"]
        st.dataframe(div_display, width="stretch", hide_index=True)
    else:
        st.info("No dividend history found for this stock.")

    # Fundamentals panel
    if has_fundamentals:
        st.markdown("<div class='section-header' style='margin-top:20px'>Fundamentals (PDF-Extracted)</div>",
                    unsafe_allow_html=True)
        f1, f2, f3, f4 = st.columns(4)
        items = [
            (f1, "EPS", f"₦{eps:.2f}" if pd.notna(eps) else "—", "#c8ff3e"),
            (f2, "ROE", f"{roe:.1f}%" if pd.notna(roe) else "—", "#3ecfff"),
            (f3, "Revenue Growth", f"{rev_growth:.1f}%" if pd.notna(rev_growth) else "—",
             "#c8ff3e" if safe_num(rev_growth) >= 0 else "#ff4d4d"),
            (f4, "PAT Growth", f"{pat_growth:.1f}%" if pd.notna(pat_growth) else "—",
             "#c8ff3e" if safe_num(pat_growth) >= 0 else "#ff4d4d"),
        ]
        for col, label, value, color in items:
            with col:
                st.markdown(f"""
                <div class="metric-card">
                    <div class="metric-label">{label}</div>
                    <div class="metric-value" style="color:{color}; font-size:22px">{value}</div>
                </div>""", unsafe_allow_html=True)