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
from src.scoring.fundamentals import FundamentalsScorer


class Ranker:
    """
    Combines momentum, dividend and fundamentals scores into final combined score.
    Persists scores to database.

    Formula:
    - With fundamentals data:    momentum*0.5 + dividend*0.3 + fundamentals*0.2
    - Without fundamentals data: momentum*0.6 + dividend*0.4 (original weights)
    """

    def __init__(self):
        self.conn = get_connection()
        self.today = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    def run(self, verbose: bool = True) -> list[dict]:
        """
        Full pipeline:
        1. Get eligible stocks from screener
        2. Score momentum, dividend, fundamentals
        3. Combine scores with appropriate weights
        4. Save to scores table
        5. Return ranked list
        """
        # Step 1 — filter
        screener = Screener()
        eligible = screener.run(verbose=False)

        if not eligible:
            print("No eligible stocks. Run market_collector first.")
            return []

        # Step 2 — score all three dimensions
        momentum_scorer = MomentumScorer(conn=self.conn)
        momentum_results = momentum_scorer.score_all(eligible)
        momentum_map = {r["symbol"]: r for r in momentum_results}

        dividend_scorer = DividendScorer(conn=self.conn)
        dividend_results = dividend_scorer.score_all(eligible)
        dividend_map = {r["symbol"]: r for r in dividend_results}

        fundamentals_scorer = FundamentalsScorer(conn=self.conn)
        fundamentals_results = fundamentals_scorer.score_all(eligible)
        fundamentals_map = {r["symbol"]: r for r in fundamentals_results}

        # Step 3 — combine
        combined = []
        for stock in eligible:
            symbol = stock["symbol"]
            price = stock.get("price", 0)

            m_score = momentum_map.get(symbol, {}).get("momentum_score", 0)
            d_score = dividend_map.get(symbol, {}).get("dividend_score", 0)
            f_data = fundamentals_map.get(symbol, {})
            f_score = f_data.get("fundamentals_score", 45)
            has_fundamentals = f_data.get("has_fundamental_data", False)

            # Use different weights depending on data availability
            if has_fundamentals:
                combined_score = round(
                    (m_score * 0.5) +
                    (d_score * 0.3) +
                    (f_score * 0.2),
                    2
                )
                weight_label = "M50+D30+F20"
            else:
                combined_score = round(
                    (m_score * config.MOMENTUM_WEIGHT) +
                    (d_score * config.DIVIDEND_WEIGHT),
                    2
                )
                weight_label = "M60+D40"

            in_range = 1 if config.MIN_PRICE <= price <= config.MAX_PRICE else 0

            combined.append({
                "symbol": symbol,
                "price": price,
                "momentum_score": m_score,
                "dividend_score": d_score,
                "fundamentals_score": f_score,
                "combined_score": combined_score,
                "has_fundamentals": has_fundamentals,
                "weight_label": weight_label,
                "in_price_range": in_range,
                # breakdown
                "score_7d": momentum_map.get(symbol, {}).get("score_7d_return", 0),
                "score_vol": momentum_map.get(symbol, {}).get("score_volume", 0),
                "score_stab": momentum_map.get(symbol, {}).get("score_stability", 0),
                "score_sect": momentum_map.get(symbol, {}).get("score_sector", 0),
                "score_yield": dividend_map.get(symbol, {}).get("score_yield", 0),
                "score_cons": dividend_map.get(symbol, {}).get("score_consistency", 0),
                "score_grow": dividend_map.get(symbol, {}).get("score_growth", 0),
                "score_time": dividend_map.get(symbol, {}).get("score_timing", 0),
                "score_eps": f_data.get("score_eps", 0),
                "score_roe": f_data.get("score_roe", 0),
                "score_revenue": f_data.get("score_revenue", 0),
                "score_profit": f_data.get("score_profit", 0),
            })

        # Sort by combined score
        combined.sort(key=lambda x: x["combined_score"], reverse=True)

        # Step 4 — save to database
        self._save_scores(combined)
        log_run(self.conn, "ranker", "success", len(combined))

        # Step 5 — print and return
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
        print(f"\n{'='*72}")
        print(f"  NGX SCREENER — RANKED WATCHLIST — {self.today}")
        print(f"{'='*72}")
        print(f"{'#':<3} {'Symbol':<12} {'Price':>7} {'Mom':>5} {'Div':>5} {'Fund':>5} {'SCORE':>7} {'Weights'}")
        print(f"{'-'*72}")

        for i, r in enumerate(results, 1):
            fund_str = f"{r['fundamentals_score']}" if r['has_fundamentals'] else "  —"
            print(
                f"{i:<3} "
                f"{r['symbol']:<12} "
                f"₦{r['price']:<6} "
                f"{r['momentum_score']:>5} "
                f"{r['dividend_score']:>5} "
                f"{fund_str:>5} "
                f"{r['combined_score']:>7}  "
                f"{r['weight_label']}"
            )

        print(f"{'='*72}")

        print(f"\nTOP MOMENTUM PLAYS (1-month):")
        momentum_top = sorted(results, key=lambda x: x["momentum_score"], reverse=True)[:5]
        for i, r in enumerate(momentum_top, 1):
            print(f"  {i}. {r['symbol']:<12} mom={r['momentum_score']}  ₦{r['price']}")

        print(f"\nTOP DIVIDEND + GROWTH (long-term):")
        dividend_top = sorted(results, key=lambda x: x["dividend_score"], reverse=True)[:5]
        for i, r in enumerate(dividend_top, 1):
            print(f"  {i}. {r['symbol']:<12} div={r['dividend_score']}  ₦{r['price']}")

        print(f"\nTOP FUNDAMENTALS:")
        fund_top = sorted(
            [r for r in results if r['has_fundamentals']],
            key=lambda x: x["fundamentals_score"],
            reverse=True
        )[:5]
        if fund_top:
            for i, r in enumerate(fund_top, 1):
                print(f"  {i}. {r['symbol']:<12} fund={r['fundamentals_score']}  ₦{r['price']}")
        else:
            print("  No fundamental data yet — run fundamentals.py first")

        print(f"\nHIGH CONVICTION (top momentum + top dividend):")
        top_m_syms = {r["symbol"] for r in momentum_top}
        top_d_syms = {r["symbol"] for r in dividend_top}
        crossover = top_m_syms & top_d_syms
        if crossover:
            for sym in crossover:
                match = next(r for r in results if r["symbol"] == sym)
                flag = " ★ FUND DATA" if match['has_fundamentals'] else ""
                print(f"  ★ {sym:<12} combined={match['combined_score']}  ₦{match['price']}{flag}")
        else:
            print("  None — build more history for stronger signals")

        print()


if __name__ == "__main__":
    ranker = Ranker()
    ranker.run()