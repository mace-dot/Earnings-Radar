# Quantitative research methods

The hosted app separates documented facts, historical market statistics, and hypotheses. It does not claim to reproduce a proprietary hedge-fund model. No calibrated predictive model is currently deployed. Public SEC filings and XBRL facts support fundamental context; Federal Reserve feeds support macro context. Authorized Alpaca adjusted IEX daily bars enable descriptive price statistics. IEX is single-exchange coverage, not consolidated market data.

## Implemented measures

- Daily log returns: log(close_today / close_previous_session).
- Realized volatility: sample standard deviation of the last 20 or 60 returns times sqrt(252), displayed as an annualized percentage. This is historical dispersion, not an options-implied forecast.
- Volatility compression: 20-session volatility divided by 60-session volatility below 0.7. This is a transparent, unvalidated research flag. It does not imply an imminent breakout or its direction.
- Return z-score: latest return minus the mean of up to 60 **preceding** returns, divided by their sample standard deviation. The latest return is excluded from the baseline. Absolute scores at least 2 trigger an unusual-move research flag; returns are not assumed Gaussian and this is not a significance/profit probability.
- ATR: mean of the last 14 true ranges, using high-low and gaps from prior close. ATR divided by the latest close provides a comparable percentage.
- Momentum: 20-session close-to-close total adjusted price change.
- Drawdown: current adjusted close versus the highest adjusted close of the last 60 sessions. This is not maximum historical peak-to-trough drawdown.
- Beta: sample covariance of stock and SPY daily log returns divided by SPY sample variance over up to 60 aligned returns (at least 40 pairs).
- SEC fundamental context: reported USD revenue, net income, gross profit, and year-over-year changes only when a comparable period is available. Period duration and source filing precision matter. Net-income changes use the absolute prior value; loss-to-profit transitions should not be interpreted as ordinary revenue growth.

At least 61 valid completed daily bars are required; timestamps must be timezone-aware, session dates ordered/unique, and prices finite/positive. Zero-variance scores are unavailable, never infinity. Bars use split/dividend adjustments; historical revisions can change results. Each snapshot displays its last bar date. Collection time is not a live quote timestamp.

## Expectations versus reality

A contrarian opportunity requires **documented expectations**, an independently supported factual deviation, a plausible economic mechanism, valuation context, a dated catalyst, and evidence that would invalidate the thesis. These inputs cannot be derived merely by reversing headline sentiment. Current consensus and executable options data are missing; the website labels the gap unverified. A low-volatility stock is not automatically undervalued and high volatility does not imply a profitable trade.

## Before adding predictive stock picks

Store point-in-time expectations, prices, corporate actions, release dates, and source arrival times. Define a prediction target/horizon and benchmark in advance. Validate with walk-forward splits, embargo overlapping outcomes, retain delisted securities, account for transaction costs/liquidity and multiple testing, and compare with a simple baseline. Report sample sizes, confidence intervals, calibration, and out-of-sample results. Never use future filings, revised data unavailable at the decision time, or profitable backtests to imply guaranteed outcomes. The current descriptive flags have not passed this validation.

Useful methodological background: Fama & French (1992), *The Cross-Section of Expected Stock Returns*, Journal of Finance; Engle (1982), *Autoregressive Conditional Heteroscedasticity with Estimates of the Variance of United Kingdom Inflation*, Econometrica; Bollerslev (1986), *Generalized Autoregressive Conditional Heteroskedasticity*, Journal of Econometrics; Harvey, Liu & Zhu (2016), *… and the Cross-Section of Expected Returns*, Review of Financial Studies. These works inform research design; referencing them does not validate this application's flags. No GARCH model or Fama–French factor model is implemented.

## Fundamental research interpretation and priority

The research API computes matched-period gross/operating/net margins, operating cash flow divided by positive net income, a free-cash-flow proxy (operating cash flow minus property/plant/equipment purchases), operating-income/interest-expense coverage, and liabilities/assets. Ratios retain both evidence IDs and reject mismatched periods/units. Negative/zero denominators are unavailable. Liabilities/assets is not debt/assets; total liabilities include non-debt obligations. The free-cash-flow proxy omits other investment categories. Annual/quarterly revenue charts retain fiscal end dates; source publication timestamps are distinct.

Research ranking is a rule-based priority score: primary-source support (20), publication freshness (up to 20), specific reported numbers/excerpts (20, versus headline-only 5), a supported year-over-year comparison (15), limited context completeness (5), missing consensus (-10), and missing market context (-5). Weekly eligibility also requires publication within seven days, a score of at least 40, and specific evidence. These conservative fixed rules are not calibrated forecasts. No opportunity is called contrarian merely because its score is high. Counterevidence absence is explicit and does not count as corroboration.
