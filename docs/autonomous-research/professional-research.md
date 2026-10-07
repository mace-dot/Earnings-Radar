# Earnings Radar: professional research and entry-process findings

Research date: 2026-10-07. This memo distinguishes reviewed primary material, published methodology, and proposed product rules. It does not establish that a practice causes outperformance, reveal private fund models, or claim to replicate a manager's returns.

## Primary sources reviewed

1. AQR Funds prospectus/statement of additional information: https://www.sec.gov/Archives/edgar/data/1444822/000119312526210899/d38130d485bpos.htm . Relevant sections describe combining value, momentum and quality; comparing securities within a relevant universe; evaluating profitability/business health; transaction-cost-aware implementation; model/data risk and crowded trading. AQR's investor supplements were also checked, but manager ownership tables do not reveal entry signals. The full prospectus, not those supplements, supports this summary.
2. Berkshire Hathaway 2024 Form 10-K: https://www.sec.gov/Archives/edgar/data/1067983/000095017025025210/brka-20241231.htm . Relevant sections describe long holding periods, concentrated equity positions, substantial capital/liquidity, and repurchases below conservatively determined intrinsic value subject to a liquidity floor. That repurchase policy is not a universal stock-entry rule. Berkshire is a conglomerate/investment business, not a hedge fund; its time horizon is poorly matched to short-dated options.
3. SEC Form 13F FAQ: https://www.sec.gov/divisions/investment/13ffaq . Filings are generally due 45 days after calendar-quarter end; short positions are excluded. Reports do not reveal exact entry prices, portfolio hedges or reasons for holding. They are context, not live copy-trading signals.
4. Bollerslev and Zhou, Expected Stock Returns and Variance Risk Premia, FEDS 2007-11: https://www.federalreserve.gov/pubs/feds/2007/200711/200711pap.pdf . This reviewed working-paper version uses market-level implied/realized variance information, a historical sample and quarterly horizons; its results depend materially on particular measurement methods and high-frequency realized variance. The results are not a current single-stock call/put success probability.
5. Alpaca Market Data API documentation: https://docs.alpaca.markets/docs/about-market-data-api and https://docs.alpaca.markets/docs/market-data-faq . The reviewed documentation distinguishes free IEX equities data, consolidated SIP, indicative options data and OPRA. Different feeds have different market coverage and entitlement. A visible TradingView chart is not a machine-readable input to the app's backend.

AQR publisher research pages, Bridgewater's All Weather page and Berkshire's shareholder-letter PDF were not retrievable in this environment. No assertion below should be represented as a newly verified quotation from those inaccessible pages.

## What these methods contribute

### Systematic value, momentum and quality

The AQR prospectus supports a process of ranking comparable securities using multiple fundamental and price characteristics, then controlling portfolio exposure and implementation cost. The transferable lesson is to combine interpretable evidence rather than chase a headline. It does not disclose a specific universal threshold that justifies buying a call today. Cross-sectional value, medium-term momentum and company quality can disagree, so the assistant must show disagreements and match its forecast horizon to the instrument.

### Fundamental valuation and liquidity discipline

Berkshire's materials support valuing economic ownership, maintaining funding capacity and tolerating price fluctuations over long periods. Fundamental strength is useful for downside resilience, but an undervalued company can stay undervalued longer than an option survives. The app must translate an economic thesis into a dated catalyst and separately compare the cost of the option. A Berkshire-style business case alone is not permission to buy a weekly call.

### Volatility and option pricing

Variance-risk-premium research concerns compensation for bearing volatility risk and the relationship between option-implied and realized variance. It does not say that high volatility makes long options cheap. Long calls/puts may lose through time decay and falling implied volatility despite a correct directional view. The app needs authorized contract quotes, spreads, expiry, IV/Greeks when supplied, realistic scenarios and cost assumptions. It must distinguish variance-premium research from a simplistic implied-versus-realized volatility subtraction.

### Institutional position-entry process

A proposed entry process for this product is: identify an economic mechanism; establish a horizon; inspect source quality; calculate descriptive features; corroborate a trigger; find counterevidence; assess market conditions and crowding; compare alternatives and instrument costs; reject stale/illiquid contracts; apply risk limits; save an immutable decision. These are product design principles derived from established portfolio practice, not a private fund's disclosed entry algorithm.

Professional outcomes also depend on execution, financing, transaction costs, portfolio diversification, capacity, staffing, fees, selection bias and luck. Public manager success stories cannot isolate the contribution of any one rule. A stronger engineering objective is an auditable decision process and honest out-of-sample evaluation.

## Published-methodology references for further verification

- Moskowitz, Ooi and Pedersen (2012), Time Series Momentum: https://doi.org/10.1016/j.jfineco.2011.11.003 . Distinguish own-price trend from cross-sectional relative strength. The linked paper was not newly retrieved in this session.
- Asness, Frazzini and Pedersen, Quality Minus Junk: https://doi.org/10.1007/s11142-018-9470-2 . Quality is a multi-dimensional construct; it is not merely positive EPS. Bibliographic reference; full linked paper not newly retrieved.
- Brunnermeier and Pedersen (2009), Market Liquidity and Funding Liquidity: https://doi.org/10.1093/rfs/hhn098 . Funding constraints and trading liquidity can reinforce each other. Bibliographic reference; full linked paper not newly retrieved.
- Engle (1982), ARCH: https://doi.org/10.2307/1912773 . Model time-varying conditional volatility; do not assume a stationary volatility estimate forecasts an event jump. Bibliographic reference.
- Parkinson (1980), range-based volatility: https://doi.org/10.1086/296071 . OHLC estimators have assumptions and limitations. Bibliographic reference.
- Black and Scholes (1973): https://doi.org/10.1086/260062 . European-option model assumptions are not exact for dividend-paying American equity options. Bibliographic reference.
- Bailey et al., The Probability of Backtest Overfitting: https://doi.org/10.21314/JCF.2016.322 . Protect evaluation from parameter-search selection bias. Bibliographic reference.

## Boundaries for manager inspiration

Bridgewater/All Weather can be investigated for macro regime and risk diversification; it is not evidence for concentrated long-option timing. Trend-following CTAs can inform systematic triggers and risk scaling. Renaissance/Simons and multi-manager firms can inform questions about empirical validation, execution and drawdown control, but their proprietary alpha and entry criteria are not available here. Discretionary trader interviews and books can suggest falsifiable hypotheses; they are not audited proof of a rule's profitability. Do not attribute proposed product defaults or exact thresholds to these managers without a verifiable source.

## Additional directly reviewed institutional disclosure

AQR Funds alternatives prospectus, filed April 28, 2026: https://www.sec.gov/Archives/edgar/data/1444822/000119312526185725/d29849d485bpos.htm . This document includes Managed Futures Strategy, Macro Opportunities, Style Premia and other distinct funds. Its managed-futures description relates position direction and size to systematic assessments of trends using price/fundamental data, continuation and instrument risk, across multiple asset classes. Its equity-model discussion describes selecting signals for economic intuition, historical forecasting efficacy, statistical/economic significance and effectiveness across universes and market environments. These are public process descriptions; the proprietary formulas are not disclosed. Fund-specific volatility targets vary and must not be copied into a retail option risk budget. The prospectus explicitly distinguishes targeted from realized volatility.

An additional January 26, 2026 filing was inspected; corporate/legal references alone were not treated as evidence of trading criteria. Reviewed documents are regulatory disclosures, not proof of profitable live performance. No causal ranking of hedge funds or audited comparison of their private entries was performed.

## Research conclusions that change the design

1. A directional thesis, a timing thesis and an instrument-value thesis require separate approval. No amount of strong fundamentals repairs an option that expires before the expected catalyst.
2. Public disclosures reveal useful process standards, not a downloadable hedge-fund algorithm. Institutional signal horizons and instruments differ from retail long calls/puts.
3. Searching more outlets does not necessarily add independent information. Syndication, repeated commentary and revisions must be tracked.
4. “Contrarian” requires an observable expectations benchmark and evidence that contradicts it. A unpopular opinion alone is not an edge.
5. Company funding risk and market trading liquidity are different mechanisms. An app may screen funding pressure; it cannot reliably forecast a specific liquidity crisis from ratios alone.
6. High historical volatility describes risk. A profitable volatility trade also depends on the premium paid, future path, liquidity and event-driven repricing.
7. Backtests must measure realistic instruments and costs at the information timestamps actually available. A successful underlying-stock signal does not validate an options strategy.
8. Good automation produces an explicit “wait” when required data is absent, while still delivering useful business research and explaining what would change the decision.
