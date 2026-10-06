# Personal single-host operation

This is a local research tool, not a deployed production service. Keep the UI on
loopback. Add authentication and a reviewed TLS reverse proxy before any future remote
access. A sleeping laptop cannot monitor continuously. No hosting is provisioned here.

## Install and migrate

From `/workspace/Earnings-Radar` (or your checkout directory):

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m pip check
python -m earnings_radar.database migrate --db data/earnings_radar.db
python -m earnings_radar.database migrate --db data/research.db
pytest -q
```

Python 3.12 is tested. Requirements pin the tested dependency set. Tracked source and
lock state are on `feature/autonomous-earnings-research`; no merge is performed.
Each schema upgrade takes a short write lock and a consistent SQLite online backup.
Versions apply transactionally. A failed migration rolls back; fix the diagnosed cause
before retrying. Never edit schema_version to pretend a failed upgrade succeeded.
Older binaries refuse a newer schema. Legacy notes, quotes, trades and schedule rows
are retained; missing fiscal periods or contract identities are not invented.

Copy `.env.example` to `.env` only if `.env` does not already exist. Set the real SEC
User-Agent contact, and optional API credentials, locally or in secure environment
settings. Never commit `.env`. Public RSS requires no credentials. Live news/model/
notifications are optional and stay unverified until authorized requests succeed.

## Start independent processes

Terminal 1, with the venv active:

```bash
python -m earnings_radar.worker
```

Terminal 2:

```bash
streamlit run app.py --server.headless=true --server.address=127.0.0.1 --browser.gatherUsageStats=false
```

A bounded refresh is `python -m earnings_radar.worker --once`. Repeated refreshes
respect persisted due times; they do not force unlimited polling. Collection is every
5 minutes, not instantaneous. Initial records and records older than two hours are
backfill and cannot notify. Worker jobs use 120-second leases; an interrupted job can
resume after expiry. A failed source retries with exponential backoff and pauses for
an hour after five failures. Check Connections for specific failure reasons.

Readiness: `curl --fail --silent http://127.0.0.1:8501/_stcore/health` must return `ok`.
Also check Connections for advancing last-success timestamps and stored evidence;
an open port alone does not prove collection. SIGTERM/SIGINT stops the worker cleanly.
The dashboard never calls collectors. Closing the browser does not stop the worker.
Use the existing isolated checkout in cloud tasks; do not create a worktree unless asked.

## Storage, retention and backups

- `data/earnings_radar.db`: existing imports, notes, paper journal and manual evaluations.
- `data/research.db`: evidence revisions, source registry, jobs, analyses, alerts and outbox.
- `data/demo.db`: samples only. Loading samples never erases the real databases.
- `data/backups/`: consistent pre-migration and operator backups; keep off-host copies.

Keep these files on a local durable disk; do not share SQLite over a network filesystem.
WAL and a 15-second busy timeout support short concurrent UI/worker transactions.
Metadata is retained; article bodies are not scraped/stored. Evidence and evaluation
references are immutable. Review your provider contract before changing retention or
redistributing content. Do not automatically delete evidence still referenced by trades.
At this personal scale, retain evidence until an operator archives a consistent DB;
there is no unbounded full-text crawl. A scheduled backup is recommended daily.

```bash
python -m earnings_radar.database backup --db data/research.db
python -m earnings_radar.database backup --db data/earnings_radar.db
```

Stop both worker and Streamlit before restore. The CLI verifies the source, backs up
an existing target, stages the restore, removes stale WAL sidecars and swaps the file.

```bash
python -m earnings_radar.database restore --db data/research.db --source data/backups/REPLACE_WITH_BACKUP.bak --services-stopped
python -m earnings_radar.database migrate --db data/research.db
```

If migration failed, use the named pre-upgrade backup and the compatible code version.
For multi-host operation, migrate leases, evidence and outbox to Postgres and add a
shared provider rate limiter; do not merely mount SQLite on a shared filesystem.

## Optional model and phone notifications

Set model credential securely and explicitly enable model work. Missing/failing models
fall back to factual analysis. Budget is a pessimistic reservation, not actual invoice
spend. Check current pricing, model availability and the per-call ceiling before use.

Telegram is phone-capable but disabled by default. Create your own bot using Telegram's
BotFather, privately configure its token and chat ID, and verify the destination belongs
to you before setting `RADAR_TELEGRAM_DESTINATION_VERIFIED=true` and
`RADAR_TELEGRAM_ENABLED=true`. No test message is sent automatically. Only then can
fresh high-severity events queue delivery. Quiet hours are America/New_York 22–08 by
default; urgent exceptions require explicit opt-in. Revisions update one inbox alert.
Backfill/replay/fixture evidence cannot notify. Attempts are leased and stop after five
failures. Inspect the outbox; do not blindly replay failed messages.

Telegram has no sendMessage idempotency key. A timeout/crash after acceptance can
produce duplicate delivery on retry; the inbox itself remains deduplicated. Never
include secret values in notification content or notes.

## Long-running deployment templates

`deploy/*.service` are user-systemd templates, not installed services. For a future
single-host deployment, adapt `%h/Earnings-Radar`, put protected config at
`%h/.config/earnings-radar.env` (mode 600), and copy the units to your user service
configuration. Review durable data paths before enabling. Units restart failed processes
and keep the UI local. Ensure the host stays awake and user services persist across
logout; that is an operator deployment decision, not verified here.

## Evaluations and replay

Only standard long calls, long puts and same-expiration straddles are supported.
Live eligibility needs known announcement time, confirmed schedule, valid future
expiration, explicit contract IDs and synchronized leg/underlying timestamps within
5 seconds, each no older than 60 seconds. Historical/indicative/sample data cannot
produce a live candidate. No entitled options collector has been verified yet.
Simulated fills use ask plus slippage and fees. Sizes/fills are not guaranteed.
Expiration payoff scenarios are not intraday prices or predictions. Capital/risk limits
apply only if supplied by the user; no account balance is assumed.
Replay consumes only evidence/revisions known at the supplied as-of time and cannot
send notifications. It is an engineering test, not evidence of profitability. Historical
licensed quote data, point-in-time universe coverage and execution latency are not
available; survivor bias and missing cost/performance data remain explicit limitations.
