# Free-tier web setup

The Vercel dashboard lives in `web/`. It reads public research from Supabase through a server-only API. GitHub Actions runs the existing SEC/Federal Reserve collector hourly. It does not run a permanent worker on Vercel. This is a public, read-only research dashboard, not the Streamlit paper journal or private notes. Existing SQLite data stays intact. No personal records are synced. Historical source records are explicitly labeled; headlines do not become verified earnings forecasts or buy recommendations.

## 1. Supabase project

Open https://supabase.com/dashboard and create `earnings-radar` in a **Free** organization. Choose a region near your users and a strong database password. Do not post the password in chat. Free-plan limits and inactivity rules still apply; do not opt into a paid plan for this setup.

Open the project's **SQL Editor**, paste `supabase/migrations/202610060001_radar.sql`, and run it. Both tables have row-level security, no anonymous/authenticated policies, and revoked public access. The API serves only fixed, public research fields. Never upload private notes to these tables. This creates a separate Postgres database; it does not migrate every old SQLite workflow.

In project settings, copy the **Project URL** and legacy **service_role** API key. The service-role key bypasses RLS; keep it only in server environment variables and GitHub Actions secrets. Never put it in browser code, GitHub files, screenshots, or chat.

## 2. Vercel project

Open https://vercel.com/new, import `mace-dot/Earnings-Radar`, and use:

- Project name: `earnings-radar` (or an available variation).
- Production branch: `main`.
- **Root Directory: `web`** (essential; the repository root is the old Python app).
- Framework preset: **Other**.
- Build command: `npm run build`.
- Output directory: `public`.
- Environment variables: `SUPABASE_URL` and `SUPABASE_SERVICE_ROLE_KEY`.

Use Hobby only if your intended use meets Vercel's current personal/noncommercial eligibility terms. Review the plan screen before creation. Do not enable paid upgrades. Deploy; Vercel supplies the actual HTTPS URL. If variables are added after deployment, redeploy to apply them. The dashboard deliberately shows an empty/unconfigured notice until the database and collector are connected. There is no fabricated sample research.

## 3. Populate research

In GitHub **Settings → Secrets and variables → Actions**, add repository secrets `SUPABASE_URL` and `SUPABASE_SERVICE_ROLE_KEY` using the same values. Then **Actions → Collect public research → Run workflow → main**. After the first successful run, add repository **variable** `RADAR_CLOUD_ENABLED` = `true` to enable the hourly schedule. Until then scheduled jobs are skipped to avoid repeated failures against an unconfigured database. Initial collection includes AAPL, MSFT, NVDA SEC filings/financial results and Federal Reserve updates. SEC identification is `EarningsRadar mace@udel.edu`, as authorized.

The workflow runs hourly on the default branch; GitHub may delay/skip scheduled runs, and schedules in inactive public repositories may be disabled. Private-repository Actions allowances differ. Watch the run result and usage limits. Every run uses temporary SQLite storage; Supabase retains stable evidence identities and content revisions, while local numeric references are remapped. Original cloud first-seen times are retained. It is a bounded backfill scan, not a streaming ingestion service. Source access failures are visible. No model calls, paid financial APIs, or Telegram delivery are enabled.

## Validation and limits

The website uses no Streamlit/pandas process. The standard-library serverless API has bounded, fixed reads and never returns the Supabase key. Browser content uses text nodes and HTTPS-only links. The SQL transaction is repeatable and does not drop tables. The collector validates evidence-grounded analysis before syncing; writes are idempotent by source identity and content hash. API errors return a useful empty-state message rather than fictional analysis.

Before calling a deployment functional, verify the SQL ran, a workflow succeeded, `/api/dashboard` returns real records, source timestamps render correctly, and Vercel has no deployment errors. Cloud account provisioning, Postgres execution, and Vercel runtime validation require actual account access and are not established by local tests.

A verified upcoming earnings calendar, real executable stock/options data, multiuser accounts, private alerts, and the full Streamlit paper-trade workflow are not ported here. Bloomberg/WSJ/Seeking Alpha and other restricted sources still require authorized access. A successful collector does not mean every requested source is connected. The public website's footer explains the market-data limitations.

## Watchlist and quantitative data

Default backend coverage is `AAPL,MSFT,NVDA`. The website displays these stocks even before database collection succeeds. Browser-added tickers are saved only to browser storage; to actually collect a new company, set GitHub Actions variable `RADAR_WATCHLIST` (comma-separated, at most 20) and `RADAR_CIK_MAP` (JSON mapping to 10-digit SEC CIKs). Unknown companies without explicit CIKs are reported as unavailable. Browser filters do not configure global collectors.

Optional Actions secrets `ALPACA_API_KEY` and `ALPACA_API_SECRET` enable authorized historical IEX daily-bar statistics. Use credentials with the required data entitlement. Do not buy a paid data subscription as part of this setup. Without them, the watchlist remains visible but quantitative values show unavailable. SEC historical fundamentals can still populate independently. The statistics and limitations are documented in [Quantitative methods](QUANTITATIVE_METHODS.md).

The Vercel API accepts a legacy `SUPABASE_SERVICE_ROLE_KEY` or new server-side `SUPABASE_SECRET_KEY`. Both stay server-only. The collector currently uses the configured `SUPABASE_SERVICE_ROLE_KEY` secret; a server secret key may be stored under that application variable name. Never use a publishable/anon key in its place or a `NEXT_PUBLIC_` variable name. New Supabase secret keys are sent as `apikey`; legacy JWT service-role keys also authenticate using a Bearer header.

## Direct connection from the Codex environment

For the existing projects `fepyjsmmgortycprrxjr` and `earnings-radar-two.vercel.app`, `scripts/connect_cloud.py` can initialize the schema, configure encrypted Vercel server variables, collect initial public evidence, and request a production redeployment. It requires `SUPABASE_ACCESS_TOKEN` and `VERCEL_TOKEN` entered securely in cloud environment settings. Supabase management access retrieves the service-role key without displaying it. If that is unavailable, also configure `SUPABASE_SERVICE_ROLE_KEY` securely. These are account credentials, not values to paste into chat. The script requires the existing Vercel GitHub linkage and Root Directory `web` and refuses an unexpected project. External API execution is unverified until these credentials and network access are supplied. Do not claim a successful script request means Vercel has completed its build; verify the resulting production API separately. Hourly collection still requires Actions configuration as above.
