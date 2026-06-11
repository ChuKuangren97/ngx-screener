import json
import os
import sys
import time
from datetime import datetime, timezone

import requests

# Robust sys.path handling
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

import config
from src.database.db import get_connection, insert_dividends, log_run


class DividendCollector:
    """
    Fetches dividend history per stock from NGX Pulse API.
    Rate-limit aware: stays within 100 req/day by caching results
    and only re-fetching when cache is stale (older than 7 days).
    """

    def __init__(self):
        self.headers = {"X-API-Key": config.NGX_API_KEY, "Accept": "application/json"}
        self.conn = get_connection()
        self.request_count = 0
        self.MAX_REQUESTS = 90  # leave 10 buffer for other collectors
        print("DividendCollector initialized.")

    def _get_cache_path(self, symbol: str) -> str:
        """Returns path to cached dividend JSON for a symbol."""
        os.makedirs(config.DIVIDEND_DIR, exist_ok=True)
        return os.path.join(config.DIVIDEND_DIR, f"{symbol}.json")

    def _is_cache_fresh(self, symbol: str, max_age_days: int = 7) -> bool:
        """
        Returns True if cached file exists and is less than max_age_days old.
        Prevents re-fetching dividend history that hasn't changed.
        """
        cache_path = self._get_cache_path(symbol)
        if not os.path.exists(cache_path):
            return False
        file_age_seconds = time.time() - os.path.getmtime(cache_path)
        file_age_days = file_age_seconds / 86400
        return file_age_days < max_age_days

    def _load_cache(self, symbol: str) -> list:
        """Loads dividend history from local cache file."""
        cache_path = self._get_cache_path(symbol)
        try:
            with open(cache_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data.get("history", [])
        except Exception:
            return []

    def _save_cache(self, symbol: str, data: dict) -> None:
        """Saves raw API response to cache file."""
        cache_path = self._get_cache_path(symbol)
        with open(cache_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

    def fetch_dividends_for_symbol(self, symbol: str) -> list:
        """
        Fetches dividend history for one symbol.
        Uses cache if fresh, otherwise calls API.
        Returns list of dividend dicts or empty list on failure.
        """
        if self._is_cache_fresh(symbol):
            print(f"  [{symbol}] Using cached data")
            return self._load_cache(symbol)

        if self.request_count >= self.MAX_REQUESTS:
            print(
                f"  [{symbol}] Skipping — daily request limit reached ({self.MAX_REQUESTS})"
            )
            return self._load_cache(symbol)

        url = f"{config.NGX_API_BASE}/api/ngxdata/dividends/{symbol}"
        try:
            response = requests.get(url, headers=self.headers, timeout=30)
            self.request_count += 1
            response.raise_for_status()
            data = response.json()

            if data.get("success"):
                self._save_cache(symbol, data)
                history = data.get("history", [])
                print(f"  [{symbol}] Fetched {len(history)} dividend records")
                return history
            else:
                print(f"  [{symbol}] API returned success=false")
                return []

        except Exception as e:
            print(f"  [{symbol}] ERROR: {str(e)}")
            log_run(self.conn, f"fetch_dividends_{symbol}", "error", 0, str(e))
            return []

    def run(self, symbols: list = None) -> None:
        """
        Fetches and stores dividend history for a list of symbols.
        Defaults to WATCHLIST from config if no symbols provided.
        Adds 1s delay between API calls to respect rate limits.
        """
        if symbols is None:
            symbols = config.WATCHLIST

        print(f"\n--- Starting Dividend Collection ({len(symbols)} stocks) ---")
        total_records = 0
        failed = []

        for i, symbol in enumerate(symbols):
            print(f"[{i + 1}/{len(symbols)}] {symbol}")
            try:
                history = self.fetch_dividends_for_symbol(symbol)

                if history:
                    insert_dividends(self.conn, symbol, history)
                    total_records += len(history)
                    log_run(self.conn, f"dividends_{symbol}", "success", len(history))
                else:
                    log_run(self.conn, f"dividends_{symbol}", "empty", 0)

                # Only sleep if we actually made an API call (not cached)
                if not self._is_cache_fresh(symbol):
                    time.sleep(1.0)

            except Exception as e:
                error_msg = str(e)
                print(f"  [{symbol}] FAILED: {error_msg}")
                log_run(self.conn, f"dividends_{symbol}", "error", 0, error_msg)
                failed.append(symbol)

        print(f"\n--- Dividend Collection Summary ---")
        print(f"Symbols processed: {len(symbols)}")
        print(f"Total records inserted: {total_records}")
        print(f"API requests used: {self.request_count}")
        print(f"Failed: {failed if failed else 'None'}")
        print(f"-----------------------------------\n")

        log_run(self.conn, "dividend_collection_run", "success", total_records)

        if self.conn:
            self.conn.close()
            print("Database connection closed.")


if __name__ == "__main__":
    collector = DividendCollector()
    collector.run()
