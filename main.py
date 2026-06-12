import os
import sys
import argparse
from datetime import datetime, timezone

# Ensure project root is in path
project_root = os.path.abspath(os.path.dirname(__file__))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from src.database.db import init_db
from src.collectors.market_collector import MarketCollector
from src.collectors.dividend_collector import DividendCollector
from src.filters.screener import Screener
from src.scoring.ranker import Ranker
from src.reports.txt_report import generate_report


def run_daily():
    """
    Manual daily run — triggered by you each day.
    1. Fetch latest prices and market overview
    2. Run screener + scoring + ranker
    3. Generate and save daily report
    """
    print("\n" + "="*60)
    print(f"  NGX SCREENER — DAILY RUN")
    print(f"  {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}")
    print("="*60)

    # Step 1 — collect market data
    print("\n[1/3] Collecting market data...")
    collector = MarketCollector()
    collector.run()

    # Step 2 — score and rank
    print("\n[2/3] Scoring and ranking...")
    ranker = Ranker()
    results = ranker.run(verbose=False)

    # Step 3 — generate report
    print("\n[3/3] Generating report...")
    report = generate_report(results)
    print(report)

    print("\nDaily run complete.")


def run_weekly():
    """
    Automatic weekly run — triggered by Windows Task Scheduler.
    Refreshes dividend history for all watchlist stocks.
    Then runs full daily pipeline on top.
    """
    print("\n" + "="*60)
    print(f"  NGX SCREENER — WEEKLY RUN")
    print(f"  {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}")
    print("="*60)

    # Step 1 — refresh dividends
    print("\n[1/4] Refreshing dividend history...")
    div_collector = DividendCollector()
    div_collector.run()

    # Step 2 — collect market data
    print("\n[2/4] Collecting market data...")
    market_collector = MarketCollector()
    market_collector.run()

    # Step 3 — score and rank
    print("\n[3/4] Scoring and ranking...")
    ranker = Ranker()
    results = ranker.run(verbose=False)

    # Step 4 — generate report
    print("\n[4/4] Generating report...")
    report = generate_report(results)
    print(report)

    print("\nWeekly run complete.")


def run_report_only():
    """
    Generates report from existing scores in database.
    No API calls — useful when market is closed.
    """
    print("\nGenerating report from existing data...")
    report = generate_report()
    print(report)


def run_setup():
    """
    First-time setup — initializes database.
    Run this once after cloning the project.
    """
    print("Initializing database...")
    init_db()
    print("Setup complete. Run 'python main.py --daily' to start.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="NGX Screener — Nigerian Stock Market Intelligence"
    )
    parser.add_argument(
        "--mode",
        choices=["daily", "weekly", "report", "setup"],
        default="daily",
        help=(
            "daily  = fetch prices + score + report (run manually each day)\n"
            "weekly = refresh dividends + daily pipeline (run by scheduler)\n"
            "report = generate report from existing DB data (no API calls)\n"
            "setup  = initialize database (run once on first use)"
        )
    )

    args = parser.parse_args()

    if args.mode == "daily":
        run_daily()
    elif args.mode == "weekly":
        run_weekly()
    elif args.mode == "report":
        run_report_only()
    elif args.mode == "setup":
        run_setup()