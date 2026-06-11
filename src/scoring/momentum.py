import os
import sys
from datetime import datetime, timezone

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

import config
from src.database.db import get_connection


class MomentumScorer:
    """
    Calculates momentum score (0-100) for each stock.

    Scoring breakdown:
    - 7-day return:        0-40 pts
    - Volume vs average:   0-30 pts
    - Price stability:     0-20 pts  (inverse of daily swing)
    - Sector trend:        0-10 pts  (based on sector net advancers)
    """

    def __init__(self, conn=None):
        self.conn = conn or get_connection()

    def score_7d_return(self, change_7d_pct) -> float:
        """
        Awards points based on 7-day price return.
        >=10%  → 40 pts
        5-10%  → 25 pts
        0-5%   → 10 pts
        negative → 0 pts
        """
        if change_7d_pct is None:
            return 0
        if change_7d_pct >= 10:
            return 40
        elif change_7d_pct >= 5:
            return 25
        elif change_7d_pct > 0:
            return 10
        else:
            return 0

    def score_volume(self, symbol: str, current_volume) -> float:
        """
        Compares today's volume against 30-day average.
        >2x average  → 30 pts
        1.5-2x       → 20 pts
        1-1.5x       → 10 pts
        <1x          → 0 pts
        Returns 5 pts if not enough history yet.
        """
        if current_volume is None:
            return 0

        query = """
            SELECT AVG(volume) as avg_vol
            FROM (
                SELECT volume FROM prices
                WHERE symbol = ?
                AND volume IS NOT NULL
                ORDER BY date DESC
                LIMIT 30
            )
        """
        cursor = self.conn.execute(query, (symbol,))
        row = cursor.fetchone()

        if not row or not row["avg_vol"] or row["avg_vol"] == 0:
            return 5  # not enough history

        ratio = current_volume / row["avg_vol"]

        if ratio >= 2.0:
            return 30
        elif ratio >= 1.5:
            return 20
        elif ratio >= 1.0:
            return 10
        else:
            return 0

    def score_stability(self, change_pct) -> float:
        """
        Awards points for low daily price swing (stability).
        Inverse of volatility — stable stocks score higher.
        |change| < 1%  → 20 pts
        |change| < 2%  → 15 pts
        |change| < 5%  → 10 pts
        |change| < 10% → 5 pts
        >=10%          → 0 pts (filtered out by screener anyway)
        """
        if change_pct is None:
            return 10  # neutral if unknown

        abs_change = abs(change_pct)

        if abs_change < 1:
            return 20
        elif abs_change < 2:
            return 15
        elif abs_change < 5:
            return 10
        elif abs_change < 10:
            return 5
        else:
            return 0

    def score_sector_trend(self, symbol: str) -> float:
        """
        Checks if the stock's sector has more advancers than decliners
        over the last 5 trading days in the database.
        Sector positive → 10 pts
        Sector flat     → 5 pts
        Sector negative → 0 pts
        """
        # Get sector for this symbol
        sector_query = "SELECT sector FROM stocks WHERE symbol = ?"
        cursor = self.conn.execute(sector_query, (symbol,))
        row = cursor.fetchone()

        if not row or not row["sector"]:
            return 5  # neutral if unknown

        sector = row["sector"]

        # Count positive vs negative days for all stocks in same sector
        trend_query = """
            SELECT
                SUM(CASE WHEN change_pct > 0 THEN 1 ELSE 0 END) as up_days,
                SUM(CASE WHEN change_pct < 0 THEN 1 ELSE 0 END) as down_days
            FROM prices p
            INNER JOIN stocks s ON p.symbol = s.symbol
            WHERE s.sector = ?
            AND p.date >= date('now', '-5 days')
        """
        cursor = self.conn.execute(trend_query, (sector,))
        row = cursor.fetchone()

        if not row or (row["up_days"] is None and row["down_days"] is None):
            return 5

        up = row["up_days"] or 0
        down = row["down_days"] or 0

        if up > down:
            return 10
        elif up == down:
            return 5
        else:
            return 0

    def score_stock(self, stock: dict) -> dict:
        """
        Calculates total momentum score for one stock.
        Returns dict with symbol, individual scores, and total.
        """
        symbol = stock.get("symbol")
        change_7d = stock.get("change_7d_pct")
        volume = stock.get("volume")
        change_pct = stock.get("change_pct")

        s_7d = self.score_7d_return(change_7d)
        s_vol = self.score_volume(symbol, volume)
        s_stab = self.score_stability(change_pct)
        s_sect = self.score_sector_trend(symbol)

        total = s_7d + s_vol + s_stab + s_sect

        return {
            "symbol": symbol,
            "score_7d_return": s_7d,
            "score_volume": s_vol,
            "score_stability": s_stab,
            "score_sector": s_sect,
            "momentum_score": round(total, 2),
        }

    def score_all(self, stocks: list[dict]) -> list[dict]:
        """
        Scores a list of stocks and returns results sorted by
        momentum_score descending.
        """
        results = [self.score_stock(s) for s in stocks]
        return sorted(results, key=lambda x: x["momentum_score"], reverse=True)


if __name__ == "__main__":
    from src.filters.screener import Screener

    screener = Screener()
    eligible = screener.run(verbose=False)

    scorer = MomentumScorer()
    scores = scorer.score_all(eligible)

    print("\n--- Momentum Scores ---")
    print(f"{'Symbol':<15} {'7D':>5} {'Vol':>5} {'Stab':>5} {'Sect':>5} {'TOTAL':>7}")
    print("-" * 50)
    for s in scores:
        print(
            f"{s['symbol']:<15}"
            f"{s['score_7d_return']:>5}"
            f"{s['score_volume']:>5}"
            f"{s['score_stability']:>5}"
            f"{s['score_sector']:>5}"
            f"{s['momentum_score']:>7}"
        )
    print("-" * 50)
