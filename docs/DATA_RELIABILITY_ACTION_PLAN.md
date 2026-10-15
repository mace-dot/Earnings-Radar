# Data reliability and budget course of action

Audit baseline: main 3f2b944, October 14, 2026 (Eastern). Prices below were checked
against official provider pages during the audit; verify current terms before purchase.

## 1. Stabilize operation before adding providers

- Massive history acquisition returns HTTP 403 in recent GitHub runs. Distinguish
  subscription entitlement, release timing, authentication, and rate limits using
  safe diagnostic categories. Do not print provider messages or rotate keys blindly.
- Keep cached data with its original source date. A successful cached read is not a
  successful fresh acquisition. Never relabel prior-session data as a live quote.
- Full-market screening remains separate from deeper research. Bound deeper runs
  to 300 symbols, prioritize queued requests and unexpired recent research, and
  rotate the calendar cohort daily. Completed and failed queue records do not keep
  every previously researched company in the routine scoring universe forever.
- Bootstrap research may run after a failed scan shard only after an independent
  gate finds 100 covered histories, each with at least 61 observations and a source
  session within the last three exchange sessions. This is a degraded-recovery
  threshold, not full-market completeness or live-entry eligibility. The original
  scan failure still makes the workflow fail visibly.

## 2. Resolve the free-history / validation timing mismatch

- Latest archived daily session at audit: October 13. Corporate-action reference:
  October 14. Same-session prospective validation currently has zero cases.
- Inspect the account's actual daily-data release policy. If current-session
  history is unavailable at the scheduled cutoff, record that restriction.
- New validation diagnostics report the latest source session and rows skipped for
  session lag. Preserve the strict availability and same-session gates.
- Do not simply move the anchor back one day: that changes the target and can
  include a return that already occurred before the decision.
- A different cutoff or a live-close anchor requires a separately versioned model
  definition, consistent adjustment basis, exact tradable-session horizon, and
  leakage tests. Collect real forward outcomes before independent model approval.

## 3. Reduce storage safely

Database reports 1,252 MB; largest tables at audit:
line_sides 539 MB, daily_bars 256 MB, features 153 MB, lines 114 MB.
The bounded workload limits new growth; it does not reclaim existing storage.

Next retention implementation must first produce a dry-run inventory and an
export manifest with checksums and tested restoration. Protect all published
picks, outcomes (including losses), frozen validation cases, referenced evidence,
and source availability timestamps. Identify foreign-key dependencies before
selecting expired unpublished research for archival. Do not delete records as
part of this release. Archiving must avoid triggering a paid storage service.
Monitor logical data and physical table/index sizes separately; ordinary deletes
need not immediately shrink physical storage. Do not run VACUUM FULL casually
on a serving database.

## 4. Select the minimum useful provider stack

| Requirement | First choice | Cost / conditions |
| --- | --- | --- |
| Reported fundamentals | SEC EDGAR | Free; use an identifying User-Agent and fair-access limits. |
| Adjusted daily history | Existing Massive account | Free EOD tier; verify entitlement and release schedule. Starter is $29/month and 15-minute delayed, not live. |
| Current stock quotes/news | Existing Finnhub account | Verify actual account entitlements and timestamps; do not assume historical candles are included. |
| Personal live stock/options quotes | Evaluate Tradier brokerage API | Lite lists $0/month; requires an eligible account and agreements. Consolidated live stocks/options; sandbox delayed; Greeks hourly. Other account/trading fees may apply. |
| Standalone stock/options API | Evaluate Market Data Trader | $75 month-to-month, or $30/month equivalent with annual commitment. Advertises nonprofessional live stocks/options; verify quote coverage, credit use and exchange agreements. |

Official links:
- https://www.sec.gov/search-filings/edgar-application-programming-interfaces
- https://massive.com/stocks
- https://docs.tradier.com/docs/market-data
- https://www.tradier.com/individuals/pricing
- https://www.marketdata.app/pricing/

Personal subscriptions and brokerage API access do not automatically authorize
redistribution on a public Vercel site. Obtain appropriate display rights before
public use. Do not purchase, open brokerage accounts, transfer funds, or enable
execution automatically. Robinhood can remain the user's execution platform.

## 5. Acceptance before declaring the app fully functional

1. Fresh acquisition succeeds and stores genuine timestamps.
2. Coverage distinguishes supported, unresolved, unavailable, stale and failed names.
3. A deployed company chart shows the new session and identifies its source.
4. Quote and contract eligibility preserve latency/entitlement restrictions.
5. Published research has costs, evidence, counterevidence and invalidation rules.
6. Grading retains losses and does not invent missing option marks.
7. Prospective validation starts collecting eligible cases and later outcomes.
8. CI passes; production deployment is ready; storage growth is monitored.

Only after these checks should broader Reddit/TradingView/Seeking Alpha sentiment
be added using approved APIs or permitted feeds. Do not buy news subscriptions
as a substitute for reliable prices and executable option quotes.
