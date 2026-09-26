import streamlit as st
import pandas as pd
import sys
import os

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from app.utils.data import get_latest_market_summary, get_market_history, safe_num
from app.utils.charts import asi_trend_chart


def render():
    market = get_latest_market_summary()
    if not market:
        st.warning("No market data. Run `python main.py --mode daily` first.")
        return

    asi = safe_num(market.get("asi"))
    chg = safe_num(market.get("pct_change"))
    volume = safe_num(market.get("volume"))
    value = safe_num(market.get("value"))
    adv = safe_num(market.get("advancers"))
    dec = safe_num(market.get("decliners"))
    unc = safe_num(market.get("unchanged"))
    trade_date = market.get("date") or "—"

    chg_color = "green" if chg >= 0 else "red"
    chg_sign = "+" if chg >= 0 else ""

    st.markdown(f"""
    <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:20px;">
        <div class="section-header">Market Overview</div>
        <div style="font-family:'DM Mono',monospace; font-size:10px; color:#8899aa;">
            {trade_date}
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Metric cards row
    c1, c2, c3, c4, c5 = st.columns(5)

    with c1:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-label">All-Share Index</div>
            <div class="metric-value">{asi:,.0f}</div>
            <div class="metric-sub">NGX ASI</div>
        </div>""", unsafe_allow_html=True)

    with c2:
        st.markdown(f"""
        <div class="metric-card {'blue' if chg >= 0 else 'red'}">
            <div class="metric-label">Daily Change</div>
            <div class="metric-value {chg_color}">{chg_sign}{chg:.2f}%</div>
            <div class="metric-sub">vs prior close</div>
        </div>""", unsafe_allow_html=True)

    with c3:
        st.markdown(f"""
        <div class="metric-card blue">
            <div class="metric-label">Volume Traded</div>
            <div class="metric-value blue">{volume/1e6:.0f}M</div>
            <div class="metric-sub">shares</div>
        </div>""", unsafe_allow_html=True)

    with c4:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-label">Value Traded</div>
            <div class="metric-value">₦{value/1e9:.2f}B</div>
            <div class="metric-sub">Nigerian Naira</div>
        </div>""", unsafe_allow_html=True)

    with c5:
        st.markdown(f"""
        <div class="metric-card {'blue' if adv > dec else 'red'}">
            <div class="metric-label">Breadth</div>
            <div class="metric-value" style="font-size:20px;">
                <span style="color:#c8ff3e">{adv}↑</span>
                <span style="color:#ff4d4d; margin:0 4px">{dec}↓</span>
                <span style="color:#8899aa">{unc}—</span>
            </div>
            <div class="metric-sub">adv / dec / unc</div>
        </div>""", unsafe_allow_html=True)

    st.markdown("<div style='margin-top:24px'></div>", unsafe_allow_html=True)

    # ASI trend chart
    history = get_market_history(days=30)
    if not history.empty:
        st.plotly_chart(asi_trend_chart(history), width="stretch")
    else:
        st.info("ASI trend available after 2+ days of data collection.")

    # Recent market summary table
    st.markdown("<div class='section-header' style='margin-top:24px'>Recent Sessions</div>",
                unsafe_allow_html=True)
    history_display = get_market_history(days=10).sort_values("date", ascending=False)
    if not history_display.empty:
        history_display = history_display[[
            "date", "asi", "pct_change", "volume", "value", "advancers", "decliners"
        ]].rename(columns={
            "date": "Date", "asi": "ASI", "pct_change": "Chg%",
            "volume": "Volume", "value": "Value (₦)",
            "advancers": "Adv", "decliners": "Dec"
        })
        history_display["ASI"] = history_display["ASI"].apply(
            lambda x: f"{x:,.2f}" if pd.notna(x) else "—")
        history_display["Chg%"] = history_display["Chg%"].apply(
            lambda x: f"+{x:.2f}%" if pd.notna(x) and x >= 0 else (f"{x:.2f}%" if pd.notna(x) else "—")
        )
        history_display["Volume"] = history_display["Volume"].apply(
            lambda x: f"{x/1e6:.0f}M" if pd.notna(x) else "—")
        history_display["Value (₦)"] = history_display["Value (₦)"].apply(
            lambda x: f"₦{x/1e9:.2f}B" if pd.notna(x) else "—")
        st.dataframe(history_display, width="stretch", hide_index=True)