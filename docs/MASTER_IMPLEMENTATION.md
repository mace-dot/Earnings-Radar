# Master implementation: running the new foundation

The new app lives in `apps/web`; the current production root stays `web` until the replacement passes Phase 3. No legacy code or existing database rows were removed.

Protected new-app preview: https://earnings-radar-7yx3juvjb-mace16.vercel.app/ (sign in with the existing Vercel account). Vercel reports READY; browser smoke against the same Supabase data passed locally.

## Development

Use Python 3.12 and Node 24:

```bash
python3.12 -m venv .venv
.venv/bin/python -m pip install -r engine/requirements.txt
npm ci --prefix apps/web
.venv/bin/python -m pytest engine/tests -q
npm test --prefix apps/web
npm run build --prefix apps/web
npm run dev --prefix apps/web
```

The Next.js server reads `SUPABASE_URL` and `SUPABASE_SERVICE_ROLE_KEY`. Both are server-only. Populate them securely in the shell or ignored `apps/web/.env.local`. The Python engine reads shell variables, not Next.js `.env.local`.

Apply `supabase/migrations/202610070008_master_foundation.sql` once. It is additive and already applied to the existing user project. Owner policies protect profiles, lineups, items and alerts. Published picks reject updates and deletes. New market tables have RLS and server-role access only while provider publication rights remain unverified.

## Actual collection

```bash
python -m engine.run universe
python -m engine.run calendar
python -m engine.run prices --symbols AAPL,MSFT,NVDA
python -m engine.run score --symbols AAPL,MSFT,NVDA
```

The default ten-symbol batch is a foundation smoke, not full-universe coverage. Directory search covers all imported SEC identifiers; membership is not proof of common-share eligibility. Sector enrichment, all-company background collection and provider fallback remain incomplete.

## Credentials

- SEC: no key, contact User-Agent already supplied.
- Alpaca: existing key + secret, daily IEX data only; not consolidated live equity quotes or executable options.
- Finnhub: free key for calendar when the account endpoint permits it. Existing environment binding currently permits hostname `finnhub`; edit that binding's allowed destination to `finnhub.io` in Environment settings. Draft update was rejected for conflict; no replacement requirement was added.
- Alpha Vantage: a free account key for calendar cross-check. Missing in this environment.
- Supabase: existing URL + server role for engine and server-rendered app. Management access token is for migrations, never the app.
- Vercel: existing management token for deployment, never browser code.
- Historical options, premium consensus revisions and OPRA rights may require payment. They are not enabled and their costs cannot be avoided by scraping paywalls.

## Scheduling

`.github/workflows/master-engine.yml` supports manual jobs and DST-aware schedules. Configure GitHub Actions secrets `SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY`, `ALPACA_API_KEY`, `ALPACA_API_SECRET`, `FINNHUB_API_KEY`, `ALPHAVANTAGE_API_KEY`. Enable repository variable `RADAR_MASTER_ENGINE_ENABLED=true` after those are available. This is a scheduler control, not a whole-page feature flag. The current cloud session cannot access GitHub's Actions-secret API (HTTP 403); Git pushes do not prove that separate permission.

Current jobs: directory, calendar, daily prices, price-feature scoring. Options refresh, fundamentals enrichment, news, historical-event backfill, automatic pick publication/grading, full-universe rotation and model training are not yet wired to scheduled production jobs.

## Validation limits

The walk-forward challenger is code tested on labeled synthetic fixtures, not a trained real historical model. It returns Brier/log loss/reliability but does not calibrate or promote itself. Rule case text is a template; business claims are conditional hypotheses, not sourced deep-research conclusions. There are no validated probabilities, live option selections, public trading performance, AI provider calls, or broker orders in this foundation.

## Move Engine update

`docs/MOVE_ENGINE_PLAN.md` is now the active technical extension. The direct `FINN_HUB` credential works; no replacement Finnhub key is needed. Alpha Vantage historical earnings and cross-check still need a free key.

New jobs:

```bash
python -m engine.run doctor
python -m engine.run calendar
python -m engine.run sectors
python -m engine.run prices
python -m engine.run score
python -m engine.run queue
python -m engine.run context --symbols MU
```

Apply additive migrations 009, 010 and 011 in order (already applied to the existing project). The worker uses calendar-driven scope. The queue is serviced by the five-minute GitHub schedule when its secrets are available. Existing API integration cannot manage those secrets (HTTP 403), even though Git and Actions run metadata work.

To switch production **after acceptance**: Vercel → earnings-radar → Settings → Build and Deployment → Root Directory `apps/web`; Framework `Next.js`; Install `npm ci`; Build `npm run build`; Output `.next` (or framework default), then redeploy `main`. Preserve server env values for Supabase and Alpaca. The existing production root was not switched by this update.
