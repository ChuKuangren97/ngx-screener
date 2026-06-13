import os
import sys

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from src.database.db import get_connection


class FundamentalsScorer:
    """
    Scores stocks based on extracted financial fundamentals.

    Scoring breakdown (0-100):
    - EPS growth YoY:      0-30 pts
    - ROE:                 0-25 pts
    - Revenue growth:      0-25 pts
    - Profit growth:       0-20 pts
    """

    def __init__(self, conn=None):
        self.conn = conn or get_connection()

    def get_financials(self, symbol: str) -> dict:
        """Returns most recent financials for a symbol."""
        query = """
            SELECT * FROM financials
            WHERE symbol = ?
            ORDER BY extracted_at DESC
            LIMIT 1
        """
        cursor = self.conn.execute(query, (symbol,))
        row = cursor.fetchone()
        return dict(row) if row else {}

    def score_eps_growth(self, financials: dict) -> float:
        """
        Scores EPS trend.
        No EPS data        → 15 pts (neutral)
        EPS growing        → 30 pts
        EPS flat (<5% chg) → 15 pts
        EPS declining      → 0 pts
        Deeply negative    → 0 pts (loss-making)
        """
        eps = financials.get('eps')
        profit_growth = financials.get('profit_growth')

        if eps is None and profit_growth is None:
            return 15  # neutral — no data

        if eps is not None and eps < 0:
            return 0  # loss-making

        if profit_growth is not None:
            if profit_growth > 5:
                return 30
            elif profit_growth >= -5:
                return 15
            else:
                return 0

        return 15  # neutral fallback

    def score_roe(self, financials: dict) -> float:
        """
        Scores Return on Equity.
        No data  → 10 pts (neutral)
        >=25%    → 25 pts
        15-25%   → 18 pts
        10-15%   → 10 pts
        5-10%    → 5 pts
        <5%      → 0 pts
        """
        roe = financials.get('roe')

        if roe is None:
            return 10  # neutral

        if roe >= 25:
            return 25
        elif roe >= 15:
            return 18
        elif roe >= 10:
            return 10
        elif roe >= 5:
            return 5
        else:
            return 0

    def score_revenue_growth(self, financials: dict) -> float:
        """
        Scores revenue growth YoY.
        No data   → 10 pts (neutral)
        >=20%     → 25 pts
        10-20%    → 18 pts
        0-10%     → 10 pts
        negative  → 0 pts
        """
        rev_growth = financials.get('revenue_growth')

        if rev_growth is None:
            return 10  # neutral

        if rev_growth >= 20:
            return 25
        elif rev_growth >= 10:
            return 18
        elif rev_growth >= 0:
            return 10
        else:
            return 0

    def score_profit_growth(self, financials: dict) -> float:
        """
        Scores profit after tax growth YoY.
        No data        → 10 pts (neutral)
        >=20% growth   → 20 pts
        0-20% growth   → 12 pts
        -20 to 0%      → 5 pts
        < -20%         → 0 pts
        """
        profit_growth = financials.get('profit_growth')

        if profit_growth is None:
            return 10  # neutral

        if profit_growth >= 20:
            return 20
        elif profit_growth >= 0:
            return 12
        elif profit_growth >= -20:
            return 5
        else:
            return 0

    def score_stock(self, stock: dict) -> dict:
        """Calculates total fundamentals score for one stock."""
        symbol = stock.get('symbol')
        financials = self.get_financials(symbol)

        s_eps = self.score_eps_growth(financials)
        s_roe = self.score_roe(financials)
        s_rev = self.score_revenue_growth(financials)
        s_pat = self.score_profit_growth(financials)

        total = s_eps + s_roe + s_rev + s_pat
        has_data = bool(financials)

        return {
            'symbol': symbol,
            'score_eps': s_eps,
            'score_roe': s_roe,
            'score_revenue': s_rev,
            'score_profit': s_pat,
            'fundamentals_score': round(total, 2),
            'has_fundamental_data': has_data
        }

    def score_all(self, stocks: list[dict]) -> list[dict]:
        """Scores list of stocks, returns sorted by fundamentals_score desc."""
        results = [self.score_stock(s) for s in stocks]
        return sorted(results, key=lambda x: x['fundamentals_score'], reverse=True)


if __name__ == "__main__":
    from src.filters.screener import Screener
    from src.ai.qwen_extractor import QwenExtractor
    from src.database.db import get_connection, insert_financials

    # First load extracted data into database
    print("Loading extracted financials into database...")
    conn = get_connection()
    extractor = QwenExtractor()
    pdf_map = extractor.auto_build_pdf_map()
    results = extractor.extract_all(pdf_map)

    for symbol, data in results.items():
        insert_financials(conn, data)
        print(f"  Inserted {symbol} financials")
    conn.close()

    # Then score
    screener = Screener()
    eligible = screener.run(verbose=False)

    scorer = FundamentalsScorer()
    scores = scorer.score_all(eligible)

    print(f"\n--- Fundamentals Scores ---")
    print(f"{'Symbol':<15} {'EPS':>5} {'ROE':>5} {'Rev':>5} {'PAT':>5} {'TOTAL':>7} {'Data':>6}")
    print("-" * 55)
    for s in scores:
        print(
            f"{s['symbol']:<15}"
            f"{s['score_eps']:>5}"
            f"{s['score_roe']:>5}"
            f"{s['score_revenue']:>5}"
            f"{s['score_profit']:>5}"
            f"{s['fundamentals_score']:>7}"
            f"  {'✓' if s['has_fundamental_data'] else '—':>4}"
        )