# Implementation decisions

The attached MASTER_PLAN and root AGENTS supersede earlier product specifications.

- Keep the existing production application until the new application and Phase 3 pass. No destructive migration of legacy data.
- Free services only. Missing paid historical options data is not replaced by synthetic production data.
- A directional probability is not a profit probability. Variable option payoffs require a payoff distribution and transaction costs; no invented expected-value ranking from direction alone.
- Shares with stops have gap risk. Without an approved account budget, show per-share or one-contract exposure, never a quantity recommendation.
- Alpaca IEX is a partial equity feed and indicative options are not executable quotes. Preserve feed labels and source rights; no artificial liquidity or calibrated probability claims.
- GitHub Actions schedules perform analysis; Vercel renders cached Supabase data. Live broker execution remains disabled.

## Move Engine revision

MOVE_ENGINE_PLAN is the new technical specification. Prior direct user instructions remain authoritative: do not purchase or activate paid services automatically.

- Reuse the working direct `FINN_HUB` binding before the unusable `FINNHUB` binding. Finnhub supports the token header; an observed HTTP 401 was credential selection, not evidence that query-string authentication is required.
- Indicative options may produce clearly labeled comparison estimates. They do not establish executable fills, verified deliverables or historical trading profits.
- Size only from a user's supplied budget; show one-contract estimated exposure otherwise. No unknown portfolio assumptions.
- A trailing-median magnitude target and an implied-move target are different events; their probabilities cannot be interchanged.
- Two quantiles alone do not identify a payoff distribution or expected option P&L. Expected-value ranking needs a validated distribution and timing/cost assumptions.
- Lightweight, same-origin quote refresh is an exception to the previous Supabase-only web rule: it requests one IEX trade and caches it under an atomic lease. All heavy analysis remains in the engine.
- Forum samples reflect self-selected opinions. Missing feeds are unavailable, not zero attention. No public-post popularity score is represented as a calibrated trading edge.
- Keep the protected preview until the new model/data and production publication requirements are resolved. Do not remove protection to test it.


### Public-feed replacement

User requested removing Alpaca after authentication failures. Use existing Finnhub credentials for quotes/news; Nasdaq daily history and Cboe delayed chains require no API key for these endpoints. Respect provider access denials and rate limits. Do not bypass verification challenges or infer redistribution entitlements. SEC filings supply dated fundamental context. Preserve old source records and strategy-version grading. No paid service or order execution enabled.
