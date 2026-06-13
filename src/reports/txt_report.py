import os
import sys
from datetime import datetime, timezone

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

import config
from src.database.db import get_connection


OVERRIDES = {
    "WAPCO": "⚠ Trading 42% above analyst target (Cordros ₦240.54). Score valid but price risky.",
    "OANDO": "⚠ Zero dividend history. Momentum play only — not a long-term hold.",
    "FIRSTHOLDCO": "⚠ Profit down 79% YoY per FY2025 report. High momentum but weak fundamentals.",
    "DANGSUGAR": "⚠ Still loss-making (PAT -₦64B) despite revenue recovery. High risk.",
}


def generate_report(results: list[dict] = None) -> str:
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    conn = get_connection()

    if results is None:
        query = """
            SELECT s.symbol, s.combined_score, s.momentum_score, s.dividend_score,
                   p.price, p.change_pct, p.change_7d_pct, p.volume,
                   st.sector,
                   f.eps, f.roe, f.revenue_growth, f.profit_growth
            FROM scores s
            LEFT JOIN prices p ON s.symbol = p.symbol
                AND p.date = (SELECT MAX(date) FROM prices WHERE symbol = s.symbol)
            LEFT JOIN stocks st ON s.symbol = st.symbol
            LEFT JOIN financials f ON s.symbol = f.symbol
            WHERE s.date = ?
            ORDER BY s.combined_score DESC
        """
        cursor = conn.execute(query, (today,))
        results = [dict(row) for row in cursor.fetchall()]

    if not results:
        conn.close()
        return f"No scores found for {today}. Run ranker first."

    market_query = "SELECT * FROM market_summary ORDER BY date DESC LIMIT 1"
    cursor = conn.execute(market_query)
    market = cursor.fetchone()
    market = dict(market) if market else {}
    conn.close()

    lines = []
    sep = "=" * 62

    # Header
    lines.append(sep)
    lines.append(f"  NGX INTELLIGENCE REPORT — {today}")
    lines.append(f"  Generated: {datetime.now(timezone.utc).strftime('%H:%M UTC')}")
    lines.append(sep)

    # Market overview
    if market:
        lines.append("")
        lines.append("MARKET OVERVIEW")
        lines.append("-" * 40)
        lines.append(f"  ASI:        {market.get('asi', 'N/A'):>12,.2f}")
        lines.append(f"  Change:     {market.get('pct_change', 0):>+11.2f}%")
        lines.append(f"  Volume:     {int(market.get('volume', 0)):>12,}")
        lines.append(f"  Value:      ₦{market.get('value', 0)/1e9:>10.2f}B")
        lines.append(f"  Advancers:  {market.get('advancers', 'N/A'):>12}")
        lines.append(f"  Decliners:  {market.get('decliners', 'N/A'):>12}")

    # Full ranked table
    lines.append("")
    lines.append("FULL RANKED WATCHLIST")
    lines.append("-" * 40)
    lines.append(f"  {'#':<3} {'Symbol':<12} {'Price':>7} {'Mom':>5} {'Div':>5} {'Fund':>5} {'Score':>7}")
    lines.append(f"  {'-'*52}")

    for i, r in enumerate(results, 1):
        price = r.get("price") or 0
        fund = r.get("fundamentals_score")
        fund_str = f"{fund:.0f}" if fund is not None else "—"
        line = (
            f"  {i:<3} "
            f"{r['symbol']:<12} "
            f"₦{price:<6} "
            f"{r.get('momentum_score', 0):>5} "
            f"{r.get('dividend_score', 0):>5} "
            f"{fund_str:>5} "
            f"{r.get('combined_score', 0):>7}"
        )
        lines.append(line)
        if r["symbol"] in OVERRIDES:
            lines.append(f"       {OVERRIDES[r['symbol']]}")

    # Fundamentals snapshot
    lines.append("")
    lines.append("FUNDAMENTALS SNAPSHOT (PDF-extracted)")
    lines.append("-" * 40)
    has_fund = [r for r in results if r.get("eps") is not None or r.get("roe") is not None]
    if has_fund:
        lines.append(f"  {'Symbol':<12} {'EPS':>8} {'ROE%':>7} {'RevGr%':>8} {'PATGr%':>8}")
        lines.append(f"  {'-'*48}")
        for r in results:
            if r.get("eps") or r.get("roe") or r.get("revenue_growth"):
                eps = f"₦{r['eps']:.2f}" if r.get("eps") else "—"
                roe = f"{r['roe']:.1f}%" if r.get("roe") else "—"
                rev = f"{r['revenue_growth']:.1f}%" if r.get("revenue_growth") else "—"
                pat = f"{r['profit_growth']:.1f}%" if r.get("profit_growth") else "—"
                lines.append(f"  {r['symbol']:<12} {eps:>8} {roe:>7} {rev:>8} {pat:>8}")
    else:
        lines.append("  No fundamental data yet — run: python src/scoring/fundamentals.py")

    # Top momentum
    lines.append("")
    lines.append("TOP MOMENTUM PLAYS — 1 MONTH")
    lines.append("-" * 40)
    momentum_top = sorted(results, key=lambda x: x.get("momentum_score", 0), reverse=True)[:5]
    for i, r in enumerate(momentum_top, 1):
        price = r.get("price") or 0
        change_7d = r.get("change_7d_pct") or 0
        lines.append(f"  {i}. {r['symbol']:<12} ₦{price:<8} +{change_7d:.1f}% (7d)  mom={r.get('momentum_score',0)}")
        if r["symbol"] in OVERRIDES:
            lines.append(f"     {OVERRIDES[r['symbol']]}")

    # Top dividend
    lines.append("")
    lines.append("TOP DIVIDEND + GROWTH — LONG TERM")
    lines.append("-" * 40)
    dividend_top = sorted(results, key=lambda x: x.get("dividend_score", 0), reverse=True)[:5]
    for i, r in enumerate(dividend_top, 1):
        price = r.get("price") or 0
        lines.append(f"  {i}. {r['symbol']:<12} ₦{price:<8} div={r.get('dividend_score',0)}")

    # High conviction
    lines.append("")
    lines.append("HIGH CONVICTION — BOTH LISTS")
    lines.append("-" * 40)
    top_m = {r["symbol"] for r in momentum_top}
    top_d = {r["symbol"] for r in dividend_top}
    crossover = top_m & top_d
    if crossover:
        for sym in crossover:
            match = next(r for r in results if r["symbol"] == sym)
            price = match.get("price") or 0
            fund_flag = " [FUND DATA ✓]" if match.get("fundamentals_score") else ""
            lines.append(f"  ★ {sym:<12} combined={match.get('combined_score',0)}  ₦{price}{fund_flag}")
    else:
        lines.append("  None — build more daily history for stronger signals")

    # Notes
    lines.append("")
    lines.append("NOTES")
    lines.append("-" * 40)
    lines.append("  • Scoring: M50+D30+F20 when PDF data available, M60+D40 otherwise")
    lines.append("  • Scores improve as 30-day price history accumulates")
    lines.append("  • Run market_collector.py daily before generating report")
    lines.append("  • Run dividend_collector.py weekly to refresh yield data")
    lines.append("  • Run fundamentals.py when new quarterly PDFs are available")
    lines.append("  • NOT FINANCIAL ADVICE. Verify before trading.")
    lines.append("")
    lines.append(sep)

    report = "\n".join(lines)

    os.makedirs(config.REPORTS_DAILY, exist_ok=True)
    report_path = os.path.join(config.REPORTS_DAILY, f"{today}.txt")
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(report)

    print(f"Report saved to {report_path}")
    return report


if __name__ == "__main__":
    report = generate_report()
    print(report)