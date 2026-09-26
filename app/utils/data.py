import os
import sys
import sqlite3
import pandas as pd
from datetime import datetime, timezone

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

import config


def safe_num(x, default=0):
    """Coerces None/NaN to default. Plain `x or default` is not enough
    because NaN is truthy and would pass straight through to formatting."""
    try:
        if x is None or pd.isna(x):
            return default
        return x
    except Exception:
        return default


def get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(config.DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def _rows_to_df(cursor) -> pd.DataFrame:
    rows = cursor.fetchall()
    if not rows:
        return pd.DataFrame()
    return pd.DataFrame([dict(r) for r in rows])


def get_latest_market_summary() -> dict:
    conn = get_conn()
    row = conn.execute(
        "SELECT * FROM market_summary ORDER BY date DESC LIMIT 1"
    ).fetchone()
    conn.close()
    return dict(row) if row else {}


def get_market_history(days: int = 30) -> pd.DataFrame:
    conn = get_conn()
    df = pd.read_sql_query(
        """
        SELECT date, asi, pct_change, volume, value, advancers, decliners, unchanged
        FROM market_summary
        ORDER BY date DESC
        LIMIT ?
        """,
        conn, params=(days,)
    )
    conn.close()
    return df.sort_values("date")


def get_latest_scores() -> pd.DataFrame:
    conn = get_conn()
    df = pd.read_sql_query(
        """
        SELECT
            s.symbol,
            s.combined_score,
            s.momentum_score,
            s.dividend_score,
            s.fundamentals_score,
            s.has_fundamentals,
            s.weight_label,
            p.price,
            p.change_pct,
            p.change_7d_pct,
            p.volume,
            p.market_cap,
            st.sector,
            st.market,
            f.eps,
            f.roe,
            f.revenue_growth,
            f.profit_growth,
            f.debt_to_equity
        FROM scores s
        LEFT JOIN prices p ON s.symbol = p.symbol
            AND p.date = (SELECT MAX(date) FROM prices WHERE symbol = s.symbol)
        LEFT JOIN stocks st ON s.symbol = st.symbol
        LEFT JOIN financials f ON f.id = (SELECT MAX(f2.id) FROM financials f2 WHERE f2.symbol = s.symbol)
        WHERE s.date = (SELECT MAX(date) FROM scores)
        ORDER BY s.combined_score DESC
        """,
        conn
    )
    conn.close()
    return df


def get_score_history(symbol: str) -> pd.DataFrame:
    conn = get_conn()
    df = pd.read_sql_query(
        """
        SELECT date, momentum_score, dividend_score, combined_score, fundamentals_score
        FROM scores
        WHERE symbol = ?
        ORDER BY date ASC
        """,
        conn, params=(symbol,)
    )
    conn.close()
    return df


def get_price_history(symbol: str, days: int = 60) -> pd.DataFrame:
    conn = get_conn()
    df = pd.read_sql_query(
        """
        SELECT date, price, volume, change_pct, change_7d_pct
        FROM prices
        WHERE symbol = ?
        ORDER BY date DESC
        LIMIT ?
        """,
        conn, params=(symbol, days)
    )
    conn.close()
    return df.sort_values("date")


def get_dividend_history(symbol: str) -> pd.DataFrame:
    conn = get_conn()
    df = pd.read_sql_query(
        """
        SELECT ex_date, record_date, pay_date, amount, currency
        FROM dividends
        WHERE symbol = ?
        ORDER BY ex_date DESC
        """,
        conn, params=(symbol,)
    )
    conn.close()
    return df


def get_upcoming_dividends(months_ahead: int = 6) -> pd.DataFrame:
    conn = get_conn()
    df = pd.read_sql_query(
        """
        SELECT
            d.symbol,
            d.ex_date,
            d.pay_date,
            d.amount,
            p.price,
            ROUND(d.amount / NULLIF(p.price, 0) * 100, 2) as yield_pct
        FROM dividends d
        LEFT JOIN prices p ON d.symbol = p.symbol
            AND p.date = (SELECT MAX(date) FROM prices WHERE symbol = d.symbol)
        WHERE d.ex_date >= date('now')
        AND d.ex_date <= date('now', '+' || ? || ' months')
        ORDER BY d.ex_date ASC
        """,
        conn, params=(months_ahead,)
    )
    conn.close()
    return df


def get_all_fundamentals() -> pd.DataFrame:
    conn = get_conn()
    df = pd.read_sql_query(
        """
        SELECT
            f.symbol,
            f.period,
            f.eps,
            f.roe,
            f.revenue_growth,
            f.profit_growth,
            f.debt_to_equity,
            p.price
        FROM financials f
        LEFT JOIN prices p ON f.symbol = p.symbol
            AND p.date = (SELECT MAX(date) FROM prices WHERE symbol = f.symbol)
        ORDER BY f.symbol
        """,
        conn
    )
    conn.close()
    return df


def get_all_symbols() -> list:
    conn = get_conn()
    rows = conn.execute(
        "SELECT DISTINCT symbol FROM scores ORDER BY symbol"
    ).fetchall()
    conn.close()
    return [r["symbol"] for r in rows]


def get_sectors() -> list:
    conn = get_conn()
    rows = conn.execute(
        "SELECT DISTINCT sector FROM stocks WHERE sector IS NOT NULL ORDER BY sector"
    ).fetchall()
    conn.close()
    return [r["sector"] for r in rows]