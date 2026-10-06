# Implementation status

Baseline: main at 920df3707c42ff4f2970d2f650412ba8c011f711; 11 tests passed before changes.
Branch: feature/autonomous-earnings-research. No deployment or brokerage execution.

## Stage 1

Implemented numbered transactional migrations with online backups, strict shared validators,
isolated demo storage, shared event-aware quote selection, XNYS calendar cutoffs, UTC
normalization, source/feed classification, preserved schedule revisions, and paper legs.
Legacy trades retain their original records; missing contract identities are not invented.
CSV events without stable IDs or fiscal periods only reconcile same-date revisions; cross-date
matching remains unknown. Provider conflicts are retained rather than silently merged.
Only long calls, puts and straddles can be entered as new trades.

Validation: 29 tests passed (11 baseline plus integrity regressions). Calendar library 4.13.2
is required for pandas 3 compatibility. Dependencies pinned to the tested installation.

## Stage 2

Implemented a separate research SQLite database and explicit source registry, official
Fed RSS collectors, SEC submissions collector requiring real request identification,
Alpaca news metadata and IEX stock quote adapters, durable jobs/checkpoints, atomic
leases, expiry recovery, bounded retries, backoff, worker heartbeat and degraded status.
Writes are idempotent; revisions and hashes preserved. Initial/history ingestion is
flagged backfill. No paywall scraping or undocumented Yahoo/Google/Truth API workaround.
Worker is independent of Streamlit. 36 tests passed. Public requests succeeded;
SEC collection awaits request identification, and licensed adapters await credentials.

## Stage 3

Implemented typed analyses, exact stored-evidence reference validation, factual notices,
political status classification, documented/dated relationship queries and conservative
systemic dimensions. Deterministic notices work without a model. An optional bounded
Anthropic Messages adapter has a daily reservation budget, timeout, schema validation,
and factual fallback on failure. Official Anthropic SDK README was inspected on GitHub;
live model access remains unverified. Metadata alone does not establish guidance changes,
consensus, financial mechanisms, market reaction or a trading advantage.

43 tests passed, including unsupported facts/tickers, model failures, budget exhaustion,
corrections, retries and replay isolation. Analysis inbox/outbox foundations accompany
this stage so deterministic output is immediately usable by the worker.

## Stage 4

Implemented persistent in-app inbox, revision updates, reviewed state and an optional
Telegram delivery outbox with severity filtering, leased attempts, quiet hours,
cooldowns, bounded retries and backfill/replay suppression. Telegram stays disabled
unless credentials, opt-in and a verified destination are configured. No message sent.
Delivery is at-least-once under ambiguous network failure: Telegram does not provide
an idempotency key for sendMessage. A crash after acceptance may cause a duplicate.

Added the requested sports-picks-style weekly research board: readable event cards,
clear action badges, evidence strength and quote limitations. No betting odds or win
probabilities are fabricated. Source coverage includes named outlets as requirements,
not claimed working integrations. Direct Truth Social remains unverified.
