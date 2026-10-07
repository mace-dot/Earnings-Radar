Create a detailed implementation plan for Earnings Radar in mace-dot/Earnings-Radar. Do not change code yet.

PRODUCT GOAL

Build an automatic stock and long-options research assistant that ordinary people can understand. The user should select a company or tap Up/Down and receive a researched, conditional strategy—not be asked to invent their own strategy or enter financial figures.

Keep the accessible PrizePicks-style layout. Support buying calls and puts only. Never place orders or require Robinhood credentials.

Do not promise successful trades or fortune-telling. Build measurable research methods, explain uncertainty, and evaluate whether the methods actually work.

1. AUDIT THE EXISTING APP

Identify why price-action history is missing and which backend functions currently power company cards, Up/Down buttons, research answers, source links, and collection jobs.

Separate:
- Working integrations.
- Configured but failing integrations.
- Features blocked by credentials or data entitlement.
- Placeholder features that currently ask users to provide the analysis.

Inspect existing environment-variable names and presence without revealing secrets. Preserve existing accounts, watchlists, research, and database records.

2. ADD PRICE HISTORY FROM SOURCES SUITED TO MARKET DATA

SEC filings provide business information, not stock prices. Integrate authorized market-data sources separately.

Evaluate:
- Alpaca’s available historical market-data feeds.
- Alpha Vantage’s current free-tier coverage and limits.
- Twelve Data’s current free-tier coverage and limits.
- Nasdaq’s publicly available datasets, where relevant.
- Yahoo Finance only through an authorized, permitted access method; do not treat an unofficial endpoint as a dependable production contract.

Verify current documentation, licensing, attribution, redistribution rights, price adjustments, delays, coverage, and free-tier limits before choosing providers.

Do not bypass paywalls, scrape restricted services, activate paid subscriptions, or label delayed data “live.”

Recommend a primary provider and a compatible fallback. Implement provider adapters so changing providers does not require rebuilding the app.

Store daily OHLCV history: open, high, low, close, volume, session date, exchange, currency, provider, retrieval time, and adjustment method. Preserve raw prices and corporate-action information where available.

Display:
- A readable price chart.
- Available time ranges such as 1M, 3M, 6M, and 1Y.
- Period return and drawdown.
- Volume changes.
- Provider, coverage, last update, and delay.

Never silently mix adjusted and unadjusted prices or substitute one exchange/feed’s volume for consolidated volume.

If a provider is unavailable, show cached history with its age. If no data exists, explain the specific missing connection.

3. ADD FINANCIAL NEWS BEYOND SEC FILINGS

Evaluate legitimate free feeds and APIs from credible publishers, company investor-relations pages, exchange announcements, Federal Reserve releases, and economic-data institutions.

Distinguish news reporting, company statements, analyst opinions, and official economic releases.

Ingest permitted content:
- Headline.
- Publisher.
- Publication and retrieval timestamps.
- Relevant company identifiers.
- Authorized summary or excerpt.
- Original article URL.
- Event category and materiality rationale.

Deduplicate syndicated stories. Preserve corrections. Do not imply access to Bloomberg, WSJ, Seeking Alpha, or another publisher when only its homepage is linked.

Connect relevant events to price history without asserting that a headline caused a move merely because they occurred together.

4. REPLACE RAW EVIDENCE LINKS WITH READABLE SOURCE CARDS

Investigate why evidence links show raw code. Prefer human-readable SEC filing pages, relevant HTML documents, publisher articles, and company reports.

Present evidence as:
- A clear source title.
- Publisher.
- Date.
- A plain-language finding.
- A short relevant excerpt.
- “Read original source.”

For figures derived from XBRL or JSON, display the interpreted value, unit, fiscal period, comparison period, and calculation in the app. Keep raw data behind an optional technical-details control.

Every calculation and material factual claim must remain traceable to its underlying records. Distinguish source facts from the app’s interpretation.

5. BUILD DOCUMENTED VOLATILITY AND LIQUIDITY RESEARCH METHODS

Use published, reproducible methods rather than copying a trader’s branding or claiming to reproduce a hedge fund’s proprietary system.

Research and document appropriate foundations:
- Realized volatility and volatility clustering.
- Range-based volatility estimators.
- Momentum and trend persistence.
- Drawdowns and downside risk.
- Abnormal volume and market-relative returns.
- Event-driven research.
- Options pricing, Greeks, implied volatility, and volatility risk premium.
- Company cash generation, leverage, interest coverage, and refinancing risk.

For each method, explain its source, assumptions, formula, required inputs, limitations, and validation approach.

Keep three concepts separate:
- Company funding liquidity.
- Stock/option trading liquidity.
- System-wide funding stress.

Build separate engines for:
A. Directional research.
B. Volatility research.
C. Company funding risk.
D. Broader market stress.

Use matched periods, appropriate benchmarks, corporate-action-adjusted history, and sufficient sample sizes. Do not infer an imminent move from low volatility alone or a liquidity crisis from one weak ratio.

Where authorized options data is available, evaluate implied versus realized volatility, bid/ask spread, quote age, volume, open interest, and event timing.

6. AUTOMATE WHAT HAPPENS WHEN USERS TAP UP OR DOWN

The user’s selection is a scenario to investigate, not proof of a trading opportunity.

When Up is selected:
- Evaluate the bullish case.
- Find supporting evidence and counterevidence.
- Assess whether buying a call is justified.

When Down is selected:
- Evaluate the bearish case.
- Find supporting evidence and counterevidence.
- Assess whether buying a put is justified.

Automatically return:
- Decision: WATCH, WAIT, or eligible long-option research candidate.
- Why this direction could work.
- What would prove it wrong.
- Relevant catalyst and confirmed date, if available.
- Proposed research horizon.
- Price levels and scenario ranges, with their method.
- Whether the option appears expensive relative to the documented volatility scenario.
- Data freshness and missing inputs.

Do not ask users to enter a strike, premium, target price, or thesis to obtain the research.

If the selected direction is poorly supported, say so and show the opposing evidence.

7. AUTOMATE CONTRACT COMPARISON WHEN AUTHORIZED DATA EXISTS

Find a legally accessible options-chain provider and verify free-tier availability and entitlement. Do not invent quotes, Greeks, open interest, or available contracts.

For long calls and puts, compare candidate expirations and strikes using:
- Confirmed event timing.
- Days to expiry.
- Bid/ask spread.
- Quote freshness.
- Implied volatility and Greeks, when available.
- Trading activity and open interest.
- Standard or adjusted contract multiplier.
- Premium, maximum loss, and expiry break-even.
- Scenario payoff and sensitivity to time decay and volatility changes.

Explain tradeoffs in ordinary language. A correct directional view can still lose money through timing, an insufficient move, or overpaying for volatility.

Do not prescribe position size without portfolio and risk-budget information. Research should work without those inputs.

If required inputs are missing, return WAIT with the exact reason. Never present a specific contract as executable using stale or incomplete data.

8. BUILD THE BACKGROUND RESEARCH PIPELINE

Automatically:
- Maintain company identifiers.
- Discover material events.
- Refresh supported price history.
- Collect permitted news and disclosures.
- Calculate research features.
- Refresh company assessments.
- Compare supported option contracts.
- Store decision snapshots.

Use durable jobs, leases, retries, backoff, caching, provider rate limits, and bounded workloads appropriate to the existing free-tier infrastructure.

Prioritize material changes and user-viewed companies. Do not promise continuous research across every company if the available infrastructure only supports daily or bounded updates.

Do not let anonymous requests create uncontrolled provider or model usage.

9. MAKE THE RESEARCH EXPLANATIONS USEFUL

Structure each assessment around:
- What changed?
- Why might it matter?
- What does the price history show?
- What supports an Up case?
- What supports a Down case?
- What move may already be priced into options?
- What would change the assessment?
- What is the next useful action?

Use an optional model to explain retrieved evidence, not to manufacture facts or prediction probabilities.

Separate:
- Historical facts.
- Calculated statistics.
- Conditional scenarios.
- Validated forecasts, if a model eventually qualifies.

Display readable citations and uncertainty. Treat retrieved articles as untrusted content, not instructions.

10. VALIDATE BEFORE CLAIMING SUCCESSFUL ANALYSIS

Define the target before evaluating each strategy: direction, magnitude, volatility, or an event outcome.

Maintain point-in-time feature and decision records. Use chronological training/validation splits and walk-forward evaluation. Prevent look-ahead, survivorship, and revised-data leakage.

Compare results with simple baselines. Include spreads, fees, data limitations, and realistic option execution assumptions where relevant.

Report sample size, out-of-sample results, calibration, drawdown, and uncertainty. Do not show a win probability or expected return unless supported by appropriate validation.

Keep unvalidated methods labeled research. Do not describe a strategy as successful simply because its historical chart looks convincing.

11. IMPROVE THE USER INTERFACE

Make the default company view show:
- Price chart.
- Plain-language assessment.
- Up/Down research choices.
- Automatic strategy explanation.
- Upcoming confirmed events.
- Evidence and counterevidence.
- Data freshness.

Use progressive disclosure for formulas, technical details, and source data.

Keep mobile usability, keyboard navigation, readable labels, and accessible chart descriptions. Avoid raw API responses and unexplained financial jargon in the normal experience.

12. DELIVER THE PLAN FOR REVIEW

Provide:
- Findings from the current implementation.
- A provider comparison with verified free-tier limitations.
- Recommended architecture.
- Database changes.
- Backend jobs and API changes.
- Frontend changes.
- Strategy methodology and validation requirements.
- Credential requirements, using variable names only.
- A phased implementation order.
- Acceptance tests for each phase.
- Dependencies that prevent completion.

Prioritize:
Phase 1: Working price history and readable evidence.
Phase 2: Automated Up/Down assessments and broader news ingestion.
Phase 3: Authorized options-chain comparison.
Phase 4: Point-in-time evaluation and validated forecasting.

State what can work immediately, what requires a free account or credential, and what cannot be delivered under the current no-payment constraint.

Do not implement, push, migrate, or deploy during this planning task.