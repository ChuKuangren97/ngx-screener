import os
import sqlite3
import sys
from datetime import datetime, timezone

# Ensure the project root is in sys.path so 'config' can be imported robustly
# regardless of where the script is executed from within the project structure.
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import config
from src.database.schema import create_tables


def get_connection() -> sqlite3.Connection:
    """
    Returns a sqlite3 connection to DB_PATH.
    Enables WAL (Write-Ahead Logging) mode for better concurrent read performance.
    """
    # Ensure the directory for the database exists
    db_dir = os.path.dirname(config.DB_PATH)
    if db_dir and not os.path.exists(db_dir):
        os.makedirs(db_dir, exist_ok=True)

    conn = sqlite3.connect(config.DB_PATH)

    # Enable WAL mode for performance
    conn.execute("PRAGMA journal_mode=WAL;")

    # Set row factory to sqlite3.Row so we can easily convert results to dictionaries
    conn.row_factory = sqlite3.Row

    return conn


def init_db() -> None:
    """
    Calls get_connection() then create_tables(conn).
    Logs "Database initialized" to console.
    """
    conn = get_connection()
    create_tables(conn)
    conn.close()
    print("Database initialized")


def insert_stocks(conn: sqlite3.Connection, stocks: list[dict]) -> None:
    """
    Upserts into the stocks table.
    Sets last_updated to current UTC timestamp.
    Uses INSERT OR REPLACE to update existing records.
    """
    if not stocks:
        return

    now = datetime.now(timezone.utc).isoformat()

    query = """
        INSERT OR REPLACE INTO stocks
        (symbol, name, sector, market, shares_outstanding, last_updated)
        VALUES (?, ?, ?, ?, ?, ?)
    """

    # Extract required fields from each stock dict
    data = [
        (
            stock.get("symbol"),
            stock.get("name"),
            stock.get("sector"),
            stock.get("market"),
            stock.get("shares_outstanding"),
            now,
        )
        for stock in stocks
    ]

    conn.executemany(query, data)
    conn.commit()


def insert_prices(conn: sqlite3.Connection, prices: list[dict]) -> None:
    """
    Inserts into the prices table.
    Uses INSERT OR IGNORE to skip duplicates (based on UNIQUE constraint on symbol+date).
    Maps sample API fields to DB columns.
    """
    if not prices:
        return

    query = """
        INSERT OR IGNORE INTO prices
        (symbol, date, price, prev_close, change_pct, change_7d_pct, volume, market_cap, pe_ratio)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """

    data = []
    for p in prices:
        # Map API fields to DB fields gracefully
        symbol = p.get("symbol")

        # Parse trade_date (handles ISO format strings with or without time)
        date_str = p.get("trade_date", p.get("date", ""))
        if date_str and "T" in str(date_str):
            date_str = str(date_str).split("T")[0]

        data.append(
            (
                symbol,
                date_str,
                p.get("current_price", p.get("price")),
                p.get("previous_close", p.get("prev_close")),
                p.get("change_percent", p.get("change_pct")),
                p.get("pct_change_7d", p.get("change_7d_pct")),
                p.get("volume"),
                p.get("market_cap"),
                p.get("pe_ratio"),  # Handles None/null gracefully
            )
        )

    conn.executemany(query, data)
    conn.commit()


def insert_market_summary(conn: sqlite3.Connection, summary: dict) -> None:
    """
    Inserts daily market summary.
    Uses INSERT OR REPLACE (date is Primary Key).
    """
    query = """
        INSERT OR REPLACE INTO market_summary
        (date, asi, pct_change, volume, value, market_cap, advancers, decliners, unchanged)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """

    # Try to extract fields matching the schema
    date_str = summary.get("date", summary.get("trade_date", ""))
    if date_str and "T" in str(date_str):
        date_str = str(date_str).split("T")[0]

    data = (
        date_str,
        summary.get("asi"),
        summary.get("pct_change"),
        summary.get("volume"),
        summary.get("value"),
        summary.get("market_cap"),
        summary.get("advancers"),
        summary.get("decliners"),
        summary.get("unchanged"),
    )

    conn.execute(query, data)
    conn.commit()


def insert_dividends(
    conn: sqlite3.Connection, symbol: str, dividends: list[dict]
) -> None:
    """
    Inserts dividend history for one stock.
    Uses INSERT OR IGNORE to skip duplicates (based on UNIQUE constraint on symbol+ex_date).
    """
    if not dividends:
        return

    query = """
        INSERT OR IGNORE INTO dividends
        (symbol, ex_date, record_date, pay_date, amount, currency)
        VALUES (?, ?, ?, ?, ?, ?)
    """

    data = []
    for d in dividends:
        # Map API dividend fields to DB columns
        data.append(
            (
                symbol,
                d.get("ex_dividend_date", d.get("ex_date")),
                d.get("record_date"),
                d.get("pay_date"),
                d.get("dividend_per_share", d.get("amount")),
                d.get("currency"),
            )
        )

    conn.executemany(query, data)
    conn.commit()


def log_run(
    conn: sqlite3.Connection, stage: str, status: str, records: int, error: str = None
) -> None:
    """
    Inserts one row into run_log with current UTC timestamp.
    """
    query = """
        INSERT INTO run_log (timestamp, stage, status, records_affected, error)
        VALUES (?, ?, ?, ?, ?)
    """

    now = datetime.now(timezone.utc).isoformat()
    conn.execute(query, (now, stage, status, records, error))
    conn.commit()


def get_prices(conn: sqlite3.Connection, symbol: str, days: int = 30) -> list[dict]:
    """
    Returns last N days of prices for a given symbol.
    Ordered by date DESC.
    """
    query = """
        SELECT * FROM prices
        WHERE symbol = ?
        ORDER BY date DESC
        LIMIT ?
    """
    cursor = conn.execute(query, (symbol, days))
    # Convert sqlite3.Row objects to standard dictionaries
    return [dict(row) for row in cursor.fetchall()]


def get_dividends(conn: sqlite3.Connection, symbol: str) -> list[dict]:
    """
    Returns all dividend history for a symbol.
    Ordered by ex_date DESC.
    """
    query = """
        SELECT * FROM dividends
        WHERE symbol = ?
        ORDER BY ex_date DESC
    """
    cursor = conn.execute(query, (symbol,))
    return [dict(row) for row in cursor.fetchall()]


def get_all_scores(conn: sqlite3.Connection, date: str) -> list[dict]:
    """
    Returns all scores for a given date.
    Ordered by combined_score DESC.
    """
    query = """
        SELECT * FROM scores
        WHERE date = ?
        ORDER BY combined_score DESC
    """
    cursor = conn.execute(query, (date,))
    return [dict(row) for row in cursor.fetchall()]
