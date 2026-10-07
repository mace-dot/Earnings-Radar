# Implementation status and operating limits

The implementation uses the supplied research specifications and the proposed JSON contract in `web/api/research_policy.json`. The JSON is deliberately marked proposed: thresholds are research hypotheses, not validated investor rules. No paid services, trading or external notifications are activated.

## Implemented in dependency order

1. **Market foundation:** secret-safe capabilities and administrator diagnostics; bounded IEX quote adapter with typed validation, shared database leases, rate bounds, stale states and public-use gating. Existing completed-session history remains available when permitted. Provider failures retain eligible caches. Credentials configured is not confused with usable observations or public-use permission.
2. **Deep evidence:** SEC companyfacts batching; additional debt, capital, share-count and compensation facts; issuer SIC context; sector-specific suppression of inappropriate generic funding ratios. Human-readable filing links and primary passages remain available.
3. **Autonomous decisions:** ten bounded logical analyst roles implemented as deterministic evidence/calculation workflows; separate business/timing/contract verdicts; source grouping; two-sided cases; source-cutoff filtering; content-based immutable IDs; change comparison; policy audit fields; atomic lease-checked snapshot publication. These are not ten independently reasoning hosted LLMs.
4. **Option research:** gated snapshot source adapter; OCC identity checks, expiry, spread, freshness, delta and metadata checks; long-call/put expiry payoff functions; missing metadata and indicative feeds explicitly rejected for executable conclusions. No contract is made eligible by an AI narrative.
5. **Evaluation:** immutable underlying-monitor outcomes, strict decision-time references, future-session horizons, corporate-action discrepancy checks, no simulated option results or invented win rates. An immutable draft/review registry and bounded offline walk-forward evaluator are included, with Brier/log-loss baselines, calibration bins, outcome-time purging and event-group exclusions. Training/live model activation, uncertainty estimation and historical executable-option replay remain additional work. Forecasts remain disabled.
6. **Interface:** automatic brief, next checks, change summary, playbooks, source passages, sector context, separate verdicts, bounded price checks, automatic contract checks, source capability view, outcome cards, mobile layout and reduced-motion support. The automatic board remains independent of private watchlists.

## Remaining external prerequisites

- Public use of Alpaca equity observations must be verified before `RADAR_MARKET_DISPLAY_AUTHORIZED=true`. Authentication has been tested; it does not establish redistribution rights. Neither this migration nor code enables that flag.
- Options use requires verified permission (`RADAR_OPTIONS_DISPLAY_AUTHORIZED`), an appropriate feed (`RADAR_OPTIONS_FEED`), verified contract metadata and calendar/session handling. Basic indicative data cannot become executable OPRA quotes by changing a label.
- Hosted generative interpretation requires a supported free-account key/quota and deliberate `RADAR_AI_ENABLED` activation. No key is manufactured and no paid model is enabled. Deterministic evidence analysis works without it.
- Continuous streaming needs persistent compute. Current Vercel mode remains bounded on-demand calls plus a daily cron. A full-universe 24/7 research sweep is not supported by this free configuration.
- Forecast promotion requires point-in-time datasets, training, uncertainty analysis and untouched evaluation. Historical underlying bars do not validate option profitability.

## Operations

`GET /api/capabilities` exposes safe capability states. `GET /api/diagnostics` requires the existing cron bearer secret and returns counts/statuses, never raw keys or probed prices. `GET /api/quote?symbol=AAPL` and `/api/options?symbol=AAPL` enforce feed-use gates. Do not make the service-role key public. The new cache/evaluation tables have RLS enabled, no anon/authenticated grants and server-only access. Immutable evaluations never modify decisions.

Apply `supabase/migrations/202610070006_autonomous_workflow.sql` and `202610070007_validation_registry.sql` in order before deploying the new backend. It is additive and preserves account/watchlist/research records. Verify table permissions and RPC signatures. Existing Vercel GitHub auto-deploy uses `main` and root `web`.

No calibrated predictor, exact liquidity-crisis timer, private hedge-fund replica, licensed news archive or successful-option guarantee is delivered by this release. The application should remain useful while clearly reporting these gaps.

## Release verification

- 118 Python tests passed, including point-in-time filtering, sector exclusions, source parsing, option economics, quote gates and offline evaluation behavior.
- `npm run build` passed navigation, source safety, automatic cases, hosted-chart URL handling, accessible historical chart and research-brief DOM checks. External hosted-chart pixels/quotes were not inspected.
- Alpaca read-only checks returned 384 completed daily bars each for AAPL and SPY; descriptive statistics and beta calculated. These checks did not publish prices or enable public-use flags.
- Actual SEC quarterly and annual AAPL documents yielded readable passages; JPMorgan SIC classification suppressed generic funding ratios.
- Live Supabase checks verified idempotent decision insertion, RLS/privilege restrictions and rejection of publication without an owned lease. The additive workflow migration was applied twice successfully.
- Offline evaluation CLI was exercised with a hypothetical fixture. That is software verification, not trading-performance evidence.
