# Price history and automatic strategy implementation plan

This is a planning deliverable. The user authorized pushing the plan to main; application changes, migrations, subscriptions, and deployment actions are outside this delivery. The attached requirements are preserved in [PRICE_STRATEGY_REQUIREMENTS.md](PRICE_STRATEGY_REQUIREMENTS.md). No feature described below should be treated as implemented unless explicitly listed as current behavior.

## Feasibility under the no-payment constraint

| Category | What is possible | Limits and next step |
|---|---|---|
| Works now | Official company search, SEC disclosures and financial measures, Federal Reserve evidence, bounded daily/on-demand research, cited rule-based explanations, private watchlists, immutable research snapshots | These explain business evidence, not price forecasts. Current price history and automatic contract selection are missing. |
| Can be built without another account | Readable evidence cards, human-readable filing links, conditional automatic Up/Down business cases, clearer WAIT reasons, charts once authorized price data is available, public investor-relations/news adapters where terms permit | Requires implementation and validation; headline access does not confer full-article redistribution rights. No validated trade probabilities. |
| Needs a free account/credential, subject to verified entitlement | Limited authorized price history; optional hosted-model explanations; some economic-data series | None of the listed provider/model credentials is currently present. A free account may not include the needed exchange, historical depth, redistribution rights, or volume coverage. |
| Cannot currently promise at zero cost | Comprehensive real-time consolidated stock and options feeds, unrestricted premium publisher content, reliable live Greeks and broad historical options chains, full analyst consensus, continuous deep scanning of every security | No suitable entitlement has been verified. Design degraded modes rather than purchase services. Limited free coverage may become possible after verification. |
| Cannot promise at any price | Guaranteed profitable trades, fortune-telling, proven hedge-fund performance merely by adopting familiar formulas | Forecasts require point-in-time data and out-of-sample validation. Model explanations are not evidence of trading success. |

## Current implementation findings

- `web/api/_collector.py` collects SEC and Federal Reserve evidence. SEC is a fundamentals/disclosure source, not a market-price feed.
- `web/api/_orchestrator.py` manages per-company jobs and defaults option evaluation to WAIT. It does not select live contracts.
- `web/api/_board.py` accepts historical quantitative context when available; current Vercel inputs do not supply that context reliably. The legacy optional market-data path does not constitute a connected production feed.
- `web/public/app.js` renders Up/Down as user-selected hypotheses and a research lineup. Replace the hypothesis-only explanation with a server assessment of the selected direction; retain rejection of unsupported cases.
- Source links can open machine-readable financial endpoints. Present extracted financial facts directly and prefer the associated readable filing/document for ordinary users.
- `radar_research_snapshots` records research-only decisions. Its existence does not establish price forecasts or evaluated trading performance.
- Preserve existing accounts, saved ideas, watchlists, and records. Never send service-role credentials to the browser.

## Provider investigation and recommendation

Current official pricing/documentation retrieval attempts on 2026-10-07 failed for Alpha Vantage, Twelve Data, and Alpaca. Consequently, exact current quotas, entitlements, and redistribution permissions are **not verified**. Confirm them before implementation; do not hardcode remembered limits.

| Candidate | Proposed role | Verification required |
|---|---|---|
| [Alpaca](https://docs.alpaca.markets/docs/about-market-data-api) | First candidate for US daily stock history, consistent with the existing optional adapter | Free entitlement, exchange/feed coverage, adjustments, delay, volume scope, historical depth, display rights; separately verify options entitlement |
| [Twelve Data](https://twelvedata.com/pricing) | Candidate fallback for supported daily OHLCV | Free credits, supported instruments, adjustment behavior, exchange restrictions, public display rights |
| [Alpha Vantage](https://www.alphavantage.co/premium/) | Candidate low-volume alternative | Which daily/adjusted endpoints are free, daily quota, commercial/display terms; do not assume a free key unlocks all endpoints |
| [Nasdaq Data Link](https://data.nasdaq.com/) | Supplemental dataset-specific research | Each dataset's license, cost, update cadence and coverage; membership is not a blanket free market feed |
| Yahoo Finance | Only if permitted access is documented | Authorized access and production/display terms; unofficial endpoints are not the default fallback |
| Official company IR, Fed, BLS, BEA and permitted publisher feeds | Event/context evidence | Available feeds, permitted excerpts, attribution and timestamps; no restricted article scraping |

Provisional recommendation: evaluate Alpaca first, with Twelve Data as a candidate fallback. Make the final selection after an actual free-key request and terms review. Do not combine incompatible feeds silently. News outlets help explain events; exchange-aware market-data services supply price history.

Credential names only: `ALPACA_API_KEY`, `ALPACA_API_SECRET`, `TWELVE_DATA_API_KEY`, `ALPHA_VANTAGE_API_KEY`, optional `GROQ_API_KEY`, optional `FRED_API_KEY`. Confirm the eventual adapters' variable names before configuration. Enter secrets through environment settings, never chat or Git. The Groq adapter remains disabled unless explicitly configured; do not activate paid usage.

## Architecture and database changes

Add provider adapters exposing normalized historical bars, corporate actions, news events, and optional option chains. Every response includes provider, exchange/feed, currency, session timezone, delay, retrieval timestamp and license/display constraints. Raw and adjusted series remain distinguishable. Cache server-side and reuse the existing durable job leases and bounded queues.

Proposed additive tables:
- `radar_price_bars`: symbol, session, provider, feed, OHLCV, currency, adjustment mode, retrieved time and revision identity.
- `radar_corporate_actions`: symbol, ex-date, split/dividend details, provider and observed time.
- `radar_news_events`: publisher, headline, permitted excerpt, article URL, publication/retrieval times, symbols, story identity and correction metadata.
- `radar_features`: symbol, as-of cutoff, method version, lookback/sample size, feature values and exact input identities.
- `radar_option_quotes`: contract identifier, expiry, strike, type, multiplier, bid/ask, quote time, provider, permitted IV/Greeks/activity fields and their timestamps.
- `radar_strategy_assessments`: direction, WATCH/WAIT/candidate, evidence, counterevidence, catalyst, horizon, invalidation, missing inputs and method version.
- `radar_forecast_outcomes`: immutable forecast reference, target/horizon, evaluation price identities, costs and outcome status. Research-only snapshots remain distinct from issued forecasts.

Use indexes on symbol/session/as-of, unique provider identities, bounded retention for quote caches, and server-only access for provider records. Private account tables retain current RLS. Never rewrite historical decision snapshots when new data arrives.

Proposed server endpoints: company price history, company events, selected-direction assessment and contract comparison. Apply query bounds, same-origin writes, rate limits and sanitized errors. Return structured unavailable/stale states rather than empty-looking fabricated charts.

## Research methods and automated decisions

Start with transparent research measures: adjusted log returns, 20/60-session annualized realized volatility, ATR, benchmark-relative return, drawdown, abnormal volume and cash-flow/debt ratios. Report sample counts, definitions and units. Use an exchange session calendar; do not count calendar days as trading sessions.

Document methodological foundations: Black–Scholes–Merton assumptions/limitations for option sensitivities, Engle's ARCH volatility-clustering framework, Parkinson's range estimator, and published momentum research such as Jegadeesh–Titman. These are starting points to evaluate, not guarantees or replicas of proprietary investors' systems. Avoid double-counting correlated indicators or tuning thresholds on the evaluation set.

Keep direction, movement magnitude, company funding liquidity, trading liquidity and systemic funding stress separate. A low-volatility period alone does not imply a breakout; revenue growth alone does not imply a call is attractive. Match fiscal periods and define appropriate peer/market benchmarks.

When a user taps Up or Down, request the corresponding backend assessment automatically. Return a plain-language summary, supporting and opposing evidence, confirmed catalyst if available, research horizon, scenario ranges, invalidation conditions, freshness and the decision. A button selection never forces approval. With incomplete market inputs, supply a conditional business case and explain WAIT. Do not request manual strikes, premiums or a thesis.

Only compare contracts after authorized fresh chains exist. Screen spreads, quote age, expiration relative to the event, activity/open interest with reporting dates, multiplier and IV/Greeks where actually supplied. Compute premium-at-risk and expiry break-even; distinguish expiry payoff from modeled pre-expiry value. Explain time decay and volatility-crush scenarios. Do not size positions without portfolio/risk-budget information or place orders.

Optional model explanations must use retrieved evidence, validate source references and numeric claims, and treat documents as untrusted data. No unsupported probabilities. A model failure falls back to deterministic explanations.

## Phases and acceptance tests

### Phase 1: Price history and readable evidence

Verify provider terms/credentials, connect a daily-bar adapter, backfill a bounded universe, cache revisions and add 1M/3M/6M/1Y charts where enough observations exist. Replace raw-data links with readable cards and optional technical details.

Acceptance: live permitted prices for at least three previously unseeded companies; known-split and dividend handling; closed-session/date alignment; missing-session detection; provider failure serves clearly aged cache; no fabricated volume; chart accessibility and mobile checks; source figures/periods trace correctly to readable filings. No “live” label on delayed data.

### Phase 2: Automatic Up/Down and broader events

Add permitted IR/news adapters, deduplicate events, calculate point-in-time features and return conditional directional assessments without user-entered financial inputs. Integrate with cards and lineup. Bound daily jobs and anonymous on-demand work.

Acceptance: Up and Down produce server explanations and counterevidence; unsupported direction yields WAIT; conflicting sources are visible; syndicated news is not counted repeatedly; absent catalyst is unknown; no headline/price causation claim without evidence; retry/backoff and workload-cap tests; private records remain isolated.

### Phase 3: Authorized option comparison

Proceed only if a verified entitlement provides the necessary chain and quote fields within the no-payment constraint. Otherwise retain WAIT and deliver the provider-ready interface without pretending it selects executable trades.

Acceptance: stale quotes/wide spreads/unknown multipliers rejected; event-after-expiry rejected; missing Greeks/IV never synthesized as provider facts; call/put payoff checks; no position-size recommendation; no broker credentials or execution.

### Phase 4: Evaluation and qualified forecasts

Define direction/magnitude/volatility targets before fitting. Store point-in-time inputs, perform chronological walk-forward validation against simple baselines and reserve an untouched evaluation period. Address survivorship, corrected data, multiple testing, spreads/fees and realistic fills. Validate calibration before publishing probabilities. Historical options evaluations require suitable actual data, not reconstructed fictional chains.

Acceptance: future records cannot enter features; sample size, costs, calibration and out-of-sample uncertainty displayed; research-only snapshots excluded from trading win rates; no performance claims until evaluation passes predefined gates. Any unavailable dataset remains a declared blocker.

## Immediate next action

Implement readable evidence and conditional automatic business assessments without new credentials. In parallel, verify a permitted free daily-price provider using secure credentials. Price charts cannot be completed merely by adding a news homepage link. Broad live option selection and validated forecasts remain separate gated phases; do not purchase services to remove those gates.
