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

## Research assistant upgrade

Apply migrations `202610060001_radar.sql` and `202610060002_research.sql` in order. The second migration adds evidence metadata, private Supabase-authenticated watchlists and a database collection lease; it preserves existing research. Configure Vercel server variables `SUPABASE_ANON_KEY`, `SEC_USER_AGENT`, and a strong random `CRON_SECRET` alongside the existing database connection. Never expose the service key or cron secret to the browser.

The deployed free-tier schedule is **daily at 12:00 UTC** (8 a.m. US Eastern during daylight saving time; 7 a.m. in standard time). It processes up to three companies per run and Federal Reserve feeds. The universe combines default coverage with authenticated users' saved symbols. Failed companies rotate rather than blocking the queue. Collection is globally limited to once per 15 minutes through an atomic SQL lease; expired leases are recoverable. Manual refresh requires sign-in, same-origin requests and server-validated sessions. A larger universe means longer per-company refresh intervals, shown through timestamps. Source failures never become low-risk assessments.

`CRON_SECRET` is Vercel's built-in cron Bearer authorization. An unauthenticated request to `/api/collect` must fail. The same handler can be manually tested using its secret, but that does not prove a future scheduler invocation has occurred. GitHub hourly scheduling remains an optional alternative requiring separately configured Actions secrets; do not run both unintentionally.

Supabase handles email/password account creation and email confirmation. Configure its Auth Site URL to the Vercel origin. Passwords are submitted only to a same-origin backend proxy; session and refresh tokens use Secure HttpOnly SameSite cookies and are validated against Supabase before private writes. Notes are not added or exposed. Supabase's own authentication rate limits apply. The live isolation script `scripts/verify_private_watchlists.py` creates and deletes temporary confirmed accounts without sending emails.

The public API interprets source evidence with conditional mechanisms and matched-period financial calculations. It supports today's brief, a research candidate board, company dossiers with annual revenue charts, macro context, history, and operational source health. Ranking components are shown; there is no calibrated predictive model. History retains revisions and source facts, but profit/outcome evaluation remains unavailable without suitable price histories.

Run Python tests and `npm ci --prefix web && npm run build --prefix web`. The UI smoke test covers navigation, dossier rendering, missing-data labels and malicious-source text. The standard-library Vercel collector never calls a paid model, accesses a brokerage, or bypasses licensed sources. Free-tier quotas and platform schedule reliability still apply.

## Stock pick-board interface and private ideas

Apply `202610060003_ideas.sql` after the earlier migrations. Saved ideas are private account records, with RLS and a 20-idea database cap. The backend validates each company's supporting evidence before saving an Up or Down hypothesis. This is a research lineup, not an order ticket or a recommendation. Signing out clears the displayed lineup; saved account data remains private.

The default screen uses compact company tiles and plain-language business context. Up/Down buttons explore buying individual calls/puts, as specified by the user. Big-swing filtering requires fresh historical volatility data; no data yields an explicit empty state. Funding flags retain their financial period and evidence. They do not estimate a market-wide crisis probability. Historical growth never determines a stock-price direction or establishes an executable option trade.

The Robinhood checklist explains what to check manually in the brokerage: expiration, strike, quoted premium, spread, and catalyst timing. A standard 100-share long-option calculator computes total premium, maximum premium loss, break-even at expiration, and a user-entered expiration payoff before fees. It fetches no Robinhood credentials, places no orders, and does not model the option's price before expiration. Adjusted/nonstandard contracts are outside this calculator's scope.

The UI includes a glossary, keyboard focus indicators, a skip link, selection states, mobile layouts and a mobile lineup shortcut. Methodology/source details remain available through company details and Data checks. The public API now returns `move_board` summaries; saved ideas use authenticated `/api/ideas` endpoints.


## Broad directory and autonomous research

Apply `202610070004_discovery.sql` after migrations 001–003. It preserves existing data and adds an official company directory, bounded persistent research jobs, optional model-call accounting, and immutable research snapshots. Initialize the directory using `web.api._directory.refresh_directory(Store())` from a server-only environment with `SEC_USER_AGENT` and the existing Supabase connection. The daily secured Vercel job refreshes directory membership weekly, discovers recent SEC filings independently of watchlists, and researches a bounded batch. Public name/ticker search selects a company and automatically requests fresh research; cache reuse lasts 24 hours. Queue leases recover after five minutes; retries use exponential backoff and stop after five attempts. The enqueue allowance is 40 distinct company jobs per day across the site. This is daily/on-demand evidence research, not a continuous real-time market feed.

`/api/directory`, `/api/company`, `/api/research`, `/api/assistant`, and `/api/track-record` are same-origin server endpoints. Directory search does not imply complete research, worldwide coverage, or available option contracts. Saved watchlists and ideas retain existing private authentication. No Robinhood login is needed and no orders are placed.

The default assistant explains evidence using deterministic rules. An optional Groq model adapter requires server-only `GROQ_API_KEY` plus `RADAR_AI_ENABLED=true`; it is disabled by default. Verify free-account terms and model availability before enabling. Model calls are capped at ten per UTC database day, cached by evidence identities, and source IDs/quoted passages are validated. Citations do not prove every inference or trading edge. No paid model is enabled.

Automatic contract selection remains WAIT until authorized option quotes, confirmed catalyst dates, documented expectations, and calibrated forecasting inputs are connected. Price forecasts, probabilities, outcome scoring, and trading win rates are unavailable. The audit in `AUTONOMOUS_RESEARCH_AUDIT.md` separates delivered capabilities from missing dependencies.


## Statistical and fundamental strategy upgrade

Apply `202610070005_market_research.sql` after the earlier migrations. It adds private server-only price/news caches, 12-hour per-company refresh leases, and a site-wide 40-company daily limit for each pipeline. Existing records and private watchlists are preserved.

Up/Down now requests a backend assessment automatically through `/api/strategy`: matched-period fundamental changes, opposing evidence, funding measures, and optional historical-price statistics. Both directions may have supporting and opposing evidence; WATCH means research to monitor, not a buy instruction. Specific option selection remains WAIT without an authorized chain and confirmed timing. No manual financial input or broker credentials are required.

To activate daily IEX stock history, configure **server-only Vercel production variables** `ALPACA_API_KEY` and `ALPACA_API_SECRET` from an account with the relevant entitlement. After checking the provider's public-display and redistribution terms for this website, set `RADAR_MARKET_DISPLAY_AUTHORIZED=true`. A free account does not automatically establish public-display rights. No paid upgrade is authorized. Redeploy after changing environment variables and open a company to trigger bounded collection. Do not enter keys in chat. The cloud environment draft also contains these credential names and additional source domains; draft saves do not configure Vercel or activate the runtime.

The adapter requests completed daily bars with provider split/dividend adjustments, distinguishes IEX venue volume from consolidated volume, checks timestamp/OHLC validity, caches sufficient history, and preserves old data when requests fail. The chart supports available 1M/3M/6M/1Y ranges and an accessible table. No unofficial Yahoo-price endpoint or synthetic prices are used. Price calculations include realized volatility, Parkinson range volatility, ATR, momentum, drawdown, abnormal volume and a latest-return z-score. Price sensitivity ranges use zero-drift historical volatility scaling; they are not forecast intervals or targets. Market-relative measures require actual aligned benchmark observations; they remain absent otherwise.

The daily collector attempts CNBC, BLS and BEA public RSS headlines, and company research attempts Yahoo Finance's public ticker RSS feed. It records actual success/failure and never retrieves paywalled article bodies. Feed availability can vary by host/network; an adapter's presence is not proof of working collection. Source cards link to readable filing indexes; raw financial endpoints remain preserved in backend evidence identities. Optional model explanations remain disabled without credentials.
