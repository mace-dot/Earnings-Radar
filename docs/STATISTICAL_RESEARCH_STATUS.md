# Statistical research upgrade

Implemented: server-generated Up/Down cases, matched-period fundamental comparisons, funding warnings, readable SEC financial-filing links, public RSS collectors with provenance, an authorized daily-price adapter, cached price charts, descriptive statistics and sensitivity scenarios. Private data remains private.

Verified locally: parser/calculation tests, no-data and malformed-data behavior, cache preservation, automatic strategy interaction, source safety, chart accessibility, and existing application regressions. Live Supabase has migration 005. Existing Tesla evidence generates both directional cases and readable source destinations.

Not yet live: company price bars, because no Alpaca credentials or confirmed public-display entitlement are configured. No synthetic prices are seeded. The chart is exercised with test-only fixtures, not presented as a live data integration. Exact provider free-tier display rights must be checked before enabling. No options chain, live Greeks, confirmed earnings calendar, consensus dataset or calibrated forecasting model is connected.

News feed success and production deployment are verified separately after release. The collectors read timestamped headlines from public feeds; they do not search the whole internet or read inaccessible full articles. Optional hosted-model synthesis is disabled. Frameworks are reproducible financial/statistical methods, not reproductions of proprietary investors' systems or claims of successful trading.

Methods: matched fiscal-period year-over-year changes, margin/cash-conversion/interest-coverage ratios; log-return sample standard deviation annualized with 252 sessions; high/low Parkinson volatility estimate; 14-session true-range ATR; 20/60-session momentum/drawdown; latest volume versus previous 20 bars; previous-session return baseline for z-scores. Five/20-session price ranges are zero-drift log-price sensitivities scaled by square-root time, not calibrated probabilities. Independent/constant-volatility assumptions may fail during event shocks; indicators are correlated.

References for methodology: [Parkinson's range estimator](https://doi.org/10.1086/296071), [Engle's ARCH framework](https://doi.org/10.2307/1912773), [Jegadeesh–Titman momentum study](https://doi.org/10.1111/j.1540-6261.1993.tb04702.x), [Options Industry Council education](https://www.optionseducation.org/). Current calculations are descriptive; ARCH modeling, portfolio sizing and options valuation are not implemented merely by citing these references.


Production validation: Vercel automatically deployed the first implementation commit. `/api/company`, `/api/strategy`, readable SEC destinations, and missing-price states were checked live. The production daily handler researched three additional identifiers and retrieved permitted news headlines: Yahoo Finance (24 retained records), CNBC (20), and BLS (1) in the checked dashboard window. BEA collection failed and is displayed as unavailable. Counts refer to that window, not lifetime totals or guaranteed future feed availability. A manual secured collector invocation does not establish a future scheduler invocation.

Daily discovery now enqueues one representative identifier per issuer to avoid spending the bounded batch on multiple share/bond classes of the same company. The identifier heuristic does not certify common-stock status, optionability or liquidity; users can request other official identifiers through search. Saved research ideas automatically request current assessments in a bounded sequence. Recent ticker-feed reports are displayed as reported developments requiring corroboration, not treated as independently verified directional signals.

Fundamental collection includes alternate revenue concepts, current assets/liabilities and cash balances. Quarterly, half-year, nine-month and annual durations are retained; comparisons require the same fiscal duration and matched periods, so year-to-date cash flow is not compared with a single quarter. Current ratio complements cash conversion and interest coverage.

## Provider-hosted price charts

Company views now embed a provider-hosted TradingView chart, defaulting to one-minute candles and offering interval/date-range controls. The widget is loaded directly from the provider in an isolated cross-origin frame; raw prices are not scraped or proxied. TradingView attribution and a full-chart link remain visible. Exchange-qualified symbols use official company-directory metadata when available. Actual realtime/delayed status, supported symbols and market-session status are determined and displayed by the provider. A running widget is not proof of consolidated realtime exchange data.

Charts mount before company research finishes. The Big swings lane retains company access even when computed volatility statistics are missing. This visual chart is independent of the Alpaca analytical feed; no chart observations are read back into backend models, and the existing raw-price display entitlement gate is retained. No subscriptions, broker orders or additional credentials are activated.

DOM smoke checks cover frame URL construction, exchange/class-share mapping, symbol validation, source attribution and accessible frame titles. The execution environment blocks direct TradingView requests, so an actual rendered provider chart/quote has not been inspected here. Production verification checks the served integration and frame CSP; runtime chart availability must not be described as independently verified realtime quotes.
