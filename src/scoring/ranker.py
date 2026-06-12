import os
import sys
from datetime import datetime, timezone

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

import config
from src.database.db import get_connection, log_run
from src.filters.screener import Screener
from src.scoring.momentum import MomentumScorer
from src.scoring.dividend import DividendScorer


class Ranker:
    """
    Combines momentum and dividend scores into a final combined score.
    Persists scores to the database.

    Formula: combined = (momentum * 0.6) + (dividend * 0.4)
    """

    def __init__(self):
        self.conn = get_connection()
        self.today = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    def run(self, verbose: bool = True) -> list[dict]:
        """
        Full pipeline:
        1. Get eligible stocks from screener
        2. Score momentum
        3. Score dividends
        4. Combine scores
        5. Save to scores table
        6. Return ranked list
        """
        # Step 1 — filter
        screener = Screener()
        eligible = screener.run(verbose=False)

        if not eligible:
            print("No eligible stocks found. Run market_collector first.")
            return []

        # Step 2 — momentum scores (keyed by symbol)
        momentum_scorer = MomentumScorer(conn=self.conn)
        momentum_results = momentum_scorer.score_all(eligible)
        momentum_map = {r["symbol"]: r for r in momentum_results}

        # Step 3 — dividend scores (keyed by symbol)
        dividend_scorer = DividendScorer(conn=self.conn)
        dividend_results = dividend_scorer.score_all(eligible)
        dividend_map = {r["symbol"]: r for r in dividend_results}

        # Step 4 — combine
        combined = []
        for stock in eligible:
            symbol = stock["symbol"]
            price = stock.get("price", 0)

            m_score = momentum_map.get(symbol, {}).get("momentum_score", 0)
            d_score = dividend_map.get(symbol, {}).get("dividend_score", 0)

            combined_score = round(
                (m_score * config.MOMENTUM_WEIGHT) +
                (d_score * config.DIVIDEND_WEIGHT),
                2
            )

            in_range = 1 if config.MIN_PRICE <= price <= config.MAX_PRICE else 0

            combined.append({
                "symbol": symbol,
                "price": price,
                "momentum_score": m_score,
                "dividend_score": d_score,
                "combined_score": combined_score,
                "in_price_range": in_range,
                # breakdown for display
                "score_7d": momentum_map.get(symbol, {}).get("score_7d_return", 0),
                "score_vol": momentum_map.get(symbol, {}).get("score_volume", 0),
                "score_stab": momentum_map.get(symbol, {}).get("score_stability", 0),
                "score_sect": momentum_map.get(symbol, {}).get("score_sector", 0),
                "score_yield": dividend_map.get(symbol, {}).get("score_yield", 0),
                "score_cons": dividend_map.get(symbol, {}).get("score_consistency", 0),
                "score_grow": dividend_map.get(symbol, {}).get("score_growth", 0),
                "score_time": dividend_map.get(symbol, {}).get("score_timing", 0),
            })

        # Sort by combined score
        combined.sort(key=lambda x: x["combined_score"], reverse=True)

        # Step 5 — save to database
        self._save_scores(combined)
        log_run(self.conn, "ranker", "success", len(combined))

        # Step 6 — print and return
        if verbose:
            self._print_results(combined)

        self.conn.close()
        return combined

    def _save_scores(self, results: list[dict]) -> None:
        """Persists combined scores to the scores table."""
        query = """
            INSERT OR REPLACE INTO scores
            (symbol, date, momentum_score, dividend_score, combined_score, in_price_range)
            VALUES (?, ?, ?, ?, ?, ?)
        """
        data = [
            (
                r["symbol"],
                self.today,
                r["momentum_score"],
                r["dividend_score"],
                r["combined_score"],
                r["in_price_range"]
            )
            for r in results
        ]
        self.conn.executemany(query, data)
        self.conn.commit()

    def _print_results(self, results: list[dict]) -> None:
        """Prints formatted ranked table to terminal."""
        print(f"\n{'='*65}")
        print(f"  NGX SCREENER — RANKED WATCHLIST — {self.today}")
        print(f"{'='*65}")
        print(f"{'#':<3} {'Symbol':<12} {'Price':>7} {'Mom':>5} {'Div':>5} {'SCORE':>7}")
        print(f"{'-'*65}")

        for i, r in enumerate(results, 1):
            print(
                f"{i:<3} "
                f"{r['symbol']:<12} "
                f"₦{r['price']:<6} "
                f"{r['momentum_score']:>5} "
                f"{r['dividend_score']:>5} "
                f"{r['combined_score']:>7}"
            )

        print(f"{'='*65}")
        print(f"\nTOP MOMENTUM PLAYS (1-month):")
        momentum_top = sorted(results, key=lambda x: x["momentum_score"], reverse=True)[:5]
        for i, r in enumerate(momentum_top, 1):
            print(f"  {i}. {r['symbol']:<12} momentum={r['momentum_score']}  price=₦{r['price']}")

        print(f"\nTOP DIVIDEND + GROWTH (long-term):")
        dividend_top = sorted(results, key=lambda x: x["dividend_score"], reverse=True)[:5]
        for i, r in enumerate(dividend_top, 1):
            print(f"  {i}. {r['symbol']:<12} dividend={r['dividend_score']}  price=₦{r['price']}")

        print(f"\nHIGH CONVICTION (both lists):")
        top_symbols_m = {r["symbol"] for r in momentum_top}
        top_symbols_d = {r["symbol"] for r in dividend_top}
        crossover = top_symbols_m & top_symbols_d
        if crossover:
            for sym in crossover:
                match = next(r for r in results if r["symbol"] == sym)
                print(f"  ★ {sym:<12} combined={match['combined_score']}  price=₦{match['price']}")
        else:
            print("  None yet — build more history for stronger signals")

        print()


if __name__ == "__main__":
    ranker = Ranker()
    ranker.run()