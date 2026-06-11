import os
import sys

# Robust sys.path handling
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

import config
from src.database.db import get_connection


class Screener:
    """
    Filters all stocks in the database against configured thresholds.
    Returns only stocks eligible for scoring.

    Filters applied:
    - Price between MIN_PRICE and MAX_PRICE (₦50-700)
    - Volume >= MIN_VOLUME (500,000 shares/day)
    - Market cap >= MIN_MARKET_CAP (₦50 billion)
    - Daily swing <= MAX_DAILY_SWING (10% max move)
    - Excludes null volume stocks
    """

    def __init__(self):
        self.conn = get_connection()

    def get_latest_prices(self) -> list[dict]:
        """
        Pulls the most recent price row for every stock from the database.
        Uses a subquery to get the latest date per symbol.
        """
        query = """
            SELECT p.*
            FROM prices p
            INNER JOIN (
                SELECT symbol, MAX(date) as max_date
                FROM prices
                GROUP BY symbol
            ) latest ON p.symbol = latest.symbol AND p.date = latest.max_date
        """
        cursor = self.conn.execute(query)
        return [dict(row) for row in cursor.fetchall()]

    def apply_filters(self, stocks: list[dict]) -> list[dict]:
        """
        Applies all screener filters to a list of stock price dicts.
        Returns only stocks that pass every filter.
        Logs reason for exclusion if in debug mode.
        """
        passed = []
        excluded = {}

        for s in stocks:
            symbol = s.get("symbol", "UNKNOWN")
            price = s.get("price") or 0
            volume = s.get("volume")
            market_cap = s.get("market_cap") or 0
            change_pct = s.get("change_pct")

            # Filter: null volume
            if config.EXCLUDE_NULL_VOLUME and volume is None:
                excluded[symbol] = "null volume"
                continue

            # Filter: price range
            if price < config.MIN_PRICE:
                excluded[symbol] = f"price ₦{price} below ₦{config.MIN_PRICE}"
                continue

            if price > config.MAX_PRICE:
                excluded[symbol] = f"price ₦{price} above ₦{config.MAX_PRICE}"
                continue

            # Filter: minimum volume
            if volume is not None and volume < config.MIN_VOLUME:
                excluded[symbol] = f"volume {volume:,} below {config.MIN_VOLUME:,}"
                continue

            # Filter: minimum market cap
            if market_cap < config.MIN_MARKET_CAP:
                excluded[symbol] = f"market cap ₦{market_cap / 1e9:.1f}B below ₦50B"
                continue

            # Filter: daily swing (absolute value of change_pct)
            if change_pct is not None:
                if abs(change_pct) > config.MAX_DAILY_SWING * 100:
                    excluded[symbol] = f"daily swing {change_pct:.1f}% exceeds 10%"
                    continue

            passed.append(s)

        return passed, excluded

    def run(self, verbose: bool = True) -> list[dict]:
        """
        Pulls latest prices, applies filters, returns eligible stocks.
        Prints summary of passed/excluded counts.
        """
        all_stocks = self.get_latest_prices()

        if not all_stocks:
            print("No price data in database. Run market_collector first.")
            self.conn.close()
            return []

        passed, excluded = self.apply_filters(all_stocks)

        if verbose:
            print(f"\n--- Screener Results ---")
            print(f"Total stocks in DB:  {len(all_stocks)}")
            print(f"Passed filters:      {len(passed)}")
            print(f"Excluded:            {len(excluded)}")
            print(f"\nEligible stocks:")
            for s in passed:
                print(f"  {s['symbol']:<15} ₦{s['price']:<8} vol:{s['volume']:>12,}")
            print(f"\nExcluded (sample — first 10):")
            for sym, reason in list(excluded.items())[:10]:
                print(f"  {sym:<15} {reason}")
            print(f"------------------------\n")

        self.conn.close()
        return passed


if __name__ == "__main__":
    screener = Screener()
    screener.run(verbose=True)
