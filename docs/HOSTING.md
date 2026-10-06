# Hosted access from GitHub

The existing Streamlit UI needs a long-lived Python process/WebSocket session. Its
collector needs a continuously running worker and its SQLite database needs a local
persistent disk. Vercel Functions are not a direct host for this architecture.
Connecting this checkout to Vercel does not turn it into a working Streamlit site.

Two supported architecture choices:

- Preserve the current app on a container host with a persistent disk, such as Render
  or Railway. A provider-managed URL removes local Python installation from viewing.
- Build a Vercel-compatible web frontend and use a separate API/worker and durable
  database. This is a new interface/backend integration, not a deployment toggle.

## Shared hosting preparation

`Dockerfile` uses Python 3.12 and tested portable dependencies. The entrypoint starts
Streamlit and the collector together, stops both on shutdown, and fails the service if
either component exits so the host can restart it. Run one instance with one local
persistent disk; do not horizontally scale this SQLite deployment.

Mount a durable disk at `/var/lib/earnings-radar`. Database files, pre-migration backups
and exports use this disk. The container build excludes local databases, keys and .env
files. Local demo data is separate and ephemeral unless explicitly configured otherwise.

Supply `RADAR_DASHBOARD_PASSWORD` securely in host settings; never commit its value.
The hosted entrypoint enforces password protection and fails closed if it is missing.
Use only the host's HTTPS URL. The session password gate is initial personal access
protection; a broader multi-user service needs proper identity/access management.
Supply `SEC_USER_AGENT` with the already approved real contact. Optional news/model/
notification credentials remain separate and disabled until configured/verified.

The provider should expose its assigned `PORT` and restart on failure. Health endpoint:
`/_stcore/health`. A healthy HTTP endpoint does not prove source coverage; also check
Connections and its worker heartbeat/source successes.

No hosting account is connected and no deployment has occurred. The image built successfully and its complete suite passed (68 tests). The cloud build used an ephemeral trust-certificate mount for this environment’s egress proxy, with TLS verification preserved; that certificate is not included in the deployed image. Python startup, dependencies,
UI tests and password-gate behavior can be validated independently. Any paid persistent
host/disk needs the user's provider-account and budget decision before provisioning.


## Connect the existing app to Render

The root `render.yaml` Blueprint specifies the feature branch, Python container, one
Starter web service, a 1 GB persistent disk, automatic deployment on branch updates,
and a generated private-dashboard password. A paid service/disk is required for this
persistent architecture. Review Render's displayed prices before creating it; no paid
resources have been provisioned by Codex.

1. Sign in at https://dashboard.render.com and connect your GitHub account.
2. Select New → Blueprint and choose `mace-dot/Earnings-Radar`.
3. Set the branch to `feature/autonomous-earnings-research` (main is still the old app).
4. Render should detect `render.yaml`. Enter your real SEC User-Agent name/contact
   in the requested `SEC_USER_AGENT` setting and review the service/disk cost.
5. Create the Blueprint. After deployment, open the service's Render-provided HTTPS
   URL. Retrieve `RADAR_DASHBOARD_PASSWORD` from that service's environment settings
   and use it to open the dashboard. Do not share or paste its value into chat.
6. Confirm Today/Connections appear, source successes advance, and the worker heartbeat
   is running. Changing the feature branch on GitHub triggers a deployment.

No Render token/account binding is available in this session, so account linking and
actual service creation remain user actions. The current cloud research DB is not in
GitHub: the hosted collector populates a new database. Existing private data must be
migrated through a separate secure backup/restore operation, not committed to GitHub.

Supabase is an optional future database/auth layer, not an app or continuous-worker
host. Adding it requires replacing the SQLite persistence/migrations/leases with
Postgres-backed storage; it is unnecessary for the first single-host review URL.


Validation: 68 tests passed both in a fresh Python environment and inside the container.
The container started the UI and collector, returned `ok` from its health endpoint,
recorded a worker heartbeat and used mounted database paths. Temporary test container
and volume were removed. Live collection was previously verified in the cloud instance;
Render deployment/its live connections remain unverified until the user creates it.
Official Render documentation requests were blocked by the cloud network policy; the
Blueprint uses standard fields and must pass Render's own review/validation on creation.
