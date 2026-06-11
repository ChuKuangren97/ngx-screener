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
from src.database.db import (
    get_connection,
    insert_market_summary,
    insert_prices,
    insert_stocks,
    log_run,
)


class MarketCollector:
    """
    Fetches daily stock prices and market overview from NGX Pulse API
    and persists them into the local SQLite database.
    """

    def __init__(self):
        self.headers = {"X-API-Key": config.NGX_API_KEY, "Accept": "application/json"}
        self.conn = get_connection()
        print("MarketCollector initialized.")

    def fetch_all_stocks(self) -> dict:
        url = f"{config.NGX_API_BASE}/api/ngxdata/stocks"
        try:
            print(f"Fetching all stocks from {url}...")
            response = requests.get(url, headers=self.headers, timeout=30)
            response.raise_for_status()
            data = response.json()

            os.makedirs(config.SNAPSHOT_DIR, exist_ok=True)
            today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
            snapshot_path = os.path.join(config.SNAPSHOT_DIR, f"{today}.json")
            with open(snapshot_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
            print(f"Saved snapshot to {snapshot_path}")
            return data

        except Exception as e:
            error_msg = f"Failed to fetch all stocks: {str(e)}"
            print(f"ERROR: {error_msg}")
            log_run(self.conn, "fetch_all_stocks", "error", 0, error_msg)
            return None

    def fetch_market_overview(self) -> dict:
        url = f"{config.NGX_API_BASE}/api/ngxdata/market"
        try:
            print(f"Fetching market overview from {url}...")
            response = requests.get(url, headers=self.headers, timeout=30)
            response.raise_for_status()
            data = response.json()

            if data.get("success") and "data" in data:
                return data["data"]
            else:
                raise ValueError("Unexpected response format or success=false")

        except Exception as e:
            error_msg = f"Failed to fetch market overview: {str(e)}"
            print(f"ERROR: {error_msg}")
            log_run(self.conn, "fetch_market_overview", "error", 0, error_msg)
            return None

    def run(self) -> None:
        print("\n--- Starting Market Collection Run ---")
        try:
            stocks_data = self.fetch_all_stocks()
            time.sleep(0.5)
            market_data = self.fetch_market_overview()
            time.sleep(0.5)

            if not stocks_data or "stocks" not in stocks_data:
                log_run(self.conn, "run", "error", 0, "No stocks data available")
                print("CRITICAL: No stocks data fetched. Aborting run.")
                return

            stocks_list = stocks_data["stocks"]

            # Strip time component from trade_date
            for stock in stocks_list:
                if (
                    "trade_date" in stock
                    and isinstance(stock["trade_date"], str)
                    and "T" in stock["trade_date"]
                ):
                    stock["trade_date"] = stock["trade_date"].split("T")[0]

            print(f"\nInserting {len(stocks_list)} stocks into database...")
            insert_stocks(self.conn, stocks_list)
            log_run(self.conn, "insert_stocks", "success", len(stocks_list))

            print(f"Inserting prices for {len(stocks_list)} stocks...")
            insert_prices(self.conn, stocks_list)
            log_run(self.conn, "insert_prices", "success", len(stocks_list))

            if market_data:
                summary_payload = market_data.copy()
                if "date" not in summary_payload:
                    trade_date_str = summary_payload.get("trade_date", "")
                    if isinstance(trade_date_str, str) and "T" in trade_date_str:
                        summary_payload["date"] = trade_date_str.split("T")[0]
                    elif trade_date_str:
                        summary_payload["date"] = trade_date_str
                    else:
                        summary_payload["date"] = datetime.now(timezone.utc).strftime(
                            "%Y-%m-%d"
                        )

                print("Inserting market summary...")
                insert_market_summary(self.conn, summary_payload)
                log_run(self.conn, "insert_market_summary", "success", 1)
            else:
                print("Warning: No market data to insert.")
                log_run(
                    self.conn, "insert_market_summary", "skipped", 0, "No market data"
                )

            print("\n--- Collection Summary ---")
            print(f"Stocks inserted/updated: {len(stocks_list)}")
            if market_data:
                print(f"Market Status: {market_data.get('market_status', 'Unknown')}")
                print(f"ASI Value:     {market_data.get('asi', 'N/A')}")
            print("--------------------------\n")

        except Exception as e:
            error_msg = f"Run failed: {str(e)}"
            print(f"CRITICAL ERROR: {error_msg}")
            log_run(self.conn, "run", "error", 0, error_msg)
        finally:
            if self.conn:
                self.conn.close()
                print("Database connection closed.")


if __name__ == "__main__":
    collector = MarketCollector()
    collector.run()
