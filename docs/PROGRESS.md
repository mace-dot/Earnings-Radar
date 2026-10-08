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
- Imported 2,890 completed-session Alpaca IEX daily bars for ten seed instruments.
- Generated 50 two-sided research lines; probabilities null and cases explicitly unvalidated.
- Next.js production build, strict type check, Vitest (3), old pytest (118), engine pytest (23), and Chromium Playwright live-database smoke (1) passed.
- Playwright checked search → BULL case → trade context → lineup → daily price chart.

## Acceptance criteria still open

Phase 1: common-share classification and 5,000-sector enrichment; authenticated Vercel preview verification. Vercel reports the protected preview READY at https://earnings-radar-7yx3juvjb-mace16.vercel.app/.
Phase 2: two working calendars, full-universe bars, 252-session historical IV, revisions and fundamentals integration, 1,000 live events. Finnhub host binding is incorrect; Alpha Vantage key absent.
Phase 3: actual point-in-time historical event dataset, calibrated logistic model, baseline comparisons and paper P&L. Challenger tested with fixtures only. No active predictions.
Phase 4: saved private lineups/profiles, onboarding, complete research sections and Lighthouse measurement. Session-only lineup exists.
Phase 5: scheduled immutable pick publication, grade-all outcomes, equity curve and 30-day replay. Schema and direction-grading code exist; no performance claimed.
Phase 6: news/peer analysis, untouched challenger evaluation and opt-in alerts not implemented.
Phase 7: no brokerage execution. Paper-only status is visible; one-tap simulator not implemented.

GitHub Actions workflow is committed but activation/secrets cannot be verified because the Actions-secret API returned HTTP 403. Existing production root remains `web`. The new app runs alongside it; this foundation is not completion of the seven-phase master plan.

## Release checks

Pushed implementation to GitHub main. Vercel preview READY, authenticated viewing required by the existing project protection setting. Production project settings confirmed unchanged (`web`, Python, `public`).

An additional guard caught a still-forming daily bar; ingestion now excludes incomplete sessions, the ten erroneous new-schema rows were removed, and scoring succeeded again. A provider regression test covers this case. Existing research data was preserved.

Environment install/start instructions saved as a draft using the onboarding skill. Saving did not publish or apply the draft; review/save/publish in Environment settings is required for future-session reuse.

# Move Engine implementation

This section supersedes earlier connection diagnoses where new probes establish otherwise.

## Diagnosis fixes (§0)

- [x] Removed default seed-only scoring; scope comes from calendar, existing research and requested symbols.
- [x] Working Finnhub binding found (`FINN_HUB`); imported 1,361 calendar entries. Alpha Vantage fallback remains unavailable.
- [x] Upcoming calendar-sector coverage: 1,361 entries, 96.03% SIC-derived sectors. Micron classified from SIC 3674.
- [x] Distinct numeric BULL/BEAR and MORE/LESS evidence templates; missing inputs remain explicit.
- [x] Indicative option estimates allowed, separate from executable quotes.
- [ ] Actual trained magnitude model, validated probabilities and EV-ranked picks.
- [ ] Switch production root after release acceptance; protected new-app preview used meanwhile.

## Acceptance tests (§8)

- [x] Provider doctor implemented and run: Supabase, SEC, Alpaca prices/options, Finnhub work; Alpha Vantage key missing.
- [x] Live SQL audit: 1,361 entries dated today through +60 days; sector coverage 96.03%.
- [x] Micron scored by a real queue cycle; mocked queue-cycle regression added. GitHub scheduled worker credentials still unverified.
- [x] Hand-calculated implied move tests and event-variance unit test.
- [ ] >=20,000 historical report events; Alpha Vantage credential absent; Finnhub 2019 probe returned zero entries. Point-in-time rejection tests pass.
- [ ] Magnitude model beats baselines out of sample; no trained model or probability claimed.
- [x] Every generated side differs and includes real measured numbers or explicit observed sample counts.
- [ ] Every liquid prop has a complete concrete structure; indicative paired-straddle estimate exists, other structures incomplete.
- [ ] Full MORE → concrete event straddle → lineup Playwright acceptance. Micron has no event-matched estimate, so its general option range is labeled accordingly.

## User-visible improvements

- Durable scoring queue, bounded atomic claims, three-attempt lease recovery and request deduplication.
- Actual IEX observed-trade refresh while a company page is open; shared 15-second provider lease. Browser refresh 30 seconds; quote timestamp always visible.
- Real Alpaca headlines and bounded Stocktwits community sample stored with publication/retrieval times.
- Observed compression screen; no fake Move Meter, probability or historical success rate.
- Historical earnings adapter and empirical event-move helpers added, but historical data prerequisites are not met.
- Calendar-driven price batch imported 324,637 bars covering 1,146 symbols. No-price symbols remain explicitly unavailable rather than fabricated.

## Automation limitation

GitHub Actions run metadata is readable, but configuring Actions secrets returns HTTP 403 `Resource not accessible by integration`. A five-minute queue workflow is committed; its runtime credentials and successful execution must be verified separately. A manual queue cycle does not prove continuous collection.

## Move Engine release verification

- 324,637 completed-session bars / 1,146 covered symbols; 8,226 lines / 1,371 attempted symbols. 225 have no bars in this feed, and show missing-data reasons.
- Browser tests pass for existing board flow, Micron's distinct BULL/BEAR and MORE/LESS panels, actual market-price relay and cross-origin rejection. This does not satisfy the event-specific concrete-straddle acceptance: MU has no event-matched estimate.
- Magnitude challenger code added: annual outer test, previous-year Platt calibration, earlier training, median/80th-percentile regression. Fixture validation only; no real model promotion.
- Original Python tests (118), engine tests (34), frontend tests (5), production build/type/lint/format and connected-database Chromium tests (3) pass locally.
- Alpha Vantage free key requirement saved in Environment draft; no value supplied. Draft save does not publish/apply it.
- Quote polling requests one latest IEX trade every 30 seconds while the stock page is open. Heavy statistics are computed by engine jobs; this is not full-market streaming coverage.

Remaining: historical dataset/backfill credential, true fundamentals/estimate revisions/short-interest features, validated prediction/EV pipeline, complete multi-leg structures and automatic publish/grade/paper portfolio, alert opt-in/dispatch, and successful scheduled worker verification. No paid service activated, no trades placed, no unsupported probability shown.

## Deployment and scheduled-worker check

Pushed code to main at `7faf26b`. Vercel reports READY for the protected Move Engine preview:
https://earnings-radar-bxh2rkh87-mace16.vercel.app/stock/MU

GitHub CI succeeded for this commit. The engine doctor was dispatched successfully (HTTP 204), and its logs establish that GitHub Actions currently lacks working Supabase and provider credentials. SEC alone succeeded there. A successful doctor workflow exit is not evidence all providers passed.

The integration can read run metadata and dispatch workflows but cannot manage Actions secrets (HTTP 403, Resource not accessible by integration). For unattended queue collection, set repository Actions secrets through GitHub Settings → Secrets and variables → Actions:
SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY, ALPACA_API_KEY, ALPACA_API_SECRET, FINNHUB_API_KEY (reuse the working FINN_HUB value). Optional ALPHAVANTAGE_API_KEY enables historical backfill. No values belong in chat or source code.

Verified credentials in the cloud or Vercel do not automatically become GitHub Actions secrets. Until this is fixed, the web price refresh works independently, but new-symbol queue requests cannot be promised a five-minute production completion.

## Production deployment repair — October 7

Changed the actual Vercel project from `web` / Python / `public` to `apps/web` / Next.js / `.next`. Committed matching `apps/web/vercel.json` so future GitHub deployments use the correct framework and output directory. The previous Next.js failure was `NEXT_OUTPUT_DIR_MISSING`, caused by inheriting the old `public` output setting.

Production deployment `dpl_2xhvU4B59VbGkR1qrWGhnHWUdzg8` reached READY and owns `earnings-radar-two.vercel.app`. Live requests to `/`, `/stock/MU`, and `/moves` returned HTTP 200 with Next.js assets. Local production build passed with the cloud proxy enabled.

The separate GitHub research workflow failure was inspected: run `37685933535` fails with `Supabase server configuration missing`. GitHub secret-management permission was retested and remains HTTP 403. Changing Vercel settings does not resolve this scheduled-worker credential prerequisite; no unattended coverage claim is made.

## Worker connection audit and repair

The worker already transports JSON through Supabase REST. Its configuration check previously conflated missing URL, invalid URL, and missing key, and the doctor returned success even when required connections failed. Added safe, specific configuration diagnostics, whitespace normalization, newer `SUPABASE_SECRET_KEY` support, wrong-key-type rejection, and nonzero doctor exit for required failures. The workflow now accepts a URL secret or repository variable and otherwise uses this project's known public API URL; server keys remain secrets only.

After pushing `26e3adc`, actual GitHub doctor run `37722588796` passed Supabase, SEC, Alpaca prices/options, and Finnhub. Optional Alpha Vantage remains unavailable. This supersedes the earlier connection blocker: the URL wiring fix allowed the configured server credential to work. A dispatched queue run `37722649865` processed pending AAPL and MU requests; both database rows are completed with no error, at 03:25–03:26 UTC October 8 (11:25–11:26 PM Eastern October 7). This proves a real queued collection cycle, not complete market coverage or model validation. Engine tests now total 41 passing, including missing/invalid configuration and doctor exit semantics.

## Concrete paper option research and automatic grading

Added exact 14–60-day long-call/put selection using absolute delta 0.35–0.65, positive uncrossed bid/ask, spread <=25%, and a recorded quote time. Prefers 30 days and delta 0.5. Indicative ask is a paper cost reference, not an executable offer or fill; 100-share deliverables remain explicitly assumed. Last-session quotes remain last-session research, never live entry. No quantity advice or calibrated probability is generated.

Momentum/50-session-average agreement with >=60 observations and measured IEX dollar volume controls a transparent unvalidated research rule. Published records copy the contract, evidence, countercase, cost, timestamps, horizon, and rule version into immutable picks. Context collection rotates through the least-recently-collected eligible symbols; a failed symbol no longer aborts the whole batch.

GitHub context run `37723658803` collected ten symbols and published five qualifying paper cases (A, ADI, AEO, AGX, AMAT), including both directions. Production `/picks` displays their concrete contracts and economics; `/track-record` displays pending evaluation. Expiration grading uses the exact expiration-session IEX close, reports hypothetical intrinsic payoff separately from underlying direction, preserves wins/losses/flat, and does not claim actual settlement or execution P&L. No picks have reached that horizon yet. Daily grading is scheduled at 5:45 PM Eastern with late-start catch-up; optional-provider partial success does not force endless rescheduling.

User refreshed Alpaca credentials in Vercel. Production deployment `dpl_EMkmErDaAwqP2AmUYAjTBwrXjWPW` reached READY; live price relay returned HTTP 200 with a real IEX trade and original timestamp. Closed-session quotes are context, not live entry. This cloud instance's old Alpaca pair remains rejected; GitHub and Vercel's updated pairs work.

## Full-directory collection and coverage accounting

Added `market_coverage` with source/feed, observation timestamps, compact auditable completed-session bars, explicit unavailable/failed states, 24-hour retry/refresh, and per-claim UUID leases. Concurrent workers cannot finish another worker's claim. Every active SEC identifier enters the scan; directory membership is not verified common-share eligibility. This is daily IEX research coverage, not consolidated real-time whole-market coverage.

The five-minute worker processes a bounded rotating batch. A separate manual bootstrap uses eight leased workers with at most two in parallel. Latest-feature SQL view avoids the prior 1,000-row subset bias in the volatility screen, and the Move screen displays actual coverage totals. Stored latest research packs are not a point-in-time historical model training dataset.

Local engine tests: 61 passed; frontend unit tests: 5 passed; production build/type/lint/format passed. Three connected-database browser flows passed locally. Direct public-site browser tests were blocked by cloud proxy certificate trust; verified HTTPS deployed-page/price requests succeeded. Connected browser acceptance (including price/origin checks) is now part of main-branch GitHub CI using configured runtime secrets; its result must be checked separately. No TLS verification was disabled.


## Phase 6: Replace Alpaca dependencies with accessible research feeds

Default master-engine collection now uses Nasdaq public daily history, Cboe delayed option snapshots, Finnhub quotes/company news, and SEC company facts. Alpaca credentials are no longer required in the master workflows or Next.js quote relay. Historical Alpaca observations and older published picks retain their original provenance and grading eligibility.

Verified in the connected cloud environment: 68 engine tests, four browser acceptance tests, and production build. Actual collection stored 867 daily bars across MU/AAPL/AMZN; research and SEC fundamentals completed for those three names. One leased market batch covered 56 identifiers and marked 44 unavailable. This does not establish complete market coverage. Independent scheduled jobs continue after another job fails and report the overall failure honestly.

Added plain-language quarterly revenue growth, matched-period profit margin, cash and current-ratio context with readable filing links. Nasdaq adjustment basis is unspecified; Cboe timestamps identify the delayed snapshot, not individual quote age. Neither source makes historical point-in-time model training or executable option pricing complete. Paper momentum research remains unvalidated, with no probability claims. Market-wide bootstrap, remote CI and production verification must be recorded after their actual results.

Research collection now rotates across all scanned liquid identifiers, not just the earnings calendar. Independent chain-collection timestamps prevent a price-only refresh from authorizing publication of stale option research; regression coverage rejects future timestamps too.


### Remote release verification and follow-up

Commit 52da952 deployed READY. Production stock/picks/track-record/moves pages returned HTTP 200; quote relay returned a sourced Finnhub observation and rejected a foreign origin with HTTP 403. GitHub doctor confirmed Supabase, SEC, Cboe and Finnhub; Nasdaq timed out from GitHub despite working in this cloud environment. Bootstrap was cancelled to avoid wasting request/runtime budgets. Remote CI passed three browser flows but exposed static generation of the picks page without build-time database credentials. These database-backed pages now render at request time, with cached data reads retained. Scan request submission is bounded to two in-flight requests so an outage cannot queue 100 requests before surfacing a failure.

Actual AMD/NVDA context collection completed with 578 Nasdaq bars, 12 scored lines, and no provider errors. Newly researched symbols now collect stored source bars before scoring. A public connection probe checks standard Yahoo chart and Stooq CSV endpoints from GitHub; it does not bypass access challenges or disguise the client.


## Phase 7: Dated business evidence in automatic research

Bounded company research now collects comparable SEC fundamentals alongside quote/news/options context and stored daily bars. Bull/Bear explanations use matched-quarter revenue growth and net margin, with filing/period dates and opposing evidence. These are descriptive business facts, not probability contributions or a solvency verdict. Published paper records copy the financial snapshot to preserve the explanation when current company context changes. Existing published records stay immutable.

A Nasdaq history outage no longer discards successfully collected company research: the job records a partial result and scores available stored history, with original source dates. Symbol-specific Nasdaq 400/404 unavailability is distinct from a provider-wide failure.

69 engine tests passed. Actual AMD/NVDA context completed with two SEC summaries, 578 Nasdaq bars, 12 lines, and no provider errors. GitHub CI for 4f376a5 passed, including all four connected browser flows. Public source probes from GitHub: Yahoo HTTP 429, Stooq HTTP 404; Finnhub historical candles returned HTTP 403 in this cloud environment. Do not bypass these limits. Nasdaq remains usable in this cloud instance; durable GitHub history collection is still blocked. Coverage collection continues here while the session runs. No background-chat availability or complete streaming coverage is promised.


## Phase 8: Exchange identity and bounded failure handling

Added sourced Nasdaq Trader exchange-directory metadata without removing searchable SEC identifiers. Actual matching classified 7,133 identifiers and conservatively recognized 5,262 common-stock names; ETFs, warrants, preferred securities, depositary securities, test issues and ambiguous names remain distinct. This name-based classification is not prospectus or option-deliverable verification.

Paper strategy v3 requires a common-stock classification collected within seven days. Older v1/v2 picks keep their original records and grading support. Default deep research rotates among liquid common-stock candidates; other companies remain searchable. The stock page explains classification in plain language instead of showing raw internal asset labels. Migration 013 applied to the connected database.

74 engine tests passed; local production build/lint and four browser tests passed. Actual AAPL/MU v3 paper research was published with copied filing context and classification provenance. Nasdaq per-symbol transport/format failures preserve healthy names in the same batch. Adjacent transport failures halt queued requests; a completely failed batch stops bootstrap, and scheduled market scanning backs off for one hour. Provider-wide 429/403 is still raised, without access bypass. Empty history no longer passes as successful price collection. Remote verification for 90bf8e4: GitHub CI success and Vercel READY.


## Phase 9: Automatic discovery board and real history freshness

The default home board now shows current published automatic paper research, with separate weekly-earnings and quiet-setup views. Company search stays available across the directory. Bounded discovery combines quiet-price research, observed 20-session trend research and fair review of older eligible names. It requires recent observed history, source-observed liquidity, and recent exchange-name classification. Rankings are never represented as calibrated probabilities. Price-only refreshes cannot postpone independent deep research by renewing its collection timestamp.

Paper strategy v4 requires the actual last observed daily close within four calendar days; recalculating stale features cannot renew price eligibility. Old strategy versions remain gradable. Migration 014 adds history-observation provenance to existing features using only stored source observations available at each feature's original cutoff, without inventing retrieval times or using future observations. Split/dividend adjustment uncertainty is explicitly included in the countercase. News/community collection failures now produce a partial job result rather than an unqualified completed status.

Verification: 77 engine tests; frontend production build, lint, format and five connected browser acceptance flows passed locally. Actual automatic research completed for a ten-name discovery batch with ten SEC summaries, 2,884 daily bars and 60 research lines; one news/community provider failed and its result remains recorded. The corrected transport/parser handling recovered the failed scan batches. Final connected-database coverage: all 10,434 identifiers attempted, 6,908 covered, 3,526 feed-unavailable, zero failed or waiting. This is completed-session history coverage, not streaming quotes for the whole market. Database size was about 252 MB before the final recovered batch, below the free database storage limit at that check.

Persistent GitHub access to Nasdaq history still requires remote verification; earlier requests timed out there while this cloud environment worked. Reliable licensed historical access, point-in-time earnings/contract datasets and calibrated out-of-sample models remain unfinished. Neither delayed option snapshots nor paper grading imply executable fills, verified deliverables or validated predictions. Deployment/remote CI for this release must be checked independently after push.


## Phase 10: Cache-backed research recovery and Eastern time

Automatic context and company-requested research can reuse original collected coverage observations when a new Nasdaq download fails. Source, observation time and original acquisition time remain unchanged; cached data is not relabeled live. Queue research also collects SEC financial summaries. Whole-share cached volumes represented as integral decimals are serialized as exact integers; fractional, negative and nonfinite values are rejected instead of rounded.

Actual recovery restored 4,897 observations for 59 covered companies whose newer feature rows had empty history. Regeneration produced 354 lines, with zero companies missing stored price history and zero remaining covered empty feature rows. Source download failures remain recorded rather than hidden. Display timestamps and market dates now use Eastern time consistently across server and browser views.

Verification: 85 engine tests pass, including future-data rejection and exact volume normalization. Six frontend unit tests, lint/format, production build and five connected browser flows passed locally before the final Python normalization fix. Phase 9 remote CI passed and its Vercel deployment was READY. Phase 10 deployment and remote CI require independent post-push verification. Reliable new daily history downloads from GitHub and calibrated predictive models remain unresolved.


### Phase 10 follow-up: Directory refresh repair

The scheduled universe refresh failed with PostgREST PGRST102 (all object keys must match). Existing listing/sector enrichment made row shapes differ. Refresh now groups equal-shaped rows into bounded upserts, preserving optional enrichment rather than inserting nulls. A regression test exercises enriched and newly discovered companies together. Actual connected refresh completed with 10,435 identifiers; this new directory count does not imply the newly added identifier has already been scanned. All 86 engine tests pass. Phase 10 dd79b43 Vercel deployment is READY.


## Phase 11: Isolating history collection network failures

A fresh GitHub public-feed probe still returned Yahoo HTTP 429 and Stooq HTTP 404. Added a bounded, worker-authenticated Vercel retrieval endpoint to test standard Nasdaq HTTPS collection from the deployed server. It fetches one named symbol from a fixed source host and bounded date range, preserves actual retrieval time, never sends the database credential upstream, and performs no scoring. HMAC authentication binds the exact body to a two-minute timestamp window using the existing shared server credential. No access challenges or rate limits are bypassed. This route is an experiment until a production source request succeeds; existing worker transport remains unchanged.

### Phase 11: Credentialed market-wide history and prospective validation

The normal authenticated Vercel Nasdaq request also timed out (HTTP 503 from the bounded relay); the temporary diagnostic endpoint is removed. The current Finnhub account also returned HTTP 403 for split reference access. Neither changing JSON format nor renewing cached timestamps solves these source entitlements/network limits.

Added a Massive/Polygon adapter behind the price-provider factory. It archives one split-adjusted grouped daily response for the entire market per session, preserving actual acquisition timestamps, and serves bounded selected-symbol ranges through a service-only Supabase RPC. Scheduled acquisition respects the basic rate limit, skips today's UTC session for end-of-day account access, collects at most three sessions per run, and prioritizes fresh sessions before backfill. Corporate-action failures do not discard usable daily history. Short archive histories retry sooner, and deep research retains a longer existing history until a replacement has 60 sessions. No paid services or bypass are enabled. **Actual provider operation remains blocked pending MASSIVE_API_KEY and its account entitlement verification.** A secure cloud-environment key requirement was saved in the draft; saving is not credential entry or publication.

Installed migrations 015 and 016. Prospective evaluation snapshots are immutable, collected only after the exchange close from verified adjusted same-feed history and split-free windows. Five future exchange sessions are counted with the NYSE calendar including holidays and half days. Outcomes preserve source dates; training, calibration and untouched test periods purge overlapping outcomes and respect label availability. Reports include reliability buckets, Brier error, a training-base-rate benchmark and decision-date block-bootstrap uncertainty. Reports cannot self-approve. With no real completed forward cases, the actual connected report records zero snapshots/outcomes/test cases rather than fabricated validation.

Added a public Forecast testing page with actual progress counters. Local verification: 99 engine tests, six frontend unit tests, lint/format/build and six connected browser flows pass. Supabase database size was 293 MB at the check; anonymous roles have neither raw validation-table reads nor the archive RPC privilege. Source access and Vercel/remote CI require independent verification after push. Meaningful approved probabilities still require real future outcomes and independent review; stock-move testing does not validate contract profitability.

Connected archive RPC filtering was verified with explicit fixture data in a transaction that was rolled back; no fixture records remain in production.


Remote verification: Vercel 5437313 is READY and its web CI passed all six browser flows. GitHub history_sync confirmed the key is missing. Remote engine CI and validate exposed an exchange-calendar compatibility failure with a fresh pandas 3 installation (dates treated as non-sessions); the local passing environment used pandas 2.3.3. Pin pandas 2.3.3 alongside exchange-calendars 4.11.2 to make session semantics reproducible. The existing half-day and exact-five-session tests caught this failure and remain enforced.
