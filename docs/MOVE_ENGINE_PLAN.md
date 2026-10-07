# Earnings Radar v2: The Move Engine (Codex handoff)

> Save as `docs/MOVE_ENGINE_PLAN.md`. It **overrides** `docs/MASTER_PLAN.md` and `docs/DECISIONS.md` wherever they conflict. Paste the single prompt in §10 into Codex.

---

## 0. Why the site still says "Research pending" and BULL = BEAR (diagnosis of commit `2d9c8d5`)

| Symptom on screen | Cause in code | Fix |
|---|---|---|
| **Research pending** on MU | `engine/run.py` scores only a hard-coded seed list: `--symbols AAPL,MSFT,NVDA,AMZN,META,GOOGL,TSLA,JPM,XOM,SPY`. MU was never scored. | Score every symbol the earnings calendar returns for the next 60 days, plus on-demand scoring when a user opens any ticker (§6). |
| **Report date not connected** | Finnhub adapter failed ("host binding is incorrect" in `docs/PROGRESS.md`), and the Alpha Vantage key was absent. | Fix the Finnhub auth (`?token=` query param, add a `engine doctor` key check) and add the Alpha Vantage key. |
| **Unclassified** sector | SIC → sector enrichment never ran. | Pull `sic` from SEC submissions for every active symbol and map it to sectors. |
| **BULL and BEAR show the same text** | `engine/lines.py` builds both sides from one shared bullet list (20-day momentum plus generic sentences) and sets `favored = None` on every earnings line. | Each side gets **its own evidence**: features that push up go to BULL, features that push down go to BEAR (§4). |
| **No trade ever shows** | `engine/options.py` rejects any contract whose `feed != "opra"`. Alpaca's free options feed is "indicative," so 100% of contracts are rejected. | Allow indicative quotes for estimates (implied move, IV, suggested strikes), labeled `Indicative quote`. Require OPRA only for the "executable price" badge. |
| **No probabilities / no picks** | `docs/DECISIONS.md` says "free services only," "no expected-value ranking," "never a quantity recommendation." Features are only `last_close`, `return_20`, `atr_14`. | Build the historical earnings dataset from free data (§3), train the Move model, and rank picks. Those DECISIONS lines are revoked (§9). |
| Live site is a protected preview | Vercel production root is still `web` (the old app). | After this build passes, switch the Vercel root directory to `apps/web`. |

---

## 1. The core idea: predict the size of the move, not just the direction

For an earnings options trader, the most useful question is: **"Will this stock move more or less than the options market is pricing in?"**

- **Magnitude is more predictable than direction.** A stock's own history of earnings moves, its implied move, the volatility setup, and analyst disagreement say a lot about how big a move could be. Direction around earnings is close to a coin flip for most models. The app should be honest about that.
- The options market publishes its own forecast: the **implied move**. The edge is spotting when that forecast is too small (buy volatility) or too big (sell volatility, defined risk only).

So every stock gets two kinds of "props," which is a real PrizePicks over/under:

| Prop | Line | Buttons | Trade expression |
|---|---|---|---|
| **Earnings Move** | implied move, e.g. `±7.2%` | **MORE** / **LESS** | MORE → long straddle/strangle; LESS → iron condor / iron fly (advanced, defined risk) |
| **Direction** | report reaction | **BULL** / **BEAR** | BULL → call or call debit spread; BEAR → put or put debit spread |
| **Run-Up** | today → day before report | **BULL** / **BEAR** | Shares or a debit spread, **closed before the report** |
| **IV Ramp** | IV now → IV the day before the report | **MORE** / **LESS** | MORE → buy a straddle 2–4 weeks early, sell before the report (captures the IV build without earnings risk) |
| **Drift** | report +1 → +20 sessions | **BULL** / **BEAR** | Shares or a 30–45 day debit spread |

At the top of each card, a **Move Meter (0–100)** answers "is a big move coming?" at a glance:
`Move Meter 84 · BIG MOVE LIKELY · priced ±6.1%, our model ±8.9%`

---

## 2. Signals the Move Engine needs

### 2.1 Volatility and options (what the market expects)
| Feature | How to compute | Source |
|---|---|---|
| `implied_move` | ATM straddle mid ÷ spot, using the first expiry **after** the report | options snapshot |
| `event_vol` | Uses two expiries after the event, T1 < T2: `σ_base² = (σ2²·T2 − σ1²·T1)/(T2 − T1)`, then `event_move = sqrt(σ1²·T1 − σ_base²·T1)`. Cross-check against `implied_move` | options snapshot |
| `iv_rank_252`, `iv_percentile_252` | front ATM IV vs its own past year | own snapshot history, or a provider's IV history |
| `term_kink` | front IV ÷ next-month IV (> 1.1 = event premium building) | snapshot |
| `iv_ramp_hist` | this ticker's average front-IV change from T-20 to T-1 over past reports | snapshot history |
| `skew_25d` | 25-delta put IV − 25-delta call IV (fear vs greed) | snapshot with greeks |
| `options_volume_ratio` | today's options volume ÷ 20-day average; call/put volume ratio | snapshot |
| `oi_change_5d` | change in open interest near the money | snapshot |

### 2.2 History (what this stock usually does), all from free data
| Feature | How |
|---|---|
| `hist_abs_move_mean/median/max` | absolute close-to-close move across each past report (AMC → next day, BMO → same day), last 12 reports |
| `hist_exceed_rate` | share of past reports where the move beat the then-implied move (once implied-move history exists), else beat the trailing median |
| `implied_vs_hist` | `implied_move ÷ hist_abs_move_mean` (< 0.8 = options look cheap, > 1.3 = rich) |
| `runup_hist_mean`, `runup_hit_rate` | T-20 → T-1 return history |
| `drift_hist_mean` | T+1 → T+20 return history |
| `gap_fill_rate` | how often the earnings gap reversed within 5 sessions |

### 2.3 Setup going into the event
| Feature | Why it matters |
|---|---|
| `rv_10 / rv_60` (realized-vol compression) | coiled-spring setups often break big |
| `bb_width_pctile` (Bollinger band squeeze) | same idea |
| `return_5/20/60`, `rs_vs_sector_20` | direction and crowding |
| `dist_52w_high`, `dist_200dma` | stretched stocks gap harder on misses |
| `short_interest_pct_float`, `days_to_cover` | squeeze fuel on beats |
| `estimate_revision_30d` (EPS and revenue) | the "investors expect good news" signal for Run-Up |
| `estimate_dispersion` (high − low ÷ mean) | analyst disagreement → bigger moves |
| `beat_rate_8q`, `avg_surprise_8q`, `guidance_history` | track record |
| `peer_reaction_season` | average move of same-industry stocks that already reported this season |
| `news_count_7d`, `news_sentiment_7d` | attention and tone |
| `days_to_report`, `date_confirmed`, `report_time` | timing |
| `vix`, `spy_trend_20` | market regime |

---

## 3. Data: what you need to add, and what each tier gets you

> Verify current prices, rate limits, and public-display rights before buying. Plans change often.

| Tier | Providers | What it unlocks |
|---|---|---|
| **Free (do now)** | **Finnhub** (upcoming calendar, recent earnings surprises, news), **Alpha Vantage** (`EARNINGS` gives each company's past report dates and surprises; `EARNINGS_CALENDAR` gives the next 3 months), **Alpaca** (daily bars back to 2016, indicative options snapshots with IV/greeks, news), **SEC** (universe, SIC sectors, fundamentals), **FINRA** short interest files | Calendar, sectors, full historical move stats, run-up/drift history, **live indicative implied move and IV**, Move model v1 trained on historical moves. **This alone fixes everything in §0.** |
| **Recommended (low-cost paid)** | One options data plan with full chains, greeks, and historical snapshots (Polygon/Massive Options, or Tradier through a brokerage account); one fundamentals/estimates plan with historical earnings calendar and **estimate revisions** (Financial Modeling Prep or similar) | Faster full-chain coverage across thousands of tickers, skew and OI features, estimate revisions and dispersion, longer backtests |
| **Pro** | ORATS (historical earnings implied moves and IV going back years), an options-flow feed (unusual activity) | Trains MORE/LESS against **historical implied moves** right away instead of waiting for your own snapshot history to build up |

**Rate-limit strategy for free tiers:** Alpha Vantage's free tier allows very few calls per day. Use it once per symbol to backfill historical report dates (cache permanently; it only changes once a quarter), spread across days, earnings-calendar names first. Use Finnhub for daily calendar refreshes. Use Alpaca multi-symbol bar requests.

**Start collecting your own options history on day one.** Every day, save ATM IV, straddle mid, implied move, skew, and volume for every symbol with a report within 60 days. After 1–2 earnings seasons you have your own implied-move history for free.

---

## 4. Models and how BULL and BEAR get different content

### 4.1 Models (walk-forward, point-in-time)
1. **Magnitude model** (most important). Target A (free data): `|move| > trailing median |move|` for that ticker. Target B (once implied history exists): `|move| > implied_move` (this is MORE/LESS). Gradient-boosted trees (LightGBM) with a logistic-regression baseline. Output `P(MORE)` and a predicted move size (quantile regression for the 50th/80th percentile `|move|`).
2. **Direction model.** Target `sign(move)` on report day; separate models for Run-Up (T-20→T-1) and Drift (T+1→T+20). Expect weak skill. Show it honestly.
3. **IV Ramp model.** Target: front IV at T-1 > IV now (needs snapshot history; until then use `iv_ramp_hist` rules).
4. **Move Meter** = `100 × P(big move)`, calibrated, where big = top tercile of `|move| ÷ hist_median` (or `> implied` once available).

Training data: every report since 2016 for every symbol with enough liquidity at that time, using Alpaca daily bars plus Alpha Vantage/Finnhub historical report dates. That is tens of thousands of events. Walk-forward folds by year. Save Brier score, AUC, a reliability table, and a comparison against baselines ("always MORE," "implied_vs_hist rule") to `model_registry`.

### 4.2 Side-specific explanations (the BULL ≠ BEAR fix)
- Compute each feature's signed contribution to the direction model (SHAP values for trees, coefficient × standardized value for logistic).
- **BULL panel** = the top 3 positive contributors; **BEAR panel** = the top 3 negative contributors. Each is rendered from a sentence template with the real number:
  - `estimate_revision_30d = +6.2%` → BULL: "Analysts raised profit estimates 6.2% in the last 30 days."
  - `dist_52w_high = −1%` → BEAR: "It's trading within 1% of its 52-week high, so a miss has further to fall."
  - `hist_abs_move_mean = 9.1%` vs `implied_move = 6.0%` → MORE: "It has moved 9.1% on average over its last 12 reports; options are pricing 6.0%."
- Each side also shows "What the other side says" (the opposing top 2), so both views appear on every panel, but the lead content differs.
- The **Radar Pick** is the side with the higher model score, always shown with a tier. When the model has no edge (score within ±2 points of the midpoint), the label is `No edge · coin flip`. That is still a result, not "pending."
- **Unit test:** for any symbol, BULL bullets ≠ BEAR bullets, and every bullet contains at least one number.

---

## 5. Trade construction (auto-selected per prop)

| Prop · side | Default structure | Strike/expiry rule | Exit |
|---|---|---|---|
| Earnings Move · MORE | Long straddle (ATM) or strangle (±0.5× implied move) if straddle cost > 1.2× predicted move | first expiry after report | Close at the next open after the report, or at +50% |
| Earnings Move · LESS | Iron fly / iron condor, wings at ±1.5× implied move (**Advanced mode only**) | first expiry after report | Close at the next open after the report |
| Direction · BULL/BEAR | Debit spread: long at ~0.50 delta, short at the 1× implied-move strike | first expiry after report | Next open after report, or a target/stop |
| Run-Up · BULL/BEAR | Shares with a 1.5× ATR stop, or a debit spread | expiry ≥ report date + 7 days | **Exit the session before the report** |
| IV Ramp · MORE | Long straddle 14–30 days before report | expiry after report | **Exit the session before the report** |
| Drift · BULL/BEAR | Shares with a trailing stop, or a 30–45 day debit spread | | 20 sessions |

- **Quote rules:** use the mid for estimates. Show `Indicative quote` when the feed isn't OPRA. Reject only crossed or zero quotes, or spreads > 25% of mid (show `Wide spread` for 10–25%).
- **Sizing:** if the user set an account size and risk % (default 1%, max 3% for the user's own choice), compute contracts = `floor(budget × risk% ÷ max_loss_per_contract)`. If not set, show the cost and max loss of 1 contract.
- **Expected value per prop:** use the magnitude model's predicted move distribution (the quantiles) to price the structure's payoff at expiry, minus the spread cost. Rank picks by `EV ÷ max loss`.

---

## 6. Full automation (no more "pending")

| Job | Schedule (ET) | Scope |
|---|---|---|
| `universe` + `sectors` | daily 06:00 | all active SEC tickers, SIC → sector |
| `calendar` | 06:15 and 18:00 | Finnhub next 60 days, plus Alpha Vantage 3-month calendar (one call), reconciled |
| `history_backfill` | nightly, within rate limits | historical report dates per symbol (cached forever), calendar names first |
| `bars` | 17:30 | all symbols in the calendar window + sector ETFs + SPY + VIX proxy, multi-symbol requests |
| `options_snapshot` | 09:45, 12:00, 15:30 | every symbol reporting within 45 days that passes liquidity (ADV ≥ $5M, price ≥ $5) |
| `features` + `score` + `picks` | after each snapshot, and 20:00 | same set |
| `grade` | 17:45 | expired props |
| `train` | Sunday | walk-forward retrain; promote only if it beats the current model out of sample |
| **on-demand** | when a user opens an unscored ticker | insert into `score_queue`; a GitHub Actions `repository_dispatch` (or a 5-minute cron that drains the queue) scores it within minutes; the UI shows `Scoring… usually under 5 minutes` with a spinner instead of "Research pending" |

Batching: process in chunks of 100 symbols; retry with backoff; keep each job under the GitHub Actions time limit by splitting across a matrix.

---

## 7. UI changes (PrizePicks feel)

- **Board default:** "Reporting this week," sorted by Move Meter. Tabs for This week · Next week · 2–4 weeks · 1–2 months · Just reported, plus sector chips.
- **Card:** ticker, name, sector (never "Unclassified" for SIC-mapped names), report date and BMO/AMC with `Confirmed`/`Estimated`, **Move Meter gauge**, implied move vs model move, the hottest prop as a chip (e.g. `MORE ±7.2% · Strong`).
- **Player sheet:** list of props. Each prop row has the line value and two big buttons (MORE/LESS or BULL/BEAR). The Radar Pick side glows. Tapping a side opens its own case panel (§4.2), the auto-built trade (§5), confidence tier, hit rate, sample size, and "Deeper research →".
- **Big Move Alerts** page: every stock whose Move Meter ≥ 75, or whose `implied_vs_hist < 0.8`, with push/email alerts for watchlisted names.
- **Lineup slip:** total premium at risk, number of same-day reports, sector concentration, and "Paper trade this lineup."
- **Track record:** graded MORE/LESS and BULL/BEAR hit rates by tier, calibration chart, paper P&L.
- Replace any remaining "Research pending" / "Report date not connected" labels with actionable states: `Scoring…`, `Date estimated`, `No report in next 60 days`, `Options too thin for trades`.

---

## 8. Acceptance tests (Codex must add them)
1. `engine doctor` checks every API key and prints OK/FAIL per provider.
2. After a `calendar` run in earnings season: ≥ 1,000 events in the next 60 days, and ≥ 95% of calendar symbols have a sector.
3. MU (and any calendar symbol) has a scored card after the nightly run; opening an unscored ticker produces a score within one queue cycle (test with a mocked dispatcher).
4. `implied_move` matches a hand calculation within 0.1 percentage points on fixtures; the `event_vol` formula is unit-tested.
5. The historical dataset holds ≥ 20,000 report events; a look-ahead test proves no feature uses data after `as_of`.
6. The magnitude model beats both baselines out of sample on Brier score (report saved). If it doesn't, the UI shows `No edge` rather than fake confidence.
7. For every scored symbol, BULL bullets ≠ BEAR bullets and MORE ≠ LESS, each with a number.
8. Every prop with a liquid chain shows a concrete structure: strikes, expiry, debit/credit, max loss, breakeven.
9. Playwright: open board → card with Move Meter → MORE on Earnings Move → see case, straddle, max loss → add to lineup.

---

## 9. Revoked decisions (replace these lines in `docs/DECISIONS.md`)
- ~~"Free services only."~~ → Free first; paid adapters are built and switched on by env var when a key is present.
- ~~"No expected-value ranking."~~ → Rank by EV ÷ max loss from the magnitude model's move distribution (§5).
- ~~"Never a quantity recommendation."~~ → Size from the user's own account and risk settings; without them, show one-contract cost and max loss.
- ~~Reject non-OPRA quotes.~~ → Indicative quotes are allowed for estimates, labeled `Indicative quote`.
- ~~Hard-coded seed symbol list.~~ → Calendar-driven universe plus an on-demand queue.

---

## 10. Single Codex prompt (paste once)
```
Read AGENTS.md, docs/MASTER_PLAN.md, and docs/MOVE_ENGINE_PLAN.md. MOVE_ENGINE_PLAN
overrides MASTER_PLAN and DECISIONS.md where they conflict. First apply §9 to
docs/DECISIONS.md.

GOAL: Implement all of docs/MOVE_ENGINE_PLAN.md in one run: fix every row in §0,
build the features in §2, the free-tier adapters in §3 (paid adapters behind env
vars), the models and side-specific explanations in §4, trade construction in §5,
the automation and on-demand queue in §6, the UI in §7, and every test in §8.

HOW TO WORK (I am not available; do not stop to ask):
1. Add a "Move Engine" section to docs/PROGRESS.md with a checkbox per §0 row and
   per §8 test. Update it as you go.
2. Order: §0 fixes → engine doctor → calendar + sectors → history backfill + bars →
   options snapshot + implied move → features → models → explanations → trades →
   jobs/queue → UI → tests. Commit after each step: "Move Engine: <step>".
3. Missing key or rate limit: build the adapter, use labeled fixtures in tests, log
   it in PROGRESS.md, continue.
4. Ambiguity: choose the option that gives the user a concrete, honest answer
   (a score, a tier, a trade, or "No edge") over hiding the feature. Log it in
   DECISIONS.md in one line and continue.
5. Never show "Research pending" or a blank side. Never give BULL and BEAR the same
   text. Never invent a quote, date, or probability; label estimates.
6. Readable typed code, tests in CI, no new feature flags beyond PAPER_MODE.

FINISH WITH: a PROGRESS.md summary (what works, what's blocked and why, keys still
needed), README updates for new jobs and env vars, and the exact steps to switch
the Vercel production root from `web` to `apps/web`.
```
