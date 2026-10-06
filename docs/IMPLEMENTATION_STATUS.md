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
