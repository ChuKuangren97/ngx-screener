# NGX Screener

A personal Nigerian stock market intelligence system that automatically collects, scores, and ranks NGX-listed stocks for short-term momentum plays and long-term dividend investing.

Built with Python, SQLite, and the NGX Pulse API. Designed for retail investors who want data-driven watchlists without paying for Bloomberg or manual spreadsheet work.

---

## What It Does

Every day you run one command. The system:

1. Fetches live prices and market data for all 146 NGX-listed stocks
2. Filters out stocks outside your criteria (price range, liquidity, volatility)
3. Scores every eligible stock on momentum and dividend potential
4. Ranks them and generates a plain-text report

Every week it automatically refreshes dividend history for all watchlist stocks.

---

## Scoring System

### Momentum Score (0–100)
Weighted 60% of combined score. Targets 1-month setups.

| Component | Max Points | Logic |
|---|---|---|
| 7-day return | 40 | ≥10% = 40, 5–10% = 25, 0–5% = 10, negative = 0 |
| Volume vs 30-day avg | 30 | >2x = 30, 1.5x = 20, 1x = 10, <1x = 0 |
| Price stability | 20 | Inverse of daily swing — lower swing = higher score |
| Sector trend | 10 | Net advancers in sector this week |

### Dividend Score (0–100)
Weighted 40% of combined score. Targets 2–5 month holds and income.

| Component | Max Points | Logic |
|---|---|---|
| Trailing 12-month yield | 40 | ≥8% = 40, 5–8% = 28, 3–5% = 15, <3% = 5 |
| Payout consistency | 30 | 5+ years paying = 30, 3–4 = 20, 1–2 = 10 |
| DPS growth trend | 20 | Growing YoY = 20, flat = 10, declining = 0 |
| Payout timing | 10 | Ex-date within 6 months = 10, 6–12 = 5, >12 = 0 |

### Combined Score
```
combined = (momentum × 0.6) + (dividend × 0.4)
```

---

## Screener Filters

Stocks must pass all filters before scoring:

| Filter | Value | Reason |
|---|---|---|
| Price range | ₦50 – ₦700 | Affordable for retail capital |
| Minimum daily volume | 500,000 shares | Ensures liquidity to enter/exit |
| Minimum market cap | ₦50 billion | Excludes micro-caps and shells |
| Maximum daily swing | 10% | Excludes erratic/manipulated stocks |
| Null volume | Excluded | Stocks with no trading activity |

Out of 146 listed stocks, roughly 15–20 pass filters at any given time.

---

## Data Sources

| Source | What it provides | Method |
|---|---|---|
| NGX Pulse API | Live prices, volume, market overview, dividend history | Free API (100 req/day) |
| Company IR pages | Quarterly and annual report PDFs | Download + Qwen extraction (Phase 2) |

NGX Pulse free tier: 10 requests/minute, 100 requests/day. The daily run uses ~3 requests. The weekly dividend refresh uses ~10.

---

## Project Structure

```
ngx-screener/
│
├── main.py                        # Entry point — all run modes
├── config.py                      # API keys, filters, constants (gitignored)
├── requirements.txt
│
├── data/
│   ├── snapshots/                 # Daily JSON from /stocks endpoint
│   ├── dividends/                 # Per-stock dividend cache (JSON)
│   ├── pdfs/                      # Downloaded IR report PDFs
│   └── extracted/                 # Qwen PDF extraction output
│
├── database/
│   └── ngx.db                     # SQLite database (gitignored)
│
├── src/
│   ├── collectors/
│   │   ├── market_collector.py    # Fetches prices + market overview
│   │   └── dividend_collector.py  # Fetches dividend history per stock
│   │
│   ├── database/
│   │   ├── schema.py              # Table definitions
│   │   └── db.py                  # Insert/query helpers
│   │
│   ├── scoring/
│   │   ├── momentum.py            # Momentum score calculator
│   │   ├── dividend.py            # Dividend score calculator
│   │   └── ranker.py              # Combines scores, saves to DB
│   │
│   ├── filters/
│   │   └── screener.py            # Applies price/volume/cap filters
│   │
│   └── reports/
│       └── txt_report.py          # Generates plain-text daily report
│
├── app/
│   └── app.py                     # Streamlit dashboard (Phase 3)
│
├── reports/
│   ├── daily/                     # Daily .txt reports by date
│   └── weekly/                    # Weekly .txt reports
│
└── logs/
    └── run.log                    # Pipeline audit trail
```

---

## Setup

**Requirements:**
- Python 3.10+
- NGX Pulse API key (free at [ngxpulse.ng/api](https://ngxpulse.ng/api))
- Qwen API key from DashScope (for Phase 2 PDF extraction)

**Install dependencies:**
```bash
pip install requests
```

**Configure:**
```python
# config.py
NGX_API_KEY = "your_ngx_pulse_key"
QWEN_API_KEY = "your_qwen_key"
```

**Initialize database:**
```bash
python main.py --mode setup
```

---

## Usage

### Daily run (manual — run each trading day)
```bash
python main.py --mode daily
```
Fetches prices → scores → generates report. Takes ~10 seconds.

### Weekly run (automated via Windows Task Scheduler)
```bash
python main.py --mode weekly
```
Refreshes dividend history + full daily pipeline.

### Report only (no API calls)
```bash
python main.py --mode report
```
Generates report from existing database data. Useful when market is closed.

### Sample report output
```
============================================================
  NGX INTELLIGENCE REPORT — 2026-06-12
============================================================

MARKET OVERVIEW
  ASI:        244,738.74
  Change:          -0.05%
  Advancers:            36
  Decliners:            37

FULL RANKED WATCHLIST
  #   Symbol         Price   Mom   Div   Score
  1   GTCO         ₦135.95    40   100    64.0
  2   ZENITHBANK   ₦124.5     35   100    61.0
  3   DANGSUGAR    ₦78.2      60    50    56.0
  ...

HIGH CONVICTION — BOTH LISTS
  ★ DANGSUGAR    combined=56.0  ₦78.2
  ★ FIRSTHOLDCO  combined=56.0  ₦69.0
============================================================
```

---

## Automation (Windows Task Scheduler)

To run the weekly dividend refresh automatically every Sunday at 8am:

1. Create `scheduler/weekly.bat`:
```bat
cd C:\path\to\ngx-screener
python main.py --mode weekly
```

2. Open Task Scheduler → Create Basic Task
3. Trigger: Weekly, Sunday, 8:00 AM
4. Action: Start a program → point to `weekly.bat`

---

## Roadmap

### Phase 1 — Core pipeline ✅
- [x] NGX Pulse API integration
- [x] SQLite database with full schema
- [x] Price and dividend data collection
- [x] Momentum + dividend scoring engine
- [x] Screener filters
- [x] Daily text report

### Phase 2 — AI layer
- [ ] Quarterly PDF downloader from company IR pages
- [ ] Qwen-powered PDF extraction (EPS, ROE, revenue growth)
- [ ] Financials table population
- [ ] News sentiment scoring via Qwen
- [ ] Scoring engine updated with fundamentals weight

### Phase 3 — Streamlit GUI (Windows local)
- [ ] Live watchlist dashboard with charts
- [ ] Individual stock drilldown page
- [ ] Dividend calendar view
- [ ] Raw data explorer
- [ ] Score history trend charts

---

## Notes

- Scores improve significantly after 30 days of daily price data (volume averages need history)
- Dividend scores reflect confirmed NGX Pulse data only
- WAPCO flagged in reports: trading 42% above Cordros analyst target of ₦240.54
- Not financial advice. Always verify before trading.

---

## Stack

| Layer | Technology |
|---|---|
| Language | Python 3.13 |
| Database | SQLite (single file, no server) |
| Market data | NGX Pulse API (free tier) |
| AI extraction | Qwen (DashScope, Phase 2) |
| Dashboard | Streamlit (Phase 3) |
| Hosting | Local (Windows / Linux Mint) |