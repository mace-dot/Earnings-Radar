# Earnings Radar

Local earnings research dashboard built with **Python**, **Streamlit**, and **SQLite**.

CSV-first MVP for tracking upcoming earnings, reviewing option-chain snapshots, attaching research notes, exporting LLM research packets, and journaling paper trades.

## Principles

- **No fabricated live data** — prices, estimates, and earnings dates come only from your imports (or clearly labeled sample CSVs).
- **Mechanical math, not forecasts** — spread %, call+put ask cost, contract cost, and expiration breakevens are quote arithmetic. They are **not** a calibrated forecast of the earnings move.
- **Research quality ≠ options liquidity** — confirmation/source/notes flags stay separate from stale quotes, wide spreads, missing fields, and thin volume/OI.
- **No brokerage execution** — paper journal only.
- **API keys stay out of git** — copy `.env.example` → `.env` when you add live providers later.

## Setup

```bash
cd earnings-radar
python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env               # optional; for future API keys only
```

## Run

```bash
source .venv/bin/activate
streamlit run app.py
```

Open the local URL Streamlit prints (usually `http://localhost:8501`).

### Suggested first run

1. Go to **Import**
2. Download templates and/or sample CSVs
3. Click **Load sample data into local DB** (rows are labeled `SAMPLE DATA`), then select **Demo** mode
4. Open **Earnings** or **Radar** to see upcoming events, costs, and flags
5. Add notes under **Research notes**, export under **Export packet**, journal under **Paper journal**

## CSV formats

### Earnings calendar

| Column | Required | Notes |
|--------|----------|-------|
| `ticker` | yes | |
| `earnings_date` | yes | `YYYY-MM-DD` |
| `earnings_time` | yes | `BMO`, `AMC`, `During Market`, `Unknown` |
| `confirmation_status` | yes | `Confirmed`, `Estimated`, `Unconfirmed` |
| `source` | yes | URL or short citation |

Templates: `data/templates/earnings_calendar_template.csv`  
Samples: `data/samples/sample_earnings_calendar.csv`

### Option chains

| Column | Required | Notes |
|--------|----------|-------|
| `ticker` | yes | |
| `strike` | yes | |
| `expiration` | yes | `YYYY-MM-DD` |
| `stock_price` | no* | Missing → liquidity flag |
| `call_bid` / `call_ask` | no* | |
| `put_bid` / `put_ask` | no* | |
| `quote_timestamp` | no* | ISO-8601 preferred |
| `call_volume` / `put_volume` | no | |
| `call_open_interest` / `put_open_interest` | no | |
| `source` | no | How the snapshot was obtained |

\*Required for clean liquidity; incomplete rows are kept and flagged.

Templates: `data/templates/option_chains_template.csv`  
Samples: `data/samples/sample_option_chains.csv`

## Calculations (verified)

```text
spread_%          = (ask - bid) / mid * 100
                    where mid = (ask + bid) / 2

straddle_ask_cost = call_ask + put_ask          # per share
contract_cost     = straddle_ask_cost * 100
breakeven_low     = strike - straddle_ask_cost
breakeven_high    = strike + straddle_ask_cost

paper_pnl         = (exit_credit - entry_debit) * 100 * contracts - fees
```

Run the unit tests:

```bash
source .venv/bin/activate
pytest -q
```

Example from sample ATM `SAMPLE_AAA` @ 100:

- Call ask 5.00 + put ask 4.80 → **9.80** per share → **$980** per contract
- Expiration breakevens **90.20 / 109.80**
- Call spread % ≈ **4.08%** of mid

## Project layout

```text
app.py                      Streamlit UI
earnings_radar/
  config.py                 Paths + thresholds (.env aware)
  db.py                     SQLite schema + helpers
  imports.py                CSV validation / import
  calculations.py           Spread, cost, breakevens, P&L
  flags.py                  Research vs liquidity flags
  export.py                 Markdown research packet
data/templates/             Downloadable blank CSVs
data/samples/               Labeled SAMPLE DATA
tests/                      Calculation + import checks
.env.example                Placeholder for future API keys
```

SQLite DB default path: `data/earnings_radar.db` (gitignored).

## Flags

**Research quality:** `unconfirmed_earnings`, `estimated_earnings`, `missing_earnings_source`, `no_research_notes`

**Options liquidity:** `stale_quote`, `missing_fields`, `wide_call_spread` / `wide_put_spread`, `expiration_before_earnings`, `low_volume`, `low_open_interest`, `no_option_quote`

Defaults (override via `.env`): stale > 24h, wide spread ≥ 15% of mid.

## Live data later

Do not commit keys. When you add a provider:

1. Put secrets in `.env` only
2. Add a thin fetcher module that writes into the same SQLite tables
3. Keep the dashboard reading from SQLite so CSV and live paths stay interchangeable

## License

Personal / local research tool. Not investment advice.

## Automatic research and weekly board

The feature implementation adds a separate research database, SEC filings and XBRL
financial facts, official Federal Reserve RSS, a durable background worker and a
weekly picks-style research inbox. The board shows actions, evidence strength,
freshness and missing information. It does not invent betting odds or profitable picks.

```bash
source .venv/bin/activate
python -m earnings_radar.database migrate --db data/research.db
python -m earnings_radar.worker  # independent terminal/process
streamlit run app.py --server.headless=true --server.address=127.0.0.1 --browser.gatherUsageStats=false
```

Set a real `SEC_USER_AGENT` contact in ignored `.env` before SEC collection. Start
Streamlit separately; collection continues when the browser closes. Public sources
poll every five minutes (XBRL facts hourly), so measured arrival delays are shown rather
than an instantaneous-data promise. Samples now load only into `data/demo.db`; select
Demo mode to view them. Existing CSV workflows, notes, exports and paper trades remain.

Bloomberg, WSJ, EarningsHub, Seeking Alpha, Yahoo Finance and Google Finance have
explicit source-registry entries. They are **not live connections**: authorized APIs,
credentials and retention rights must be verified. Alpaca news/IEX and the optional
model/Telegram adapters are implemented but not live-verified without credentials.
No real-time options feed is configured, so trade evaluations currently reject missing
or stale data. Only supported standard long-option packages are eligible; scenarios
are simulated expiration payoffs, not forecasts.

See [implementation status](docs/IMPLEMENTATION_STATUS.md),
[providers and access](docs/PROVIDERS.md), and [runbook](docs/RUNBOOK.md) for recovery,
backups, deployment templates, model budget and notification configuration.


## Hosted URL through Render

A GitHub-connected Render Blueprint is prepared in `render.yaml`. It uses Python 3.12,
runs the dashboard and collector together, retains SQLite on a persistent disk, and
requires a generated dashboard password. In Render choose **New → Blueprint**, select
this repository and branch **feature/autonomous-earnings-research**, enter the requested
SEC User-Agent, and review the Starter service/disk costs before creation. Main remains
the older app. Deployment has not been performed from this session.

See [hosting setup](docs/HOSTING.md) for account connection, access and validation.
Vercel is not a direct host for this Streamlit/continuous-worker architecture; Supabase
is an optional future database/auth component rather than an app host.
