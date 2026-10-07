# Statistical research upgrade

Implemented: server-generated Up/Down cases, matched-period fundamental comparisons, funding warnings, readable SEC financial-filing links, public RSS collectors with provenance, an authorized daily-price adapter, cached price charts, descriptive statistics and sensitivity scenarios. Private data remains private.

Verified locally: parser/calculation tests, no-data and malformed-data behavior, cache preservation, automatic strategy interaction, source safety, chart accessibility, and existing application regressions. Live Supabase has migration 005. Existing Tesla evidence generates both directional cases and readable source destinations.

Not yet live: company price bars, because no Alpaca credentials or confirmed public-display entitlement are configured. No synthetic prices are seeded. The chart is exercised with test-only fixtures, not presented as a live data integration. Exact provider free-tier display rights must be checked before enabling. No options chain, live Greeks, confirmed earnings calendar, consensus dataset or calibrated forecasting model is connected.

News feed success and production deployment are verified separately after release. The collectors read timestamped headlines from public feeds; they do not search the whole internet or read inaccessible full articles. Optional hosted-model synthesis is disabled. Frameworks are reproducible financial/statistical methods, not reproductions of proprietary investors' systems or claims of successful trading.

Methods: matched fiscal-period year-over-year changes, margin/cash-conversion/interest-coverage ratios; log-return sample standard deviation annualized with 252 sessions; high/low Parkinson volatility estimate; 14-session true-range ATR; 20/60-session momentum/drawdown; latest volume versus previous 20 bars; previous-session return baseline for z-scores. Five/20-session price ranges are zero-drift log-price sensitivities scaled by square-root time, not calibrated probabilities. Independent/constant-volatility assumptions may fail during event shocks; indicators are correlated.

References for methodology: [Parkinson's range estimator](https://doi.org/10.1086/296071), [Engle's ARCH framework](https://doi.org/10.2307/1912773), [Jegadeesh–Titman momentum study](https://doi.org/10.1111/j.1540-6261.1993.tb04702.x), [Options Industry Council education](https://www.optionseducation.org/). Current calculations are descriptive; ARCH modeling, portfolio sizing and options valuation are not implemented merely by citing these references.
