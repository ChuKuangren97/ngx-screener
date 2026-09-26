import sqlite3


def create_tables(conn: sqlite3.Connection):
    """
    Creates all required SQLite tables if they do not already exist.
    This function is idempotent and safe to call multiple times.
    """
    cursor = conn.cursor()

    # stocks table: Basic information about each listed stock
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS stocks (
            symbol TEXT PRIMARY KEY,
            name TEXT,
            sector TEXT,
            market TEXT,
            shares_outstanding INTEGER,
            last_updated TEXT
        )
    """)

    # prices table: Daily price and volume data
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS prices (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            symbol TEXT NOT NULL,
            date TEXT NOT NULL,
            price REAL,
            prev_close REAL,
            change_pct REAL,
            change_7d_pct REAL,
            volume INTEGER,
            market_cap REAL,
            pe_ratio REAL,
            UNIQUE(symbol, date)
        )
    """)

    # dividends table: Historical dividend payouts
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS dividends (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            symbol TEXT NOT NULL,
            ex_date TEXT NOT NULL,
            record_date TEXT,
            pay_date TEXT,
            amount REAL,
            currency TEXT,
            UNIQUE(symbol, ex_date)
        )
    """)

    # financials table: Extracted fundamental metrics from PDFs
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS financials (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            symbol TEXT NOT NULL,
            period TEXT,
            eps REAL,
            roe REAL,
            revenue_growth REAL,
            profit_growth REAL,
            debt_to_equity REAL,
            source_pdf TEXT,
            extracted_at TEXT
        )
    """)

    # scores table: Calculated momentum and dividend scores
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS scores (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            symbol TEXT NOT NULL,
            date TEXT NOT NULL,
            momentum_score REAL,
            dividend_score REAL,
            combined_score REAL,
            in_price_range INTEGER,
            UNIQUE(symbol, date)
        )
    """)

    # market_summary table: Daily overall market statistics
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS market_summary (
            date TEXT PRIMARY KEY,
            asi REAL,
            pct_change REAL,
            volume INTEGER,
            value REAL,
            market_cap REAL,
            advancers INTEGER,
            decliners INTEGER,
            unchanged INTEGER
        )
    """)

    # run_log table: Audit trail for pipeline execution
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS run_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT,
            stage TEXT,
            status TEXT,
            records_affected INTEGER,
            error TEXT
        )
    """)

    # Idempotent migration — add fundamentals columns to scores if missing
    existing_cols = [row[1] for row in conn.execute("PRAGMA table_info(scores)").fetchall()]
    if "fundamentals_score" not in existing_cols:
        conn.execute("ALTER TABLE scores ADD COLUMN fundamentals_score REAL DEFAULT 45")
    if "has_fundamentals" not in existing_cols:
        conn.execute("ALTER TABLE scores ADD COLUMN has_fundamentals INTEGER DEFAULT 0")
    if "weight_label" not in existing_cols:
        conn.execute("ALTER TABLE scores ADD COLUMN weight_label TEXT DEFAULT 'M60+D40'")
    conn.commit()

    # Deduplicate financials (keep latest row per symbol+period) so
    # INSERT OR REPLACE can work, then enforce uniqueness going forward
    conn.execute("""
        DELETE FROM financials
        WHERE id NOT IN (
            SELECT MAX(id) FROM financials GROUP BY symbol, period
        )
    """)
    conn.execute("""
        CREATE UNIQUE INDEX IF NOT EXISTS idx_financials_symbol_period
        ON financials(symbol, period)
    """)
    conn.commit()

    # Commit all table creations
    conn.commit()
