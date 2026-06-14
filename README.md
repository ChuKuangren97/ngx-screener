# NGX Screener

A personal Nigerian stock market intelligence system that automatically collects, scores, and ranks NGX-listed stocks for short-term momentum plays and long-term dividend investing.

Built with Python, SQLite, NGX Pulse API, and Qwen AI for PDF financial extraction. Designed for retail investors who want data-driven watchlists without paying for Bloomberg or doing manual spreadsheet work.

---

## What It Does

**Daily** — run one command. The system:
1. Fetches live prices and market data for all 146 NGX-listed stocks via API
2. Filters out stocks outside your criteria (price range, liquidity, volatility)
3. Scores every eligible stock across three dimensions: momentum, dividend, fundamentals
4. Ranks them and generates a plain-text intelligence report

**Weekly** — automatically refreshes dividend history for all watchlist stocks.

**On demand** — run the PDF extractor when new quarterly reports are published. Qwen reads the PDFs and updates fundamental scores automatically.

---

## Scoring System

### Three-Dimensional Scoring

| Dimension | Weight (with PDF data) | Weight (without PDF data) |
|---|---|---|
| Momentum | 50% | 60% |
| Dividend | 30% | 40% |
| Fundamentals | 20% | — |

When PDF data is available for a stock, the system uses `M50+D30+F20`. Otherwise falls back to `M60+D40` so stocks without PDFs still get ranked fairly.

---

### Momentum Score (0–100)
Targets 1-month price setups.

| Component | Max Points | Logic |
|---|---|---|
| 7-day return | 40 | >=10% = 40, 5-10% = 25, 0-5% = 10, negative = 0 |
| Volume vs 30-day avg | 30 | >2x = 30, 1.5x = 20, 1x = 10, <1x = 0 |
| Price stability | 20 | Inverse of daily swing — stable = higher score |
| Sector trend | 10 | Net advancers in sector this week |

> Volume scores improve significantly after 30 days of daily data collection.

---

### Dividend Score (0–100)
Targets long-term income and 2-5 month holds.

| Component | Max Points | Logic |
|---|---|---|
| Trailing 12-month yield | 40 | >=8% = 40, 5-8% = 28, 3-5% = 15, <3% = 5 |
| Payout consistency | 30 | 5+ years paying = 30, 3-4 = 20, 1-2 = 10 |
| DPS growth trend | 20 | Growing YoY = 20, flat = 10, declining = 0 |
| Payout timing | 10 | Ex-date within 6 months = 10, 6-12 = 5, >12 = 0 |

---

### Fundamentals Score (0–100)
Extracted from company annual/quarterly PDFs via Qwen AI.

| Component | Max Points | Logic |
|---|---|---|
| EPS / Profit growth | 30 | Growing >5% = 30, flat = 15, declining = 0 |
| Return on Equity | 25 | >=25% = 25, 15-25% = 18, 10-15% = 10 |
| Revenue growth | 25 | >=20% = 25, 10-20% = 18, 0-10% = 10, negative = 0 |
| Profit after tax growth | 20 | >=20% = 20, 0-20% = 12, -20-0% = 5, <-20% = 0 |

> Stocks without PDF data score 45/100 (neutral) on fundamentals — benefit of the doubt until data is available.

---

## Screener Filters

Stocks must pass all filters before scoring:

| Filter | Value | Reason |
|---|---|---|
| Price range | N50 - N700 | Affordable for retail capital |
| Minimum daily volume | 500,000 shares | Ensures liquidity to enter/exit |
| Minimum market cap | N50 billion | Excludes micro-caps and shells |
| Maximum daily swing | 10% | Excludes erratic/manipulated stocks |
| Null volume | Excluded | Stocks with no trading activity |

Out of 146 NGX-listed stocks, roughly 15-20 pass filters at any given time.

---

## Data Sources

| Source | What it provides | Method | Cost |
|---|---|---|---|
| NGX Pulse API | Live prices, volume, market overview, dividend history | REST API | Free (100 req/day) |
| Company IR pages | Quarterly and annual report PDFs | Manual download | Free |
| Qwen AI (DashScope) | PDF financial extraction | API | Free tier available |

### NGX Pulse API Request Budget (100/day)
- 1 request -> `/stocks` (all 146 stocks)
- 1 request -> `/market` (ASI, breadth, value)
- 1 request -> `/news`
- Up to 97 requests -> `/dividends` per stock (run weekly, not daily)

---

## Project Structure

```
ngx-screener/
|
+-- main.py                        # Entry point -- all run modes
+-- config.py                      # API keys, filters, constants (NOT in repo)
+-- requirements.txt               # Python dependencies
|
+-- data/
|   +-- snapshots/                 # Daily JSON from /stocks endpoint
|   +-- dividends/                 # Per-stock dividend cache (JSON, 7-day TTL)
|   +-- pdfs/                      # Downloaded company IR report PDFs
|   +-- extracted/                 # Qwen PDF extraction output (JSON)
|
+-- database/
|   +-- ngx.db                     # SQLite database (NOT in repo)
|
+-- src/
|   +-- collectors/
|   |   +-- market_collector.py    # Fetches prices + market overview daily
|   |   +-- dividend_collector.py  # Fetches dividend history weekly
|   |
|   +-- ai/
|   |   +-- qwen_extractor.py      # Auto-detects PDFs -> Qwen extraction -> JSON
|   |
|   +-- database/
|   |   +-- schema.py              # SQLite table definitions
|   |   +-- db.py                  # Insert/query/helper functions
|   |
|   +-- scoring/
|   |   +-- momentum.py            # Momentum score (0-100)
|   |   +-- dividend.py            # Dividend score (0-100)
|   |   +-- fundamentals.py        # Fundamentals score (0-100) from PDF data
|   |   +-- ranker.py              # Combines all scores, saves to DB
|   |
|   +-- filters/
|   |   +-- screener.py            # Price/volume/cap/swing filters
|   |
|   +-- reports/
|       +-- txt_report.py          # Daily plain-text intelligence report
|
+-- app/
|   +-- app.py                     # Streamlit dashboard (Phase 3 -- local Windows)
|
+-- reports/
|   +-- daily/                     # Daily .txt reports by date (NOT in repo)
|   +-- weekly/                    # Weekly .txt reports (NOT in repo)
|
+-- logs/
    +-- run.log                    # Pipeline audit trail (NOT in repo)
```

---

## Setup

### Requirements
- Python 3.10+
- NGX Pulse API key -- free at https://ngxpulse.ng/api
- Qwen API key -- free tier at https://dashscope-intl.aliyuncs.com

### Install dependencies
```bash
pip install requests pdfplumber pandas streamlit
```

### Configure
Create `config.py` in the project root. This file is gitignored and never committed:

```python
# API Keys
NGX_API_KEY = "your_ngx_pulse_key_here"
QWEN_API_KEY = "your_qwen_dashscope_key_here"
QWEN_MODEL = "qwen-plus"

# Paths
DB_PATH = "database/ngx.db"
SNAPSHOT_DIR = "data/snapshots"
DIVIDEND_DIR = "data/dividends"
PDF_DIR = "data/pdfs"
EXTRACTED_DIR = "data/extracted"
REPORTS_DAILY = "reports/daily"
REPORTS_WEEKLY = "reports/weekly"
LOG_PATH = "logs/run.log"

# Screener filters
MIN_PRICE = 50
MAX_PRICE = 700
MIN_VOLUME = 500000
MIN_MARKET_CAP = 50_000_000_000
MAX_DAILY_SWING = 0.10
EXCLUDE_NULL_VOLUME = True

# Scoring weights (fallback -- used when no PDF fundamentals data)
MOMENTUM_WEIGHT = 0.6
DIVIDEND_WEIGHT = 0.4

# Starter watchlist
WATCHLIST = [
    "GTCO", "ZENITHBANK", "STANBIC", "NB", "MTNN",
    "DANGSUGAR", "FIRSTHOLDCO", "OANDO", "FCMB", "VITAFOAM"
]
```

### Initialize database
```bash
python main.py --mode setup
```

---

## Usage

### Daily run (manual -- run each trading day)
```bash
python main.py --mode daily
```
Fetches latest prices -> scores all dimensions -> generates report. ~10 seconds.

### Weekly run (automated via Windows Task Scheduler)
```bash
python main.py --mode weekly
```
Refreshes dividend history + full daily pipeline.

### Report only (no API calls)
```bash
python main.py --mode report
```
Generates report from existing database data. Use when market is closed.

### Run fundamentals extraction (when new PDFs available)
```bash
python src/scoring/fundamentals.py
```
Auto-detects all PDFs in `data/pdfs/`, extracts financials via Qwen, updates scores.

---

## PDF Workflow

The system auto-detects and matches PDFs to stock symbols -- no manual configuration needed.

**Recommended naming convention:**
```
data/pdfs/SYMBOL_PERIOD.pdf
e.g. GTCO_FY2025.pdf
     ZENITHBANK_FY2025.pdf
     DANGSUGAR_Q1_2026.pdf
```

**Auto-detection also works** -- the extractor reads the first 5 pages of each PDF and matches the company name to a known NGX symbol. So even a file named `Zenith-Annual-Report-2025.pdf` will be correctly identified as `ZENITHBANK`.

**Where to find PDFs:**

| Company | Investor Relations Page |
|---|---|
| GTCO | gtcoplc.com/investor-relations |
| Zenith Bank | zenithbank.com/investor-relations |
| Dangote Sugar | dangotesugar.com.ng/investors |
| FirstHoldCo | firstbanknigeria.com/investor-relations |
| MTN Nigeria | mtn.com.ng/investor-relations |
| Stanbic IBTC | stanbicibtcholdings.com/investor-relations |

After downloading, place PDFs in `data/pdfs/` and run:
```bash
python src/scoring/fundamentals.py
```

---

## Sample Report Output

```
==============================================================
  NGX INTELLIGENCE REPORT -- 2026-06-13
  Generated: 22:06 UTC
==============================================================

MARKET OVERVIEW
  ASI:          244,738.74
  Change:           -0.05%
  Volume:     1,721,871,986
  Advancers:            36
  Decliners:            37

FULL RANKED WATCHLIST
  #   Symbol         Price   Mom   Div  Fund   Score
  1   GTCO         N135.95  40.0 100.0  40.0   58.0  M50+D30+F20
  2   ZENITHBANK   N124.5   35.0 100.0  42.0   55.9  M50+D30+F20
  3   DANGSUGAR    N78.2    60.0  50.0  35.0   52.0  M50+D30+F20
     Warning: Still loss-making (PAT -N64B) despite revenue recovery.
  4   FIRSTHOLDCO  N69.0    60.0  50.0  10.0   47.0  M50+D30+F20
     Warning: Profit down 79% YoY per FY2025 report.

FUNDAMENTALS SNAPSHOT (PDF-extracted)
  Symbol            EPS    ROE%   RevGr%   PATGr%
  GTCO           N25.43   25.7%     0.1%   -14.9%
  ZENITHBANK      N7.64    6.1%     6.0%     1.0%
  DANGSUGAR           --      --    24.6%   -61.7%
  FIRSTHOLDCO         --    4.2%     6.9%   -79.0%

HIGH CONVICTION -- BOTH LISTS
  * DANGSUGAR    combined=52.0  N78.2
  * FIRSTHOLDCO  combined=47.0  N69.0
==============================================================
```

---

## Automation (Windows Task Scheduler)

Set up weekly dividend refresh to run automatically every Sunday:

1. Create `scheduler/weekly.bat`:
```bat
@echo off
cd C:\path\to\ngx-screener
C:\Users\USER\AppData\Local\Programs\Python\Python313\python.exe main.py --mode weekly
```

2. Open Task Scheduler -> Create Basic Task
3. Trigger: Weekly -> Sunday -> 8:00 AM
4. Action: Start a program -> point to `weekly.bat`

---

## Database Schema

SQLite database at `database/ngx.db` with 7 tables:

| Table | Contents |
|---|---|
| `stocks` | Symbol, name, sector, market, shares outstanding |
| `prices` | Daily price/volume per stock -- one row per stock per day |
| `dividends` | Full dividend history -- ex-date, pay-date, amount per share |
| `financials` | PDF-extracted fundamentals -- EPS, ROE, revenue/profit growth |
| `scores` | Daily combined scores per stock |
| `market_summary` | Daily ASI, breadth, value traded |
| `run_log` | Pipeline audit trail -- every run logged with status |

---

## Roadmap

### Phase 1 -- Core pipeline (complete)
- [x] NGX Pulse API integration (146 stocks)
- [x] SQLite database with full schema
- [x] Daily price and market data collection
- [x] Weekly dividend history collection with 7-day cache
- [x] Momentum scoring engine
- [x] Dividend scoring engine
- [x] Screener filters
- [x] Daily plain-text intelligence report with manual override warnings

### Phase 2 -- AI fundamentals layer (complete)
- [x] Auto PDF detection and company name matching
- [x] Qwen AI financial extraction (EPS, ROE, revenue/profit growth)
- [x] Fundamentals scoring engine
- [x] Three-dimensional combined scoring (M50+D30+F20)
- [x] Fundamentals snapshot section in daily report
- [x] Dynamic weight switching with/without PDF data

### Phase 3 -- Streamlit GUI (planned)
- [ ] Live watchlist dashboard with score breakdowns
- [ ] Individual stock drilldown with price chart
- [ ] Dividend calendar view
- [ ] Fundamentals comparison table
- [ ] Score history trend charts
- [ ] Raw data explorer

---

## Important Notes

- **config.py is gitignored** -- create your own from the template above. Never commit API keys.
- **database/ngx.db is gitignored** -- each user builds their own local database.
- **data/ and reports/ contents are gitignored** -- PDFs, JSON, and reports stay local.
- Scores improve significantly after 30 days of daily price collection (volume averages)
- WAPCO (Lafarge): flagged in reports -- trading 42% above Cordros analyst target of N240.54
- Not financial advice. Always verify before trading.

---

## Stack

| Layer | Technology |
|---|---|
| Language | Python 3.13 |
| Database | SQLite (single file, no server needed) |
| Market data | NGX Pulse API (free tier, 100 req/day) |
| PDF extraction | pdfplumber + Qwen AI (DashScope) |
| Dashboard | Streamlit (Phase 3, local Windows) |
| Hosting | Local machine (Windows / Linux Mint) |