# NGX Screener Roadmap

Long-term build plan for NGX Screener — a Nigerian Exchange quantitative research platform. Each version tests the assumptions of the previous one before adding new complexity. This is a plan, not a promise: versions ship when their exit criteria are met.

## Roadmap Summary

| Version | Name | Status |
|---|---|---|
| v0.x | Core Pipeline | Done |
| v1.0 | Factor Engine | Next |
| v1.2 | Catalyst Radar | Planned |
| v1.5 | Historical Data | Planned |
| v2.0 | Factor Validation Lab | Planned |
| v2.5 | Hypothesis Registry | Planned |
| v3.0 | Backtesting Engine | Planned |
| v4.0 | Portfolio Lab | Planned |
| v5.0 | AI Research Analyst | Planned |
| v6.0 | Kronos | Planned |

## Versioned Roadmap

### v0.x — Core Pipeline

Working daily stock screener and Streamlit dashboard. Live NGX data via NGX Pulse API (146 stocks), SQLite database with 7 tables, three-dimensional scoring (momentum, dividend, fundamentals) combined as M50+D30+F20 with PDF data or M60+D40 without, screener filters (₦50–700 price, 500k+ volume, ₦50B+ cap, <10% swing), Qwen AI PDF extraction for fundamentals, six-tab Streamlit dashboard, daily text report with warnings and high-conviction picks.

#### Exit criteria

- Daily run completes end-to-end for all 146 stocks
- Dashboard renders all six tabs without errors
- Daily text report generates with warnings and picks

### v1.0 — Factor Engine

Registry-based scoring with per-stock attribution. Replaces hardcoded score logic with a named factor registry so every number on screen traces back to the factor and inputs that produced it.

#### Exit criteria

- All current scores produced through the registry
- Per-stock attribution viewable in the dashboard
- Adding a new factor requires no changes to scoring plumbing

### v1.2 — Catalyst Radar

A catalyst and earnings momentum module that tracks upcoming NGX earnings releases, scores the pre-earnings setup for each stock, and monitors post-earnings price/volume reactions. The goal is not to give buy signals — it is to surface which stocks have an upcoming catalyst AND a setup worth watching, and let the user decide.

#### What gets built

**1. Earnings calendar**

- Pull from NGX official release calendar (ngxgroup.com/exchange/raise-capital/release-calendar/)
- Store per stock: next earnings date (confirmed vs provisional), last result period, days to earnings
- New table in SQLite: `catalysts` (symbol, catalyst_type, expected_date, confirmed INTEGER, source, created_at)

**2. Pre-earnings setup scoring — NOT a single buy score**

Seven separate signal flags per stock, each independently green/amber/red:

- Revenue trend (YoY direction from PDF fundamentals)
- PBT / PAT trend (profit direction)
- EPS trend (growing, flat, declining)
- Margin trend (improving, stable, deteriorating)
- Valuation (P/E vs sector median — where available)
- Recent price run (has the stock already moved a lot into the catalyst?)
- Volume confirmation (is volume expanding with price?)

Display as a flag table, not a composite score. The user reads the pattern and decides — a stock with all green flags but a recent sharp price run is very different from one that hasn't moved yet.

**3. Post-earnings reaction tracker**

After a result is released:

- Calculate price reaction: open vs prior close, intraday range, close change
- Calculate volume vs 20D average
- Tag the result: Strong beat + confirmation / Beat + muted reaction / Miss + selloff / Miss + held
- Store reaction history per stock so patterns build over time

**4. Momentum deterioration detector**

For stocks in the watchlist currently showing momentum:

- Track daily: price change direction + volume vs average
- Flag when volume starts declining while price still moves (distribution signal)
- Flag when price momentum slows across consecutive sessions
- Display as a warning in the Watchlist tab and Drilldown tab
- NOT an automatic sell signal — a flag for the user to investigate

**5. Catalyst Radar tab (new Streamlit tab)**

Table showing all stocks with upcoming catalysts in the next 90 days. Columns: Stock | Catalyst | Date (confirmed/provisional) | Fundamental setup (flag count) | Price setup | Days to catalyst.

Clicking a stock opens the full catalyst drilldown:

- Earnings history (last 4 quarters: revenue, PAT, EPS, price reaction)
- Current setup flags (the 7 signals above)
- Momentum deterioration status
- Valuation context

#### Data sources

- NGX official release calendar (scrape or manual CSV initially)
- Existing fundamentals table (PDF-extracted data already in DB)
- Existing prices table (daily OHLCV from NGX Pulse)
- Proshare events calendar as secondary source (provisional dates)

#### Why this fits here (between v1.0 and v1.5)

It does not require historical data (v1.5) or the full factor registry (v1.0 refactor). It works on current data already in the DB plus a new calendar source. The earnings history and reaction tracking it generates also becomes useful input for the factor validation work in v2.0.

#### Exit criteria

- Catalyst table populated for at least 10 NGX stocks with upcoming Q3 results
- Pre-earnings flag view renders in Streamlit for every eligible stock
- Post-earnings reaction stored for at least one completed result
- Momentum deterioration flag appears in Watchlist when conditions are met
- Catalyst Radar tab renders without errors

### v1.5 — Historical Data

NGX OHLCV back to 2016, macro data, corporate actions. Builds the history that validation and backtesting need.

#### Exit criteria

- Daily OHLCV coverage back to 2016 for all currently listed symbols
- Macro series and corporate actions stored alongside prices
- Gaps and survivorship limitations documented

### v2.0 — Factor Validation Lab

IC, quintile returns, hit rate per NGX factor. Tests whether the v0.x/v1.0 scores actually predicted anything, using alphalens.

#### Exit criteria

- IC and quintile-return analysis runs per factor on NGX history
- Results recorded per factor with hit rates
- At least one factor assumption revised or dropped based on evidence

### v2.5 — Hypothesis Registry

Persistent research workflow with run cards. Every research question gets a written hypothesis, a test, and a recorded outcome.

#### Exit criteria

- Run-card workflow operational for new research questions
- Past runs queryable with hypotheses and outcomes attached

### v3.0 — Backtesting Engine

Walk-forward strategy testing with quantstats tearsheets. Turns validated factors into testable rule sets.

#### Exit criteria

- Walk-forward backtest runs on any defined rule set
- quantstats tearsheet generates per backtest
- No lookahead in the pipeline (verified by construction)

### v4.0 — Portfolio Lab

skfolio allocation, risk analytics, optimization. Moves from ranked lists to sized positions with constraints.

#### Exit criteria

- Optimizer produces allocations under stated constraints
- Risk analytics viewable per portfolio
- Rebalancing logic defined and tested

### v5.0 — AI Research Analyst

Qwen interpretation layer over the deterministic engine. The numbers stay computed; the AI explains them.

#### Exit criteria

- Natural-language interpretation renders for watchlist and drilldown views
- Every AI claim links back to the underlying computed value
- No AI-generated numbers presented as computed data

### v6.0 — Kronos

ML forecasting signal, promoted only if it beats factor baselines. Machine learning earns its place by outperforming the simpler stuff — otherwise it stays out.

#### Exit criteria

- ML signal evaluated against factor baselines on the same history
- Promotion only on demonstrated outperformance
- Failure documented either way
