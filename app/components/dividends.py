import streamlit as st
import pandas as pd
import sys
import os
from datetime import datetime

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from app.utils.data import get_upcoming_dividends, get_latest_scores, safe_num


def render():
    st.markdown("<div class='section-header'>Dividend Calendar</div>", unsafe_allow_html=True)

    upcoming = get_upcoming_dividends(months_ahead=12)
    scores_df = get_latest_scores()

    if upcoming.empty:
        st.info("""
        No upcoming dividend dates found.
        This is expected — NGX Pulse dividend data shows historical ex-dates.
        Future dates will appear when companies announce new dividends.
        """)
        st.markdown("---")
        st.markdown("<div class='section-header'>Historical Dividend Summary</div>",
                    unsafe_allow_html=True)
    else:
        st.markdown(f"""
        <div style="font-family:'DM Mono',monospace; font-size:11px; color:#8899aa;
                    margin-bottom:16px">
            {len(upcoming)} upcoming dividend events found
        </div>
        """, unsafe_allow_html=True)

        for _, row in upcoming.iterrows():
            sym = row["symbol"]
            ex_date = row["ex_date"]
            pay_date = row.get("pay_date", "—")
            amount = safe_num(row.get("amount"))
            price = safe_num(row.get("price"))
            yld = safe_num(row.get("yield_pct"))

            try:
                days_to = (datetime.strptime(ex_date, "%Y-%m-%d") - datetime.now()).days
                days_label = f"in {days_to} days" if days_to > 0 else "today"
            except Exception:
                days_label = ""

            yld_color = "#c8ff3e" if (yld or 0) >= 5 else "#3ecfff" if (yld or 0) >= 2 else "#8899aa"

            st.markdown(f"""
            <div style="background:#111318; border:1px solid #1e2430; padding:14px 18px;
                        margin-bottom:8px; display:flex; justify-content:space-between;
                        align-items:center;">
                <div>
                    <span style="font-family:'DM Sans',sans-serif; font-weight:600;
                                 font-size:16px; color:#e2e8f0">{sym}</span>
                    <span style="font-family:'DM Mono',monospace; font-size:10px;
                                 color:#8899aa; margin-left:12px">Ex-Date: {ex_date}</span>
                    <span style="font-family:'DM Mono',monospace; font-size:10px;
                                 color:#8899aa; margin-left:12px">Pay: {pay_date}</span>
                </div>
                <div style="display:flex; gap:24px; align-items:center;">
                    <div style="text-align:right">
                        <div style="font-family:'DM Mono',monospace; font-size:14px;
                                    color:#e2e8f0">₦{amount:.4f}</div>
                        <div style="font-family:'DM Mono',monospace; font-size:10px;
                                    color:#8899aa">per share</div>
                    </div>
                    <div style="text-align:right">
                        <div style="font-family:'DM Mono',monospace; font-size:14px;
                                    color:{yld_color}">{yld:.2f}%</div>
                        <div style="font-family:'DM Mono',monospace; font-size:10px;
                                    color:#8899aa">est. yield</div>
                    </div>
                    <div style="font-family:'DM Mono',monospace; font-size:10px;
                                color:#4a5568">{days_label}</div>
                </div>
            </div>
            """, unsafe_allow_html=True)

    # All dividend summary from scores
    st.markdown("<div class='section-header' style='margin-top:24px'>Dividend Scores — All Stocks</div>",
                unsafe_allow_html=True)
    if not scores_df.empty:
        div_df = scores_df[["symbol", "dividend_score", "price", "sector"]].copy()
        div_df = div_df.sort_values("dividend_score", ascending=False)
        div_df["dividend_score"] = div_df["dividend_score"].apply(
            lambda x: f"{x:.0f}/100" if pd.notna(x) else "—")
        div_df["price"] = div_df["price"].apply(lambda x: f"₦{x:.2f}" if pd.notna(x) and x else "—")
        div_df.columns = ["Symbol", "Dividend Score", "Price", "Sector"]
        st.dataframe(div_df, width="stretch", hide_index=True)