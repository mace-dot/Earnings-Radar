# Alpha Vantage free-call budget

The free key allows 25 requests per day. A request is one API call. This budget spends those calls on upcoming earnings moves.

## Daily allocation

| Calls | Use | Why |
|---|---|---|
| 1 | `EARNINGS_CALENDAR`, three-month horizon, once per UTC day | Refreshes upcoming report dates for the whole covered market. The evening Finnhub refresh does not repeat this call after a successful morning download. |
| up to 23 | `EARNINGS`, one symbol each | Saves quarterly reported EPS, the estimate included with that report, and the surprise. |
| 1 | Spare | Left unused so a limit response or a manual doctor check does not push the account over the published cap. |

The scan does not spend calls on daily prices, company overviews, news sentiment, or options. Those are already covered elsewhere or are paid on this provider.

## Who gets a history call

Eligible names have a report date from 5 days ago through 60 days ahead and are common stock or still unclassified. The order is:

1. No saved history, report within 14 days.
2. No saved history, report within 60 days.
3. The report has passed and the saved history does not yet include that report.
4. Inside each group, a name with compressed volatility or a 20-session move of at least 2 percent comes first, then common stock, then the soonest report date.

A symbol that already has a pre-report snapshot is skipped until the report date passes. An empty result is not retried for 7 days. Anything attempted today is not attempted again today.

## What a saved row means

`estimate_revisions` stores the provider's reported quarter, first observed at retrieval time. The feed does not include the original publication time of the estimate, so these rows are not backdated into earlier model cases. The company page describes them as past reports. A missing estimate stays missing. The scan does not turn a history of beats into a probability.

## Stop rules

A provider limit message stops the rest of the run and records `quota`. The workflow then treats that pass as finished for the day. Authentication and entitlement failures are not retried in a loop.
