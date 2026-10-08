# Earnings Radar — Master Build Plan (Codex handoff)

> **Current specification:** `docs/PREDICTIVE_BALANCE_PLAN.md` is the plan for the operational pipeline and for predictive large-move research. It overrides this file where they conflict. This document remains the earlier product handoff.

> **How to use this file:** save it as `docs/MASTER_PLAN.md` and save `AGENTS.md` in the repo root. Then paste the **single build-everything prompt in §12** into Codex once. Codex works through all phases in order, tracks progress in `docs/PROGRESS.md`, and commits after each phase. If it runs out of time or context, paste the short **Resume prompt** (also in §12) and it picks up where it stopped.

---

## 0. Diagnosis: why the current site doesn't match the vision

Reviewed: `github.com/mace-dot/earnings-radar` (`main` = Vercel web app, `feature/autonomous-earnings-research` = Streamlit/Render app).

| Problem in current code | Where | Effect |
|---|---|---|
| Trade decisions are hard-coded to `WAIT` | `web/api/_strategy.py` (`'contract_decision':'WAIT'`), `_options_research.py` (`'decision':'WAIT'`) | The app can never suggest a trade |
| Options and live quotes are off behind env flags | `RADAR_OPTIONS_DISPLAY_AUTHORIZED`, `RADAR_MARKET_DISPLAY_AUTHORIZED` default `false` | No IV, no expected move, no contracts |
| **No earnings calendar provider at all** | `_strategy.py` → `'catalyst':'Next company update; upcoming date not confirmed.'` | An "earnings radar" that doesn't know when earnings are |
| Forecasts disabled by design | `_live.py` → `'forecasts': {'enabled': False}` | No scoring or ranking of trades |
| Coverage is about 3 companies per daily run | `_collector.py` ("up to three companies per run, rotated") | Nowhere near "every US stock" |
| Policy file is a draft | `research_policy.json` → `"status": "PROPOSED_NOT_ACTIVE"` | Codex treats every gate as blocking |
| Code is minified one-liners | all of `web/api/*.py`, `web/public/app.js` | Hard for you or Codex to change safely |
| Two diverging branches | the feature branch deletes `web/` | Codex may be editing the wrong app |
| UI says Up/Down and "research idea, not a trade" | `index.html`, `app.js` | Opposite of the product you described |

**What's worth keeping:** the SEC directory ingest (`company_tickers_exchange.json`, which already gives you the full US ticker universe with CIKs), SEC XBRL fundamentals with year-over-year math, SIC codes (used for industries), the Alpaca bars and options adapters, the Supabase auth/cookie flow, and the security headers.

**Root cause:** Codex was steered toward "research only, never recommend," and every later prompt piled more gates on top. The fix is a precise spec that defines what a recommendation is, how it gets scored, and how its uncertainty is shown, so Codex has something concrete to build instead of a reason to block.

---

## 1. Product vision (spec for Codex)

**One sentence:** pick a stock like a player, see all of its earnings "lines," tap **BULL** or **BEAR** to see that case and the auto-picked trade, and let the Radar's model portfolio trade the best ones automatically.

### 1.1 Core objects
- **Player** = a US-listed stock (about 5,000–6,000 common stocks from NYSE, Nasdaq, NYSE American, Cboe).
- **Line** = a time-boxed setup around one earnings event. Each liquid stock with a report in the next 60 days gets up to five lines:

| Line | Window | Question it answers | Main inputs |
|---|---|---|---|
| **Run-Up** | today → day before report | Does the stock tend to drift up or down into earnings? | Ticker's own T-20→T-1 history, estimate revisions, momentum vs sector |
| **Earnings Move** | report day ± 1 session | Will the reaction beat or miss the implied move, and in which direction? | Options-implied move, historical move, beat rate, revisions |
| **Post-Earnings Drift** | report +1 → +20 sessions | After a surprise, does the price keep going? | Surprise size, gap direction, post-earnings drift history |
| **Volatility** | today → report | Are options cheap or expensive going into the event? | IV rank, implied ÷ historical move ratio, IV run-up history |
| **Swing (3-month)** | 60 trading days | Medium-term thesis | Fundamentals trend, revisions, relative strength |

- **Side** = BULL or BEAR on a line. (Volatility lines use **BULL = vol up / options cheap** and **BEAR = vol down / options expensive**, with a subtitle saying so.)
- **Radar Pick** = the side the model favors on a line, with a confidence tier.
- **Lineup** = your slip of selected sides (like a PrizePicks entry), which you can paper-trade with one tap.

### 1.2 What "automated" means (phased)
1. **Auto-picks (Phase 3):** every night and every 30 minutes during market hours, the engine re-scores every line and ranks the best ones by expected value per dollar risked, after liquidity filters.
2. **Auto model portfolio (Phase 5):** a public paper portfolio that enters and exits the top picks under fixed rules, with a live P&L and a full trade log. This is your proof that the strategy works.
3. **User auto-pilot (Phase 7, after legal review):** users connect their own broker and choose rules ("copy Strong picks, max $200 per trade, max 5 open"). Every order shows a one-tap confirmation by default; full automation is opt-in.

---

## 2. Strategy engine (the "fortune teller," built as honest probabilities)

No model predicts the future. What can be done is estimating **how often setups like this one worked in the past**, checking that the estimate holds up on data the model never saw, and reporting it honestly. That is what makes it feel like a fortune teller without misleading anyone.

### 2.1 Signals (features), all point-in-time

| Family | Feature | Notes |
|---|---|---|
| Timing | `days_to_report`, `date_confirmed` (bool), `report_time` (BMO/AMC) | Estimated dates lower confidence on Run-Up and Volatility lines |
| Expectations | EPS and revenue consensus revisions over 7/30/90 days (% change, up-vs-down revision count) | Your "investors expect good news" signal. Rising revisions plus a quiet price = classic run-up setup |
| Track record | beat rate over the last 8–12 quarters, average surprise %, guidance raise/cut history | |
| Price | 5/20/60-day return, return vs sector ETF, distance from 50/200-day average, 52-week high proximity | |
| Ticker history | mean and median return T-20→T-1 and T+1→T+20 over the last 12 reports, hit rate | Minimum 8 reports or the feature is null |
| Volatility | ATM IV (front expiry after report), IV rank and percentile (252 days), **implied move** = ATM straddle mid ÷ spot, **implied ÷ historical move ratio**, IV term-structure kink | Implied move needs options data; store snapshots daily from day one |
| Positioning | short interest % float, days to cover (optional provider) | Squeeze risk on BEAR sides |
| Fundamentals | revenue, operating income, and cash flow YoY from SEC XBRL (port existing code), margin trend | |
| News | headline count and sentiment over the last 7 days (simple model first; optional LLM later) | Always link the source articles |
| Peers | average reaction of same-industry stocks that already reported this season | Read-through effect |
| Market regime | VIX level, SPY trend | One regime flag shared by all lines |

### 2.2 Models
- **v1 (Phase 3): transparent rules plus a regularized logistic regression per line type.** Target is `P(BULL side wins)`; "win" is defined per line in §2.4. Train on 2019→present with walk-forward folds (train through year N, test on year N+1).
- **Calibration:** isotonic or Platt scaling on out-of-sample predictions. Save the Brier score, log loss, and a 10-bucket reliability table to `model_registry`.
- **v2 (Phase 6):** gradient-boosted trees (LightGBM). Promote only if it beats v1 out-of-sample on Brier score **and** on paper P&L after costs.
- **Baselines for every report:** "always BULL," "follow 20-day momentum," and "coin flip." If the model doesn't beat them, the UI says so.

### 2.3 Turning probabilities into a pick
```
edge        = P(side wins) − breakeven_probability(trade structure, after costs)
EV_per_$    = edge × payoff_ratio adjusted for spread and commissions
score       = EV_per_$ × liquidity_multiplier × data_quality_multiplier
tier        = Strong  if score ≥ T1 and sample_n ≥ 200 and calibration OK
              Moderate if score ≥ T2
              Lean     if score > 0
              No pick  otherwise (the line still shows both cases)
```
Thresholds T1/T2 are set from the backtest so that "Strong" historically had the best risk-adjusted return. Store them in `model_registry`, not in code.

### 2.4 Trade-structure selector (rules table Codex should implement)

| Line × side | Condition | Beginner (shares) | Options mode (defined risk) | Exit rule |
|---|---|---|---|---|
| Run-Up BULL | revisions ↑, IV rank < 50 | Buy shares, stop −1.5× ATR | Call debit spread, expiry **before** report, or long call sold the day before report | **Exit before the report** (time stop) |
| Run-Up BEAR | revisions ↓, weak relative strength | Skip for beginners (no shorting) | Put debit spread, exit before report | Exit before the report |
| Earnings Move BULL/BEAR | strong directional probability | Shares sized at 0.5× normal (gap risk) | Debit spread, first expiry after report | Close by T+2 |
| Volatility BULL | implied ÷ historical < 0.8, IV rank < 30 | n/a (show "options only") | Long straddle or strangle, 2–4 weeks before report, **sell before report** to capture the IV run-up | Exit day before report |
| Volatility BEAR | implied ÷ historical > 1.3 | n/a | **Advanced only:** iron condor / iron fly, defined risk | Close T+1 |
| Drift BULL/BEAR | surprise > 1 SD and gap in same direction | Shares with trailing stop | Debit spread 30–45 days | 20 sessions or stop |
| Swing | fundamentals + revisions agree | Shares | 60–90 day debit spread | Target / stop / 60 days |

**Strike selection:** long leg delta about 0.40–0.55, short leg at roughly the 1× implied-move price, spread width chosen so max loss ≤ position budget.

**Position sizing:** risk per trade = `min(user_risk_pct, 2%) × account_value`. Default `user_risk_pct` = 1%. Earnings Move lines are half size.

**Lineup warnings:** more than 40% of risk in one sector, more than 3 picks reporting the same day, or a total that exceeds the max-risk setting.

### 2.5 Liquidity tiers (decides what gets auto-suggested)

| Tier | Stock filter | Options filter | Gets |
|---|---|---|---|
| A | price ≥ $10, 20-day average dollar volume ≥ $50M | front-month ATM OI ≥ 1,000, bid-ask ≤ 5% of mid | All lines, options trades, model portfolio |
| B | price ≥ $5, ADV ≥ $10M | OI ≥ 250, spread ≤ 10% | All lines, shares and simple spreads |
| C | ADV ≥ $1M | none / thin | Lines shown, shares-only suggestions, "thin options" badge |
| D | everything else | | Searchable research page only, no picks |

Every US stock is searchable. Only A–C appear on the board.

---

## 3. Data providers (pluggable)

> **Verify current pricing, rate limits, and display/redistribution terms before choosing.** Public display of exchange data usually needs redistribution rights, and the old code's "authorization" flags were reacting to that real issue. Pick plans that allow display on a public website.

| Need | Option(s) | Notes |
|---|---|---|
| Ticker universe + CIK + SIC industry | SEC `company_tickers_exchange.json` + `submissions/CIK##########.json` | Free. Already in code. SIC → sector map in §4 |
| Earnings calendar 1–3 months out | Finnhub earnings calendar, Financial Modeling Prep, Alpha Vantage `EARNINGS_CALENDAR` (3- and 12-month horizons), Nasdaq calendar | Use two sources and flag disagreement. Mark `confirmed` when the company announces the date (8-K or IR press release) |
| Daily bars, whole market | Polygon/Massive grouped daily (all tickers in 1 call), Alpaca multi-symbol bars (keys already configured) | Nightly |
| Options chains, IV, greeks | Alpaca options snapshots, Tradier, Polygon/Massive Options, ORATS (best historical IV for backtests) | Start saving your own daily ATM-IV and implied-move snapshots now; history builds up |
| Consensus estimates + revisions | FMP, Finnhub, Zacks (paid), Estimize | The most valuable paid feed for the Run-Up line |
| News | Alpaca News API, Finnhub company news, existing Yahoo/CNBC RSS code | Store headline, URL, publisher, timestamp |
| Fundamentals | SEC XBRL `companyfacts` | Port existing code |
| Short interest (optional) | FINRA short interest files (twice monthly), vendor feeds | |
| Charts | TradingView Lightweight Charts (open-source library, self-rendered from your data) or the TradingView widget (CSP already allows it) | |

**Budget path:** start with free tiers plus Alpaca, which covers the universe, bars, news, and indicative options. Add one paid estimates feed and one paid options-history feed once the board works.

---

## 4. Industries / sectors
- Map SEC SIC codes to 11 GICS-style sectors and about 60 industries with a static table, `engine/reference/sic_to_sector.csv`, that Codex generates and you review.
- Also map each sector to its SPDR ETF (XLK, XLV, XLF, XLE, XLY, XLP, XLI, XLB, XLU, XLRE, XLC) for relative-strength features.
- Allow manual overrides in `security_overrides` for misclassified mega-caps (for example, holding companies).
- UI: sector chips across the top of the board, and an industry drop-down inside each sector.

---

## 5. Architecture

```
            ┌──────────── GitHub Actions (cron) / Render worker ────────────┐
            │ engine/ (Python)                                              │
 Providers ─┤ ingest → features → models → lines/picks → grading → backtest │
            └───────────────────────────┬───────────────────────────────────┘
                                        │ writes
                                 Supabase Postgres (+ Auth, RLS)
                                        │ reads (fast, cached)
                 Next.js on Vercel (apps/web): board, stock pages, lineup, track record
```

### 5.1 Job schedule (US/Eastern)

| Job | When | Scope |
|---|---|---|
| `universe_refresh` | daily 06:00 | all tickers, SIC, active flags |
| `calendar_refresh` | daily 06:15 + 18:00 | next 90 days of earnings |
| `eod_bars` | daily 17:30 | all active tickers |
| `fundamentals_refresh` | daily 19:00 | tickers with new 10-Q/10-K/8-K (SEC daily index, code exists) |
| `features_and_score` | daily 20:00 | all Tier A–C with report ≤ 60 days or ≤ 20 days after |
| `options_snapshot` | every 30 min, 09:45–15:45 | Tier A–B with report ≤ 45 days |
| `intraday_rescore` | after each options snapshot | same set |
| `grade_picks` | daily 17:45 | expired windows |
| `model_portfolio` | 09:40 and 15:30 | paper orders |
| `backtest` | weekly, Sunday | full walk-forward; writes `model_registry` |

### 5.2 Database schema (core tables)
```
securities(symbol PK, cik, name, exchange, sic, sector, industry, is_active, liquidity_tier, updated_at)
earnings_events(id PK, symbol, report_date, report_time, fiscal_period, confirmed bool,
                sources jsonb, eps_estimate, rev_estimate, eps_actual, rev_actual, surprise_pct, updated_at)
daily_bars(symbol, date, o,h,l,c,v, vwap, source)  PK(symbol,date)
option_snapshots(symbol, ts, expiry, atm_strike, atm_iv, straddle_mid, implied_move_pct,
                 iv_rank, oi_atm, spread_pct, source)
estimate_revisions(symbol, as_of, period, metric, consensus, up_count, down_count)
news_items(id, symbol, published_at, title, url, publisher, sentiment)
features(symbol, event_id, as_of, line_type, values jsonb, data_quality jsonb)
lines(id PK, symbol, event_id, line_type, window_start, window_end, status, as_of)
line_sides(line_id, side, prob, tier, score, case_bullets jsonb, invalidation jsonb,
           trade_beginner jsonb, trade_options jsonb, evidence jsonb, model_version)
picks(id, line_id, side, issued_at, entry_ref_price, structure jsonb)   -- immutable once issued
pick_outcomes(pick_id, graded_at, result, return_pct, notes)
model_registry(version, line_type, trained_through, metrics jsonb, thresholds jsonb, promoted bool)
model_portfolio_trades(id, pick_id, opened_at, closed_at, qty, entry, exit, pnl)
profiles(user_id, experience_level, risk_pct, account_size_band, max_open)
lineups(id, user_id, created_at, status)  lineup_items(lineup_id, line_id, side, structure jsonb)
alerts(user_id, symbol, rule jsonb)
```
RLS: public read on market tables; owner-only on `profiles`, `lineups`, `alerts`. **`picks` can be inserted but never updated or deleted.** That protects the track record.

---

## 6. UX spec (PrizePicks-style)

### 6.1 Board (`/`)
- **Top bar:** search (any US ticker or company name), Beginner/Advanced toggle, account.
- **Sector chips:** All · Tech · Healthcare · Financials · Energy · Consumer Disc. · Staples · Industrials · Materials · Utilities · Real Estate · Communication.
- **Timing chips:** This week · Next 2 weeks · 2–4 weeks · 1–2 months · Just reported.
- **Sort:** Radar score (default), report date, implied move, liquidity.
- **"Radar Top Picks" carousel:** the 10 highest-scoring sides across the market right now.
- **Player cards grid:** logo, ticker, name, sector tag, report date with countdown and a `Confirmed`/`Estimated` badge, price and day change, implied move `±6.4%`, liquidity tier dot, and the best line as a chip (for example, `Run-Up · BULL · Strong`).

### 6.2 Player sheet (tap a card → bottom sheet on mobile, modal on desktop)
- Header: mini price chart with earnings markers and an implied-move cone.
- List of the stock's lines. Each row shows the line name, window, key number, and two big buttons: **🐂 BULL** (green) / **🐻 BEAR** (red). The Radar Pick side has a glowing outline and a tier label.
- **Pressing a side opens the Case panel:**
  1. **The case in 3 bullets**, plain English, each with the actual number (for example, "Analysts raised profit estimates 6% in the last 30 days.").
  2. **What could go wrong**: the 2 strongest points from the other side.
  3. **Suggested trade**: Beginner shows shares, entry zone, stop, target, exit date, max loss in dollars at the user's risk setting. Advanced shows the option structure, strikes, expiry, debit, max loss/gain, and breakeven.
  4. **Confidence:** tier, plus probability if earned (rule 4 in AGENTS.md), historical hit rate, and sample size ("Won 62% of 214 similar setups since 2019").
  5. **Kills the idea if…**: invalidation triggers that the engine watches and alerts on.
  6. Buttons: `Add to Lineup` · `Deeper research →` (`/stock/[symbol]`).
- Showing both cases side by side is required, even when the model favors one.

### 6.3 Lineup slip (right drawer on desktop, bottom bar on mobile)
- Selected sides with structure and max loss; total risk vs budget; correlation and sector warnings.
- `Paper trade this lineup` creates paper positions that are tracked and graded.
- Later (Phase 7): `Send to broker`.

### 6.4 Stock research page (`/stock/[symbol]`)
- Interactive chart with past earnings markers; toggles for the implied-move cone and 50/200-day averages.
- Earnings history table: date, implied move, actual move, beat/miss, run-up return, drift return.
- Estimates and revisions chart.
- Fundamentals trend (port the SEC XBRL code).
- News feed with sources and timestamps; SEC filings links.
- Peers in the same industry and their reactions this season.
- Options snapshot: IV rank, term structure, implied move by expiry.
- Every number has an info icon showing source and as-of time.

### 6.5 Other pages
- `/picks`: the full ranked list of current Radar Picks with filters. This is the "auto-suggest" page.
- `/track-record`: every issued pick, graded, with filters; hit rate and average return by line type and tier; calibration chart; model portfolio equity curve vs SPY.
- `/learn`: 2-minute explainers (implied move, IV crush, debit spreads, position sizing).
- **Onboarding:** 4 questions (experience, account size band, risk per trade, options yes/no) that set Beginner/Advanced and sizing.

### 6.6 Design notes
- Dark theme, high-contrast BULL green / BEAR red, big touch targets, mobile-first.
- Skeleton loaders; board loads in under 1.5s from cached Supabase reads.
- Accessible: color plus icon plus text on every bull/bear state.

---

## 7. Compliance and risk guardrails (protects the business)
*Not legal advice. Talk to a securities attorney before charging money, before Phase 7, and before marketing.*

- **Stay impersonal at first.** Picks are the same for everyone, published on a regular schedule, and based on a disclosed method. Publishers that look like this usually have the strongest argument for not needing investment-adviser registration. Sizing from a user's own inputs is a calculator the user controls; keep it clearly labeled that way.
- **Automated trading for other people's accounts** (Phase 7) is the point where broker-dealer or adviser rules most likely apply. Get legal sign-off first, or partner with a registered platform's API under its own compliance program.
- **Performance claims:** the track record must include all picks, show paper vs real, show costs, and label hypothetical or backtested results as such.
- **Required UI elements:** risk disclosure on first options use (link the OCC "Characteristics and Risks of Standardized Options"), age 18+ gate, a "Not personalized advice" footer, and a methodology page.
- **Data licensing:** confirm each provider's plan allows public display.

---

## 8. Phased roadmap (Codex builds these in order in one run; see §12)

### Phase 1: Foundation and cleanup
- Create `apps/web` (Next.js 15, TypeScript strict, Tailwind, shadcn/ui, TanStack Query, Supabase SSR auth) and `engine/` (Python 3.12, `uv` or `pip-tools`, pandas, numpy, scikit-learn, pydantic, httpx).
- Move the current `web/` and `earnings_radar/` into `legacy/`. Port SEC directory, SEC XBRL fundamentals, Alpaca bars and options adapters, and the news RSS code into `engine/providers/` as **readable** code with tests.
- New Supabase migrations for the §5.2 schema plus RLS.
- CI: ruff, black, pytest, eslint, vitest, Playwright smoke test, all on PRs.
- **Accept when:** `engine` CLI `python -m engine universe_refresh` fills `securities` with at least 5,000 active rows with sector set; the web app deploys to a Vercel preview and lists them with search.

### Phase 2: Calendar, prices, options, features
- Earnings calendar adapter (two providers, merge with conflict flag, `confirmed` logic).
- Nightly EOD bars for all active tickers; liquidity tier calculation.
- Options snapshot job: ATM IV, straddle mid, implied move, IV rank (rank becomes valid after 252 days of your own data; use a provider's IV history if available).
- Estimates/revisions adapter (stub with fixtures if no paid key yet).
- Feature builder for every §2.1 feature with `as_of`.
- **Accept when:** a look-ahead test proves no feature uses data after `as_of`; for 10 large-cap fixtures the implied move matches a hand calculation within 0.1 percentage points; the calendar shows at least 1,000 events in the next 60 days during earnings season.

### Phase 3: Lines, scoring, and auto-picks
- Line generator for the five line types; win definitions per §2.4.
- Historical dataset builder (2019→present) and walk-forward logistic model per line type; calibration; `model_registry`.
- Pick ranker (§2.3), structure selector (§2.4), sizing, liquidity gating (§2.5).
- Plain-English case generator: **template-based first** (deterministic sentences from feature values), with optional LLM polishing later that may only rephrase, never add facts.
- **Accept when:** a backtest report (`engine/reports/backtest_YYYYMMDD.html`) shows, per line type and tier, hit rate, average return after estimated costs, Brier score, and comparison vs baselines; every line_side has 3 case bullets, invalidation rules, and both trade structures.

### Phase 4: The PrizePicks UI
- Board, sector and timing chips, player cards, player sheet with BULL/BEAR, Case panel, lineup slip, `/stock/[symbol]`, `/picks`.
- Beginner/Advanced toggle and onboarding.
- **Accept when:** Playwright test: open board → filter Tech → open a card → press BULL on Run-Up → see 3 bullets, suggested trade, confidence, and Deeper research link → add to lineup → lineup shows total risk. Lighthouse mobile performance ≥ 85.

### Phase 5: Model portfolio and track record
- Paper execution engine with realistic fills (mid ± half spread, commissions), entry and exit rules from §2.4.
- Immutable `picks`, nightly grading, `/track-record` with equity curve vs SPY and calibration chart.
- **Accept when:** 30 days of simulated history replay produce consistent P&L between trade log and equity curve (test).

### Phase 6: Smarter models and alerts
- LightGBM challenger, promotion rule (§2.2), feature importance shown as "what drove this pick."
- Alerts: email/push when a watchlisted stock gets a Strong pick, a date gets confirmed, or an invalidation trigger fires.
- News sentiment model; peer read-through feature.

### Phase 7: User auto-pilot (after legal review)
- Broker connection (Alpaca Trading API first, or a multi-broker aggregator), OAuth, paper mode default.
- User rules engine (tiers, max per trade, max open, sectors), one-tap confirm by default, kill switch, daily loss limit.
- Full audit log of every suggested, confirmed, and executed order.

---

## 9. Testing checklist (Codex must add these)
- Unit tests: implied move, IV rank, spread math, sizing, strike selection, every win definition.
- Look-ahead leakage test (fails if any feature timestamp > `as_of`).
- Backtest reproducibility (same seed and data give the same metrics).
- Provider adapter contract tests with recorded fixtures (no live calls in CI).
- RLS tests: user A can't read user B's lineups; nobody can update `picks`.
- UI: Playwright happy path (Phase 4) plus empty and error states (provider down → stale badge, not a blank page).

---

## 10. Environment variables
```
# engine
SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY
SEC_USER_AGENT="EarningsRadar your-email@domain"
ALPACA_API_KEY, ALPACA_API_SECRET
EARNINGS_PROVIDER_PRIMARY=finnhub|fmp|alphavantage
EARNINGS_PROVIDER_SECONDARY=...
FINNHUB_API_KEY, FMP_API_KEY, ALPHAVANTAGE_API_KEY, POLYGON_API_KEY (as chosen)
OPTIONS_PROVIDER=alpaca|polygon|tradier|orats
# web
NEXT_PUBLIC_SUPABASE_URL, NEXT_PUBLIC_SUPABASE_ANON_KEY
```

---

## 11. Your steps (things only you can do)
1. **Pick the branch.** Make `main` the single source of truth. Archive `feature/autonomous-earnings-research` (it deletes the web app).
2. **Add `AGENTS.md`** to the repo root and this file as `docs/MASTER_PLAN.md`. Mark the old `/docs/*.md` plans as superseded (add a line at the top of each) so Codex stops following them.
3. **Get API keys:** a Finnhub or FMP free key (calendar), an Alpha Vantage free key (second calendar source), plus your existing Alpaca keys. Later, one paid estimates feed and one options-history feed. Check display rights on each plan.
4. **Add secrets** to GitHub Actions (engine) and Vercel (web). Set the Vercel root directory to `apps/web` once Phase 1 lands.
5. **Run Codex once** with the build-everything prompt below. When it finishes (or stops), check `docs/PROGRESS.md` and the test results, then use the Resume prompt if anything is unfinished.
6. **Read the Phase 3 backtest report yourself.** If a line type doesn't beat its baselines, turn it off. That is what keeps the "fortune teller" honest.
7. **Book a securities-law consult** before charging or before Phase 7.

---

## 12. Codex prompts

### 12.1 Build-everything prompt (paste once)
```
Read AGENTS.md and docs/MASTER_PLAN.md fully before writing any code.

GOAL: Build the entire product in docs/MASTER_PLAN.md in a single run, working
through Phases 1 to 6 of §8 in order, then the Phase 7 scaffolding in paper-only
mode (no live broker orders; keep everything behind PAPER_MODE=true).

HOW TO WORK (do not stop to ask me questions; I am not available):
1. First, create docs/PROGRESS.md with a checklist of every phase and every
   "Accept when" item from §8. Update it as you go: [ ] todo, [~] in progress,
   [x] done, [!] blocked + reason. This file is how you resume if you are cut off.
2. Work phase by phase. For each phase:
   a. Implement everything listed for that phase.
   b. Write the phase's "Accept when" criteria as automated tests and run them.
   c. Fix failures until tests pass (max 3 fix attempts per failure; if still
      failing, mark [!] in PROGRESS.md with the error and move on).
   d. Commit with message "Phase N: <name>" and update PROGRESS.md.
3. Missing API keys or paid data: do NOT stop. Build the adapter against the
   interface, use labeled fixtures in tests, note the needed env var in
   .env.example and PROGRESS.md, and continue.
4. Ambiguity: pick the simplest option consistent with §1 (product vision),
   record it in docs/DECISIONS.md in one line, and continue.
5. Budget your effort: get every phase working end to end before polishing any
   one phase. Working and tested beats perfect and unfinished.
6. Follow every rule in AGENTS.md: readable non-minified typed code, tests,
   missing data lowers confidence + shows a badge but never blocks the whole
   feature, no hard-coded "WAIT" decisions, no new feature flags or
   "authorization" toggles beyond PAPER_MODE.
7. Only move files into legacy/; never edit or delete them otherwise.

FINISH WITH: a final commit, an updated README (setup, env vars, how to run the
engine jobs and the web app, how to deploy to Vercel + GitHub Actions), and a
summary at the end of docs/PROGRESS.md listing: what works, what's blocked and
why, every env var I must set, and the exact commands to run the tests.
```

### 12.2 Resume prompt (use only if Codex stops before finishing)
```
Read AGENTS.md, docs/MASTER_PLAN.md, docs/PROGRESS.md and docs/DECISIONS.md.
Continue the build from the first unchecked item in docs/PROGRESS.md, following
the same HOW TO WORK rules as before. Do not redo completed phases unless their
tests now fail. Do not ask me questions. Finish with the same final summary.
```

### 12.3 Tips to stretch your usage
- Run it as one long task (Codex cloud task or the CLI in full-auto mode) instead of chatting back and forth. Every follow-up message re-reads context and costs usage.
- Don't watch and interrupt. Let it run, then read `docs/PROGRESS.md` once.
- If you run low on usage mid-build, the progress file means nothing is lost. Resume after your limit resets.
