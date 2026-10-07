Implement the following plan for Earnings Radar.

Repository: mace-dot/Earnings-Radar
Website: https://earnings-radar-two.vercel.app/
Stack: Vercel website and API, Supabase database and authentication.

GOAL

Transform Earnings Radar into an autonomous, market-wide financial research and forecasting assistant.

The user should be able to research any supported public company without entering prices, financial statements, company identifiers, or Robinhood information. Background scanning should independently discover companies and opportunities beyond a small watchlist.

The experience should feel like a “genie”: gather evidence, interpret developments, explain potential outcomes, identify missing information, and monitor whether its conclusions were correct. Do not claim certainty or manufacture predictive accuracy.

The user buys individual calls and puts through Robinhood. The app should obtain research data independently and should not require brokerage credentials.

Inspect the current implementation before editing. Preserve existing evidence, authentication, private watchlists, and saved research ideas. Implement and test the changes, push to main, and verify Vercel’s automatic deployment. Do not stop at proposing an architecture when implementation is feasible.

BUDGET AND ACCESS

Keep the existing preference for free services. Do not activate paid infrastructure, data subscriptions, or AI usage without explicit authorization.

A free website does not establish permission to scrape, retain, or redistribute its content. Use authorized APIs, permitted feeds, and primary documents. Never bypass paywalls, authentication, licensing restrictions, or rate limits.

Identify costs, coverage, delays, quotas, and missing credentials early. Complete independent work while access-dependent features remain blocked. Explain concrete blockers without pretending unavailable integrations work.

1. BROAD COMPANY COVERAGE

Replace the hardcoded company list with a searchable company directory.

- Import official SEC ticker, company-name, CIK, and exchange mappings.
- Support ticker and company-name searches.
- Handle share classes, renamed companies, and identifier changes.
- Automatically queue filings and financial-history retrieval when a company is requested.
- Display collection progress and research freshness.
- Explain coverage limits for foreign, private, newly listed, or unsupported companies.

Separate on-demand company research from background market scanning. Directory membership must not imply that a company has already been fully analyzed.

2. AUTONOMOUS DISCOVERY

Build a durable background scanner that discovers candidates without relying solely on user watchlists.

Screen for:
- New earnings releases, filings, and material disclosures.
- Changes in revenue, margins, operating cash flow, and financing obligations.
- Unusual price moves or trading volume.
- Volatility compression and expansion.
- Verified upcoming catalysts.
- Documented guidance or expectation changes.
- Company funding concerns and relevant macroeconomic developments.

Use inexpensive broad screening first, then deeper research for promising candidates.

Implement persistent queues, atomic leases, retries with backoff, checkpoints, caching, deduplication, and stale-data detection. Failed jobs must not indefinitely block other companies.

Choose scheduling and coverage that are sustainable under the authorized budget. Do not imply real-time market-wide analysis if the system performs delayed or rotating scans.

3. AUTOMATIC MARKET AND OPTIONS DATA

Remove manual financial-data entry as a dependency of normal research.

Evaluate authorized providers for:
- Historical and current stock prices.
- Volume and corporate actions.
- Earnings calendars.
- Dated analyst consensus and management guidance.
- Options chains, bid/ask prices, expirations, implied volatility, and Greeks.

Verify provider rights, current pricing, delays, quotas, and retention restrictions. Select suitable free coverage where available.

If a feature cannot operate adequately on free data, explain the limitation and leave it unavailable. Do not use unauthorized endpoints or fabricate substitutes.

Robinhood is the user’s execution platform, not the required research-data provider.

4. AI RESEARCH ORCHESTRATOR

Implement this pipeline:

Discover → collect evidence → calculate metrics → investigate → challenge the thesis → rank → explain → monitor outcomes.

The AI should:
- Read permitted primary documents and credible reporting.
- Extract facts with citations, units, fiscal periods, and timestamps.
- Compare developments with financial history and documented expectations.
- Explain the economic mechanism.
- Identify affected companies only through documented relationships.
- Develop bullish and bearish scenarios.
- Seek counterevidence.
- Identify invalidation conditions and missing inputs.
- Produce a short, understandable conclusion.

Investigate suitable hosted or open-weight models. Do not assume model access or required compute is free.

Use bounded tool access, validated structured outputs, caching, spending limits, and a useful deterministic fallback. External documents must never control system instructions, credentials, or tool permissions.

5. THREE DISTINCT RESEARCH ENGINES

Directional engine:
Investigate evidence for an upward or downward move over a defined horizon.

Volatility engine:
Investigate whether future movement might differ from what current options prices imply.

Funding-stress engine:
Investigate deterioration in company financing or broader market liquidity.

Keep these conclusions separate. Improving company results do not automatically make a call attractive. High volatility does not automatically make an option profitable.

For funding stress, use multiple independently supported dimensions:
- Company cash obligations and financing needs.
- Credit conditions.
- Bank funding.
- Market trading liquidity.
- Volatility and relevant macroeconomic conditions.

Missing indicators remain unknown. Do not convert one weak financial ratio into a market-wide crisis forecast.

6. CORE FINANCIAL AND QUANTITATIVE METHODS

Implement transparent calculations when suitable inputs exist:
- Comparable revenue growth.
- Gross, operating, and net margins.
- Operating cash flow, free-cash-flow proxies, and cash conversion.
- Leverage, liquidity, and interest coverage.
- Valuation ratios with reliable inputs and timestamps.
- Historical realized volatility.
- Volatility compression and expansion.
- Average true range.
- Unusual-return and volume-anomaly measures.
- Momentum, drawdown, and market-relative behavior.
- Options-implied movement and volatility comparisons.

Preserve units, period compatibility, corporate-action adjustments, evidence references, and calculation timestamps.

Explain every measure in ordinary language. Distinguish descriptive statistics from predictive models.

7. EXPECTATIONS VERSUS REALITY

A contrarian opportunity requires:
- A documented market expectation.
- Independently supported evidence challenging that expectation.
- A plausible financial mechanism.
- Valuation and market-reaction context.
- A catalyst or reason the disagreement could resolve.
- Counterarguments and invalidation conditions.

Distinguish analyst consensus, management guidance, news sentiment, and expectations inferred from prices.

Do not label a thesis contrarian merely because it opposes a headline or receives a high research score.

8. AUTOMATED LONG-CALL AND LONG-PUT EVALUATION

Once sufficiently fresh options data is connected, evaluate individual long calls and puts using:
- Verified catalyst timing relative to expiration.
- Contract identity and deliverable.
- Current bid/ask prices and liquidity.
- Premium, expiration break-even, and maximum premium loss.
- Implied volatility versus historical context and scenario assumptions.
- Time decay and sensitivity to implied-volatility changes.
- Scenario outcomes after realistic trading costs.

Return investigate, wait, or no attractive option when appropriate. Do not force a trade recommendation for every company.

Any suggested contract must include:
- Data timestamp.
- Supporting thesis.
- Catalyst and horizon.
- Principal risks.
- Missing inputs.
- Invalidation conditions.

Do not treat expiration-payoff arithmetic as a prediction of the option’s value before expiration.

9. FORECAST VALIDATION AND TRACK RECORD

Define targets and horizons before evaluating predictive models.

Examples:
- Stock direction over a specified number of trading sessions.
- Realized movement relative to an options-implied threshold.
- Deterioration in a defined funding indicator.

Use point-in-time datasets and walk-forward evaluation. Address:
- Look-ahead bias.
- Revised data and corporate actions.
- Survivorship bias and delisted companies.
- Overlapping outcomes.
- Transaction costs and liquidity.
- Multiple testing and repeated experimentation.

Compare performance with simple benchmarks.

Report out-of-sample sample sizes, uncertainty, and calibration. Do not display probability-of-success percentages until validated results justify them.

Maintain an immutable prediction ledger containing:
- What the system concluded.
- Its target and horizon.
- Evidence available at that time.
- Model and configuration versions.
- Subsequent outcome.
- Evaluation limitations.

Preserve unsuccessful predictions. Do not rewrite old conclusions using future evidence.

10. ACCESSIBLE PRODUCT DESIGN

Keep the stock pick-board layout with prominent company tiles and concise explanations.

Build:
- Discover: automatically researched companies beyond the watchlist.
- Today’s opportunities: ranked candidates and one-sentence explanations.
- Any-company search: automatically starts supported research.
- Up / Down / Big move: clearly distinguished research categories.
- Market weather: measured funding and liquidity conditions.
- Company assistant: answers questions using stored evidence.
- What changed: thesis-strengthening, weakening, or invalidating updates.
- Track record: outcomes and forecasting limitations.
- Data checks: actual source coverage, freshness, and failures.

Each card should lead with:

What changed → Why it matters → What could happen → What to check next.

A person without a finance background should understand the main message. Put technical detail behind expandable explanations and define unfamiliar terms.

Distinguish:
- Confirmed facts.
- Calculations.
- Interpretations.
- Hypotheses.
- Validated forecasts, if any.

Maintain responsive layouts, keyboard access, readable contrast, understandable empty states, and private account isolation.

11. TRANSPARENT RANKING

Rank candidates using explainable factors:
- Evidence quality and freshness.
- Financial materiality.
- Verified catalyst proximity.
- Documented expectation gaps.
- Market and options context.
- Counterevidence.
- Data completeness.

Show why each candidate ranks highly and penalize missing or conflicting evidence.

A research score is not a probability of profit. If no candidates satisfy the requirements, say so.

12. IMPLEMENTATION ORDER

First produce a short audit, source-access matrix, architecture, and dependency map.

Then implement:
1. Company directory and on-demand research queue.
2. Durable autonomous scheduling and source monitoring.
3. Authorized stock, catalyst, expectation, and options integrations.
4. Financial calculations and broad screening.
5. AI orchestration and evidence-backed explanations.
6. Automated long-option evaluation.
7. Prediction tracking and validation.
8. Discovery interface, company assistant, and notifications.

Make reviewable commits. Preserve working integrations and existing records.

Do not send notifications or messages until the user explicitly enables a destination.

13. VERIFICATION AND DEPLOYMENT

Test:
- Real source retrieval and storage.
- Company search and identifier resolution.
- Queue recovery and retry behavior.
- Calculation accuracy and period compatibility.
- Evidence-reference validity.
- Account isolation.
- Missing-data and stale-data behavior.
- Forecast evaluation without future information.
- Deployed Vercel and Supabase behavior.

Push completed changes to main and verify the automatic Vercel deployment.

Report what works, what was tested, and what remains blocked. Do not describe a configured schedule as proof that a scheduled collection actually succeeded.

ACCEPTANCE CRITERIA

- Searching a supported public company automatically retrieves and interprets available data.
- The scanner discovers candidates without user-entered stock information.
- Connected market data replaces manual price entry.
- Background research continues without an open browser.
- Every substantive conclusion has traceable evidence.
- Option evaluations use sufficiently fresh, authorized inputs.
- Forecast performance is measured transparently.
- Missing evidence can produce “wait” rather than a confident guess.
- The deployed application stays within the authorized budget.

The desired product is an autonomous research and forecasting assistant. Its “genie” experience must come from doing the research automatically, explaining it clearly, and improving against measured outcomes—not pretending uncertainty has disappeared.