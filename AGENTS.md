# AGENTS.md — Earnings Radar (standing rules for Codex)

Put this file in the repo root. Codex reads it on every task. The current build spec is `docs/PREDICTIVE_BALANCE_PLAN.md`. `docs/MASTER_PLAN.md` is the earlier product handoff and yields where they conflict.

## What we are building
A PrizePicks-style earnings and volatility board for retail investors. Every US-listed stock can be searched. Liquid names get automatically generated "lines" (trade setups) around upcoming earnings, from about 60 days before the report to 20 days after. Each line has a **BULL** and a **BEAR** button. Each side explains its case in plain English and shows an auto-selected trade, a confidence score, the historical hit rate, and a link to deeper research.

## Product rules (these override older docs in /docs)
1. **Default output is a decision, not "WAIT".** The old code hard-codes `decision: 'WAIT'` / `contract_decision: 'WAIT'` and hides features behind env flags. Do not copy that pattern. Missing data lowers confidence and shows a data-quality badge (`Estimated date`, `Stale quote`, `Thin options`, `Small sample`). It only blocks the one line that depends on the missing data, never the whole page.
2. **Every number shown has a source and an as-of timestamp** stored in the database. Never invent prices, dates, or estimates. Use clearly labeled fixtures in tests.
3. **Point-in-time correctness.** Features use only data available at `as_of`. Backtests must be walk-forward. A test must fail if any feature reads data timestamped after its `as_of`.
4. **Confidence must be earned.** A probability is shown only when the model behind it has ≥ 200 out-of-sample historical cases and a recorded calibration (Brier score and reliability buckets). Otherwise show a tier (`Strong / Moderate / Lean`) plus the sample size.
5. **Defined risk only** for anything suggested to beginners: shares with a stop, long calls/puts, or debit spreads. Undefined-risk structures (naked short options) are never suggested.
6. **Grade every pick automatically**, winners and losers, and publish the record on the Track Record page.
7. **Language:** 8th-grade reading level in the UI. Say "could", not "will". Never use "guaranteed", "can't lose", or "fortune teller" in user-facing copy.

## Engineering rules
- **Readable code.** No minified one-liners, no multiple statements joined with `;` on one line. Python: type hints, `ruff` + `black`. TypeScript: `strict` mode, ESLint + Prettier.
- **Layout:**
  - `apps/web` — Next.js (App Router) + TypeScript + Tailwind + shadcn/ui. Deployed on Vercel. Reads from Supabase only; no heavy compute in request handlers.
  - `engine/` — Python 3.12 package for data ingestion, features, models, pick generation, and grading. Runs on a schedule (GitHub Actions first; a Render worker if runtimes outgrow Actions).
  - `supabase/migrations` — all schema changes as SQL migrations. Row-level security on every user table.
  - `legacy/` — move the current `web/` and `earnings_radar/` here once their useful parts are ported. Do not delete until Phase 3 passes.
- **Provider adapters:** every external data source sits behind an interface in `engine/providers/` (`EarningsCalendarProvider`, `PriceProvider`, `OptionsProvider`, `EstimatesProvider`, `NewsProvider`, `FundamentalsProvider`) so vendors can be swapped by config.
- **Secrets** live only in env vars (Vercel, GitHub Actions secrets, `.env.local`). Never commit keys. Keep `.env.example` current.
- **Keep the existing security patterns:** same-origin checks on POST, httpOnly session cookies, CSP headers, URL allow-listing for outbound links, no `innerHTML` with untrusted content.
- **Tests are part of the task.** Each phase in MASTER_PLAN lists acceptance tests. A task is done when they pass in CI (`pytest`, `vitest`, Playwright smoke test).
- **Single-run builds.** Work through all phases in one task, commit after each phase ("Phase N: <name>"), and keep `docs/PROGRESS.md` updated so work can resume if interrupted. Never stop to ask questions: log decisions in `docs/DECISIONS.md` and continue.
