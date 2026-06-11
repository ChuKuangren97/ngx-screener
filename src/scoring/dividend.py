import os
import sys
from datetime import datetime, timezone

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

import config
from src.database.db import get_connection


class DividendScorer:
    """
    Calculates dividend score (0-100) for each stock.

    Scoring breakdown:
    - Dividend yield:      0-40 pts
    - Payout consistency:  0-30 pts  (how many years paid)
    - Growth trend:        0-20 pts  (DPS growing YoY)
    - Payout timing:       0-10 pts  (how soon is next ex-date)
    """

    def __init__(self, conn=None):
        self.conn = conn or get_connection()

    def get_dividend_history(self, symbol: str) -> list[dict]:
        """Returns all dividend records for a symbol ordered by ex_date DESC."""
        query = """
            SELECT * FROM dividends
            WHERE symbol = ?
            ORDER BY ex_date DESC
        """
        cursor = self.conn.execute(query, (symbol,))
        return [dict(row) for row in cursor.fetchall()]

    def get_current_price(self, symbol: str) -> float:
        """Returns most recent price for a symbol."""
        query = """
            SELECT price FROM prices
            WHERE symbol = ?
            ORDER BY date DESC
            LIMIT 1
        """
        cursor = self.conn.execute(query, (symbol,))
        row = cursor.fetchone()
        return row["price"] if row else None

    def score_yield(self, symbol: str, history: list[dict]) -> float:
        """
        Calculates trailing 12-month dividend yield against current price.
        Sums all dividends paid in last 12 months.
        >=8%  → 40 pts
        5-8%  → 28 pts
        3-5%  → 15 pts
        1-3%  → 5 pts
        0%    → 0 pts
        """
        if not history:
            return 0

        price = self.get_current_price(symbol)
        if not price or price == 0:
            return 0

        # Sum dividends from last 12 months
        cutoff = datetime.now(timezone.utc).replace(year=datetime.now().year - 1)
        cutoff_str = cutoff.strftime("%Y-%m-%d")

        ttm_dividends = sum(
            d["amount"]
            for d in history
            if d.get("ex_date", "") >= cutoff_str and d.get("amount")
        )

        if ttm_dividends == 0:
            return 0

        yield_pct = (ttm_dividends / price) * 100

        if yield_pct >= 8:
            return 40
        elif yield_pct >= 5:
            return 28
        elif yield_pct >= 3:
            return 15
        elif yield_pct > 0:
            return 5
        else:
            return 0

    def score_consistency(self, history: list[dict]) -> float:
        """
        Counts distinct years in which dividends were paid.
        5+ years → 30 pts
        3-4 years → 20 pts
        1-2 years → 10 pts
        0 years   → 0 pts
        """
        if not history:
            return 0

        years_paid = set()
        for d in history:
            ex_date = d.get("ex_date", "")
            if ex_date and len(ex_date) >= 4:
                years_paid.add(ex_date[:4])

        count = len(years_paid)

        if count >= 5:
            return 30
        elif count >= 3:
            return 20
        elif count >= 1:
            return 10
        else:
            return 0

    def score_growth(self, history: list[dict]) -> float:
        """
        Compares most recent annual DPS to prior year's annual DPS.
        Growing  → 20 pts
        Flat     → 10 pts
        Declining → 0 pts
        Not enough data → 10 pts (neutral)
        """
        if len(history) < 2:
            return 10

        # Group dividends by year, sum per year
        by_year = {}
        for d in history:
            ex_date = d.get("ex_date", "")
            if ex_date and len(ex_date) >= 4 and d.get("amount"):
                year = ex_date[:4]
                by_year[year] = by_year.get(year, 0) + d["amount"]

        sorted_years = sorted(by_year.keys(), reverse=True)

        if len(sorted_years) < 2:
            return 10

        latest_year_dps = by_year[sorted_years[0]]
        prior_year_dps = by_year[sorted_years[1]]

        if prior_year_dps == 0:
            return 10

        if latest_year_dps > prior_year_dps:
            return 20
        elif latest_year_dps == prior_year_dps:
            return 10
        else:
            return 0

    def score_timing(self, history: list[dict]) -> float:
        """
        Checks how soon the most recent ex-dividend date was.
        Stocks with recent payouts are more likely to pay again soon.
        Within 6 months  → 10 pts
        6-12 months      → 5 pts
        >12 months       → 0 pts
        No history       → 0 pts
        """
        if not history:
            return 0

        latest_ex_date = history[0].get("ex_date", "")
        if not latest_ex_date:
            return 0

        try:
            ex_dt = datetime.strptime(latest_ex_date, "%Y-%m-%d")
            now = datetime.now()
            days_since = (now - ex_dt).days

            if days_since <= 180:
                return 10
            elif days_since <= 365:
                return 5
            else:
                return 0
        except ValueError:
            return 0

    def score_stock(self, stock: dict) -> dict:
        """
        Calculates total dividend score for one stock.
        Returns dict with symbol, individual scores, and total.
        """
        symbol = stock.get("symbol")
        history = self.get_dividend_history(symbol)

        s_yield = self.score_yield(symbol, history)
        s_consistency = self.score_consistency(history)
        s_growth = self.score_growth(history)
        s_timing = self.score_timing(history)

        total = s_yield + s_consistency + s_growth + s_timing

        return {
            "symbol": symbol,
            "score_yield": s_yield,
            "score_consistency": s_consistency,
            "score_growth": s_growth,
            "score_timing": s_timing,
            "dividend_score": round(total, 2),
        }

    def score_all(self, stocks: list[dict]) -> list[dict]:
        """
        Scores a list of stocks and returns results sorted by
        dividend_score descending.
        """
        results = [self.score_stock(s) for s in stocks]
        return sorted(results, key=lambda x: x["dividend_score"], reverse=True)


if __name__ == "__main__":
    from src.filters.screener import Screener

    screener = Screener()
    eligible = screener.run(verbose=False)

    scorer = DividendScorer()
    scores = scorer.score_all(eligible)

    print("\n--- Dividend Scores ---")
    print(
        f"{'Symbol':<15} {'Yield':>6} {'Cons':>5} {'Grow':>5} {'Time':>5} {'TOTAL':>7}"
    )
    print("-" * 50)
    for s in scores:
        print(
            f"{s['symbol']:<15}"
            f"{s['score_yield']:>6}"
            f"{s['score_consistency']:>5}"
            f"{s['score_growth']:>5}"
            f"{s['score_timing']:>5}"
            f"{s['dividend_score']:>7}"
        )
    print("-" * 50)
