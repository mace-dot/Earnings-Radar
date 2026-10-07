# Master plan progress

Implementation started 2026-10-07. Production remains the existing app until the replacement is tested.

- [ ] Phase 1: Next.js foundation, Python engine, additive schema, searchable official directory.
- [ ] Phase 2: Provider adapters, calendar reconciliation, point-in-time features.
- [ ] Phase 3: Two-sided lines, trade economics, validated models.
- [ ] Phase 4: Accessible board, player sheet, deep research, lineup.
- [ ] Phase 5: Immutable picks, grading, public track record.
- [ ] Phase 6: Challenger evaluation, news/peer context, opt-in alerts.
- [ ] Phase 7: Paper-only execution scaffolding.

Unavailable credentials, entitlements, historical training data and acceptance checks must remain explicitly marked as blocked, not passed.

## Verified foundation — 2026-10-07

- Adopted the new master spec without deleting the working site.
- Additive schema applied to Supabase: source-stamped identifiers/bars/events/features/lines, immutable picks, outcomes, private owner policies.
- Imported 10,434 SEC identifiers (includes unverified asset types; not 10,434 eligible common stocks).
- Imported 2,900 actual Alpaca IEX daily bars for ten seed instruments.
- Generated 50 two-sided research lines; probabilities null and cases explicitly unvalidated.
- Next.js production build, strict type check, Vitest (3), old pytest (118), engine pytest (20), and Chromium Playwright live-database smoke (1) passed.
- Playwright checked search → BULL case → trade context → lineup → daily price chart.

## Acceptance criteria still open

Phase 1: common-share classification and 5,000-sector enrichment; authenticated Vercel preview verification.
Phase 2: two working calendars, full-universe bars, 252-session historical IV, revisions and fundamentals integration, 1,000 live events. Finnhub host binding is incorrect; Alpha Vantage key absent.
Phase 3: actual point-in-time historical event dataset, calibrated logistic model, baseline comparisons and paper P&L. Challenger tested with fixtures only. No active predictions.
Phase 4: saved private lineups/profiles, onboarding, complete research sections and Lighthouse measurement. Session-only lineup exists.
Phase 5: scheduled immutable pick publication, grade-all outcomes, equity curve and 30-day replay. Schema and direction-grading code exist; no performance claimed.
Phase 6: news/peer analysis, untouched challenger evaluation and opt-in alerts not implemented.
Phase 7: no brokerage execution. Paper-only status is visible; one-tap simulator not implemented.

GitHub Actions workflow is committed but activation/secrets cannot be verified because the Actions-secret API returned HTTP 403. Existing production root remains `web`. The new app runs alongside it; this foundation is not completion of the seven-phase master plan.
