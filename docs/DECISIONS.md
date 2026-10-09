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


### Discovery and freshness policy

Use measured setup priority for research allocation only: quietness, past price changes, and fair rotation. Require independently dated source history and exchange-directory common-stock classification. Do not interpret rank, agent agreement or indicator count as profit probability. Preserve published records across strategy versions. Return source-unavailable/partial states when a feed fails, and do not label a price refresh as a new research collection.


### Coverage-cache recovery

When fresh history collection fails, reuse only genuinely acquired coverage observations available at the scoring cutoff. Preserve original source and timing, use immutable insertion for existing observations, and keep the source failure visible. Normalize only exact whole-share volumes; do not round fractional values. Display all market timestamps in America/New_York with an explicit Eastern label.

### Supported historical replacement and earned forward validation

Standard Nasdaq collection fails outside the managed cloud environment; Yahoo remains rate-limited and Stooq unavailable in the tested GitHub context. Use an account-authorized Massive/Polygon grouped daily archive when a usable credential exists. Verify actual free-plan entitlement before claiming the feed works. Source denials remain observable; neither credentials nor source challenges are bypassed. Download once per session and share within the worker rather than repeating full-market histories per ticker.

Price-magnitude model evaluation must use frozen prospective inputs, five later exchange sessions and verified split-free windows. Current historical cache acquisition times cannot be backdated to manufacture point-in-time training cases. Store real calibration and uncertainty when enough cases exist; do not publish a number merely because tests or a model training call ran successfully. The new five-session target is distinct from event-specific earnings moves and option-contract profit.

### Predictive balance — retail evidence and large moves

The next research program is specified in `docs/PREDICTIVE_BALANCE_PLAN.md`. Institutional-style process means separate evidence desks, point-in-time features, pre-registered targets, ablation against a price-only baseline, and human promotion. It does not mean reproducing a hedge-fund portfolio or claiming its results.

The research target is a large stock move, first the existing five-session absolute move above 5 percent. Direction, earnings-event moves, and option payoffs stay separate labels. Retail posts, authorized news, and SEC facts can enter that model only as their own blocks, with missingness preserved. They are dropped from the score if they do not beat the price-only model out of sample. They still remain visible as evidence.

Daily volume and range versus the same stock’s history may be called a volume-and-range dislocation. They are not a liquidity sweep. A sweep requires licensed trade or depth data and stays blocked under the no-payment rule. Forum history is not backfilled. Sentiment features start on the day they are actually stored.

Alpha Vantage's free key allows 25 requests per day. One request refreshes the three-month earnings calendar. The remaining calls, minus one spare, download reported earnings history for upcoming reports, soonest first, and skip a symbol that already has a pre-report snapshot. Prices, news, overviews, and options are not spent from this allowance. A provider limit message stops the run. Saved rows are first observed at retrieval time; the feed does not supply the original estimate publication time, so they cannot be backdated into earlier validation cases.

Market Chameleon is the planned expectations desk: announced earnings events and end-of-day option prints with implied volatility, as a counterweight to retail discussion. As of 2026-10-08 its developer page says the website is display-only, scraping is prohibited, and there is no public Web API. Catalog feeds are paid, and an internal-use license is not permission to republish figures on the public site. No subscription is authorized. The desk stays `LICENSE_REQUIRED` until a specific feed and redistribution right are approved.

The forward test `forward-price-magnitude-v2` keeps the five price features and adds days until the report, volume and range versus the prior 20 sessions, a saved Cboe implied move, one SPY return and realized-volatility reading, and the last saved earnings surprise plus a four-quarter beat rate. Each new value has a known flag so a blank stays blank. Finnhub and Alpha Vantage date disagreements leave the day count missing. Earnings history and implied moves are used only after their own save time, so older decision dates do not receive them. The five-session 5 percent target is unchanged, and probabilities stay unpublished.
