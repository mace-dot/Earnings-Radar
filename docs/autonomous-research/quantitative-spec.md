# Quantitative specification and validation examples

Proposed implementation requirements, October 7, 2026. Examples are hypothetical, not current quotes or trade recommendations. Parameters require testing; formulas do not establish an edge by themselves.

## Descriptive features

For split-adjusted comparable closing prices, r_t = ln(P_t/P_(t−1)). Annualized daily realized volatility is sample standard deviation(r) × sqrt(252), conventionally using 252 trading sessions. Report sample count, window and adjustment convention. This is backward-looking, not a probability of an imminent move. Overnight and intraday returns can have different dynamics.

True range is max(high−low, abs(high−previous_close), abs(low−previous_close)). ATR uses a registered smoothing method/window. Do not mix Wilder smoothing and simple averages under one version. ATR measures dollar range, not expected direction.

Parkinson variance estimate is mean[ln(high/low)^2] / (4 ln 2); annualize its square root with the chosen session convention. It assumes a particular continuous-price process; jumps, overnight gaps, microstructure and invalid OHLC affect interpretation. Compare with close-return volatility rather than declaring one universally superior.

Market beta = cov(stock returns, benchmark returns)/var(benchmark returns), using synchronized sessions. Report unstable/insufficient estimates and residual risk. Sector-relative returns can help identify company-specific movement, but they do not prove causality.

Comparable volume anomaly can use median and median absolute deviation for the same feed and comparable session slice. Do not compare 10am partial volume with prior full days. A zero MAD needs a defined fallback. IEX volume remains IEX volume. Relative volume is not institutional flow or dealer gamma exposure.

Financial growth = current_comparable / previous_comparable − 1 when the denominator is meaningful. Negative or near-zero base values can produce misleading percentages; show absolute change and explain. Margin = numerator/revenue with consistent definitions. CFO minus defined capex is one cash-flow measure, not universally comparable owner earnings.

A cash-runway estimate requires usable cash, a defensible burn period and explicit financing/seasonality assumptions. It is a conditional scenario, not a bankruptcy date. Debt maturities need footnote extraction; total debt alone does not locate near-term funding stress.

## Forecast targets must be explicit

Possible underlying targets: return over N trading sessions; probability of exceeding a predeclared return barrier; volatility over a future window; range/gap risk around a verified event. These are different labels and require separate evaluation.

An option target needs a contract, entry time/quote assumption, exit policy, actual multiplier and cost model. “Stock went up” is not a winning-call label. A long put outcome similarly depends on premium and expiry. Forecast event clocks in exchange/session time; do not silently count weekends as trading observations.

For a model predicting p and binary event y, Brier = mean((p−y)^2). Log loss penalizes confidently wrong probabilities. Calibration bins compare forecast probability with observed frequency and uncertainty intervals. Always compare a relevant unconditional/conditional baseline. A model that abstains on every difficult case needs coverage reporting; apparent precision alone can conceal cherry-picking.

Do not turn percentile ranks or weighted feature scores into success percentages. A score can rank research priority, with its definition exposed, while remaining explicitly uncalibrated.

## Hypothetical option examples

Example A: underlying $100; standard $100 call purchased for $5, multiplier 100, fees ignored for illustration. Cost $500. At expiry the stock is $103: intrinsic value $300, net loss $200, despite a 3% rise. At $105, break-even before fees. At $110, net profit $500. If it expires at/below $100, premium loss $500. These expiry outcomes do not describe selling early.

Example B: an earnings event occurs before expiry, but implied volatility falls sharply afterward. Even if the stock rises, the call's pre-expiry bid may be below the entry ask. To quantify that outcome, use an appropriate valuation/scenario method or actual quotes, including time remaining, volatility and dividends. Do not supply an invented numerical premium from delta alone.

Example C: a $100 put costs $4. At expiry $98, intrinsic value $2, loss $200 for a standard contract before fees. Expiry break-even $96. A correct modest bearish view was insufficient.

Example D: option bid $2.00, ask $2.40. Mid $2.20; spread/mid ≈18.18%. Buying at ask then immediately selling at unchanged bid loses $40 per standard contract before fees. This motivates a liquidity review; it does not prove that every 18% spread contract is unusable or that a 9% spread is safe.

Example E: hypothetical expiry call above has stock outcomes $90/$100/$110 and externally justified scenario weights 0.2/0.5/0.3. Contract outcomes −$500/−$500/+$500, expected payoff −$200 before fees. This is illustrative arithmetic only. Without validated probabilities, display the outcomes without an expected-value claim. Scenario weights must not be invented to make the trade attractive.

## Event, liquidity and contrarian research

For an event study, define event type/time, window, universe, inclusion rules, benchmark, overlapping-event handling and corporate-action adjustment before inspecting outcomes. Report distribution and sample limitations rather than only average return. Conditioning on numerous subgroups increases selection risk.

A funding-pressure thesis needs a causal chain: obligations due → accessible resources/funding options → potential gap → possible management/regulatory response → plausible effects on equity. Include alternative financing and asset-sale scenarios. Equity price stress and insolvency are not synonyms. Market trading liquidity concerns spreads/depth/turnover and can deteriorate without company funding insolvency.

An expectations-divergence thesis needs: a dated expectation benchmark; a primary new fact; its economic relevance; evidence the benchmark has not already adjusted; and a plausible time for repricing. If these are absent, label “interesting fundamental development,” not “hidden institutional opportunity.” Prices can already reflect information without visible news coverage.

## Deterministic decision gate pseudocode

```text
resolve identity and eligible source usage
load point-in-time observations; keep missing values explicit
calculate versioned features using comparable windows/periods
build supporting case and strongest countercase
publish useful business research even if market inputs are incomplete

if price history missing: block price-dependent strategy assessment
if dated mechanism absent: withhold event-driven timing claim
if expectations benchmark absent: mark contrarian edge unverified
if model not approved: use conditional scenarios, never success odds

for each proposed option:
    validate underlying, expiry, strike, type, multiplier and adjustments
    require appropriate permitted quote feed and open-session freshness
    check bid/ask consistency, spread, size and event-expiry alignment
    calculate one-contract premium exposure and scenario outcomes
    reject unsupported contracts; explain exact reason

if user budget/holdings unknown: do not suggest personalized quantity
save immutable decision with evidence, versions and invalidation conditions
schedule evaluation with the original decision cutoff preserved
```

Risk checks can downgrade or reject; a fluent narrative cannot override them. A denied contract assessment does not require deleting the underlying company's useful research.

## Evaluation and promotion checklist

1. Verify point-in-time labels, delisted symbols, adjusted histories and publication dates.
2. Register strategy/feature definitions and all parameter-search trials.
3. Train and evaluate chronologically; handle overlapping labels and event dependence.
4. Retain a final untouched test interval and prospectively paper-observe.
5. Include spread/fees/slippage assumptions, unknown fills and instrument availability.
6. Compare baselines and report coverage, calibration, tail losses and uncertainty.
7. Break results down by regime, sector, liquidity and horizon, with sample counts.
8. Perform sensitivity checks to thresholds/costs and identify failure conditions.
9. Require reviewed model promotion; block automatic self-approval.
10. Monitor distribution shift and suspend probabilities when outside evaluated scope.

No fixed sample count universally validates a strategy. Closely correlated trades do not provide independent samples. A model useful for prioritizing research may still be unsuitable for contract-return predictions.
