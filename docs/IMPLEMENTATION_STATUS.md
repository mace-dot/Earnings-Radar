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

## Stage 5 and current handoff

Added standard long-call/put/straddle evaluations with leg identities, multipliers, fees,
ask-plus-slippage assumptions, maximum loss and expiration breakevens/payoffs. Quotes
must pass synchronization, freshness, announcement timing and OCC identity validation.
Nonstandard/adjusted contracts are excluded. An evaluation records immutable evidence,
analysis/alert revision and quote snapshots where available; an eligible current package
can be logged to paper legs. Manual paper trades remain supported. Imported CSV quotes
are historical; no fabricated live option candidate appears. Intraday volatility/time
valuation and a licensed options collector remain unimplemented prerequisites.

Added point-in-time evidence replay without notification side effects, database backup/
restore CLI, dark sports-picks-style UI theme, earnings result/calendar tabs and local
single-host restart templates. No deployment has occurred. The UI keeps reported data,
research hypotheses, missing inputs and simulated evaluation outcomes distinct.

The SEC XBRL collector additionally works live for AAPL, MSFT and NVDA. It retains
recent reported USD revenue/net income/gross profit where available, source accessions,
periods and filing-date precision. Comparable historical year-over-year math is separate
from future guidance and consensus. Schedule source precedence and conflicting source
records are explicit. Restore and migration rollback have regression coverage.

### Actual verification

- Baseline: 11 tests passed before changes. Final expanded suite and exact final count
  are recorded below after the final run.
- Real public collection: SEC submissions, SEC XBRL company-concept data, Fed press and
  Fed speech RSS all succeeded. An initial transient Fed press 404 was investigated;
  a successful direct check and retry restored healthy status.
- Current instance: 87 immutable evidence revisions, 87 analyses and 78 deduplicated
  inbox alerts from real public metadata. Initial/historical records are backfill;
  they did not send notifications.
- Real end-to-end: public SEC financial evidence → stored factual analysis → rendered
  weekly-board alert → recorded evidence-linked evaluation. Evaluation correctly said
  WAIT because no verified upcoming schedule or executable option quotes existed.
- Worker running independently of Streamlit; server health endpoint returned `ok`.
  AppTest exercised all views and persistent review/evaluation actions.
- Live Alpaca news/IEX, model and Telegram not tested: credentials absent. Fixture tests
  prove interface behavior, not production readiness. No notification was sent.

### Remaining limitations and precise next steps

1. Configure entitled news/market API keys securely, verify live authorized responses,
   and document the contract's delay/retention rights. Bloomberg, WSJ, Seeking Alpha,
   EarningsHub, Yahoo and Google currently have source-registry requirements only.
   The user identified earningshub.com; its API/access terms are not verified.
2. Add a verified upcoming-earnings calendar and entitled synchronized standard-options
   data collector before enabling live option comparisons. IEX stock data alone is not
   consolidated option execution data.
3. Full-document/transcript extraction, consensus expectations, documented supplier/
   customer coverage and populated independent systemic indicators remain incomplete.
   Their interfaces are present, with unavailable data explicitly unknown. No stock
   outperformance, unpriced-information thesis or crash probability is claimed.
4. Add model credentials only if desired, choose a currently available model and review
   pricing against the bounded reservation budget. Then verify outputs live; the
   deterministic factual path already works.
5. If phone alerts are desired, explicitly configure and verify a destination, then opt
   in. Delivery uncertainty remains possible under Telegram timeouts.
6. Review deployment templates, authentication and persistent host/storage before an
   always-on deployment. A running task process is not autonomous production readiness.

Run commands: see docs/RUNBOOK.md. Dependencies pinned; tracked secrets absent.
Five stage commits plus a focused primary-document follow-up deliver the foundations; main has not been merged.

Final validation: 63 tests passed; pip check reported no broken requirements; git diff --check passed.


### Primary-document follow-up

Added bounded SEC filing HTML retrieval and exact excerpts with source body/text hashes,
normalized text character offsets and evidence validation. Script/style text is excluded;
retrieved instructions remain untrusted data. Document evidence links to its parent
story, so additional primary context does not create duplicate inbox alerts. Relevant
filing excerpts appear in the alert detail. This is not full licensed transcript analysis
or independent verification of management assertions. SEC documents are capped at 20 MB;
ordinary API responses remain capped at 5 MB. One larger filing triggered the original
5 MB cap; the documented SEC-only limit was raised and the affected job retried.

Final suite after document follow-up: 65 tests passed. GitHub feature branch push
succeeded; draft PR creation returned Forbidden from the GitHub GraphQL API. No PR
was created or merged. Manual review URL is provided in the final handoff.


macOS follow-up: replaced the full cloud dependency freeze with stable direct pins
(Streamlit 1.50, Altair 5.5, pandas 2.3.3, numpy 2.2.6 and compatible calendar 4.11.2),
and documented Python 3.12/pip upgrade recovery. Fresh installation and suite validation
are recorded in the follow-up handoff; native macOS execution is not available here.


## Render hosting preparation

User selected Render to preserve the current app. Added root render.yaml Blueprint,
Python 3.12 Docker image, combined UI/worker supervision, persistent database/export
paths, build exclusions for private data, and a fail-closed hosted password gate.
Render generates the dashboard password and prompts for the real SEC User-Agent.
A single Starter instance plus a 1 GB disk is specified; user must review cost before
creating paid resources. No resources purchased and no Render service created.

Validation: 68 tests passed in a fresh Python environment and in the built image;
container UI health, worker heartbeat, mounted data paths and shutdown were checked.
The cloud proxy required ephemeral build-only DNS/trust configuration; TLS checks
stayed enabled. Render has not been tested live because no account/token binding is
available. Connect GitHub and select feature/autonomous-earnings-research in Render's
New Blueprint flow. See docs/HOSTING.md for the exact steps. Supabase is optional
future shared storage/auth, not necessary for the first single-host review URL.
