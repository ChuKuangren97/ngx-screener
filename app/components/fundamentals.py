import streamlit as st
import pandas as pd
import sys
import os

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from app.utils.data import get_all_fundamentals
from app.utils.charts import fundamentals_comparison_chart


def render():
    st.markdown("<div class='section-header'>Fundamentals Lab</div>", unsafe_allow_html=True)

    df = get_all_fundamentals()

    if df.empty:
        st.info("No fundamental data yet. Run `python src/scoring/fundamentals.py` first.")
        return

    has_data = df[df[["eps", "roe", "revenue_growth", "profit_growth"]].notna().any(axis=1)]

    if has_data.empty:
        st.info("PDF extraction hasn't populated any metrics yet.")
        return

    st.markdown(f"""
    <div style="font-family:'DM Mono',monospace; font-size:11px; color:#8899aa; margin-bottom:16px">
        {has_data['symbol'].nunique()} stocks with PDF-extracted fundamental data
    </div>
    """, unsafe_allow_html=True)

    # Summary comparison table
    st.markdown("<div class='section-header'>Side-by-Side Comparison</div>",
                unsafe_allow_html=True)

    display = has_data[["symbol", "period", "eps", "roe",
                         "revenue_growth", "profit_growth", "debt_to_equity", "price"]].copy()

    display["eps"] = display["eps"].apply(lambda x: f"₦{x:.2f}" if pd.notna(x) and x else "—")
    display["roe"] = display["roe"].apply(lambda x: f"{x:.1f}%" if pd.notna(x) and x else "—")
    display["revenue_growth"] = display["revenue_growth"].apply(
        lambda x: f"+{x:.1f}%" if pd.notna(x) and x and x >= 0 else (f"{x:.1f}%" if pd.notna(x) and x else "—")
    )
    display["profit_growth"] = display["profit_growth"].apply(
        lambda x: f"+{x:.1f}%" if pd.notna(x) and x and x >= 0 else (f"{x:.1f}%" if pd.notna(x) and x else "—")
    )
    display["debt_to_equity"] = display["debt_to_equity"].apply(
        lambda x: f"{x:.2f}x" if pd.notna(x) and x else "—"
    )
    display["price"] = display["price"].apply(lambda x: f"₦{x:.2f}" if pd.notna(x) and x else "—")
    display.columns = ["Symbol", "Period", "EPS", "ROE", "Rev Growth", "PAT Growth", "D/E", "Price"]

    st.dataframe(display, width="stretch", hide_index=True)

    # Charts
    st.markdown("<div class='section-header' style='margin-top:24px'>Visual Comparison</div>",
                unsafe_allow_html=True)

    col1, col2 = st.columns(2)
    raw = get_all_fundamentals()

    with col1:
        fig = fundamentals_comparison_chart(raw, "roe", "Return on Equity (%)")
        if fig.data:
            st.plotly_chart(fig, width="stretch")

        fig2 = fundamentals_comparison_chart(raw, "revenue_growth", "Revenue Growth (%)")
        if fig2.data:
            st.plotly_chart(fig2, width="stretch")

    with col2:
        fig3 = fundamentals_comparison_chart(raw, "profit_growth", "Profit After Tax Growth (%)")
        if fig3.data:
            st.plotly_chart(fig3, width="stretch")

        fig4 = fundamentals_comparison_chart(raw, "debt_to_equity", "Debt-to-Equity Ratio", is_percent=False)
        if fig4.data:
            st.plotly_chart(fig4, width="stretch")