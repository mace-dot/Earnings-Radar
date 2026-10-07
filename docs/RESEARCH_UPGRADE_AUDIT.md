# Research upgrade audit and architecture

## Findings before implementation

The Vercel API serves 96 source records, but many cards merely restate filing titles. The source directory lists access requirements alongside working feeds without clear operational status. Watchlist additions are browser-local and do not change collection. GitHub Actions hourly collection exists but cannot be enabled from this session because GitHub API access is denied. No Alpaca credentials, consensus estimates, options feed, or validated predictive model are present. Paid model calls remain disabled.

## Implementation architecture

Keep existing SQLite evidence and Supabase research records intact. Add a standard-library Vercel research collector, authenticated Supabase watchlists, immutable source metadata and financial interpretations. A free-tier daily Vercel cron and authenticated manual collection use the same leased, rate-limited pipeline. Read-only public research is separate from private account watchlists. Auth uses Supabase sessions; server validation is required before writes. The collector rotates through a bounded active universe and displays coverage rather than promising every stock refreshes daily.

## Source access matrix

| Source | Actual access and reuse | Implementation |
|---|---|---|
| SEC submissions/XBRL | Official public APIs; identified User-Agent, bounded requests below 10/sec; reported facts attributed | Working; company filings, financial facts and excerpts |
| Issuer releases filed as SEC exhibits | Official filing archive; no general IR-site scraping | Bounded primary-document excerpts; coverage varies |
| Federal Reserve releases/speeches | Official public feeds/documents; attributed summaries, speeches are opinions | Working RSS, bounded linked-document excerpts |
| BLS | Official government release RSS; metadata, primary publication links | Add only after live feed verification |
| Treasury/BEA | Official data/publications; specific formats/endpoints require verification | Unsupported until adapter and validation exist |
| FRED/ALFRED | Authorized API key and per-series third-party rights may apply; vintage data needed for backtests | Available but not configured; no key-free rights assumption |
| Alpaca historical IEX | Authorized account/data entitlement; free allowance and current terms govern | Available but not configured; no paid subscription enabled |
| Bloomberg/WSJ/Seeking Alpha | Licensed feeds/retention agreements | Licensed access required; never shown connected |
| Yahoo/Google Finance/EarningsHub | A public website does not establish API/retention permission | Unsupported authorized integration |
| Academic studies | Methodological background only; access/retention varies | References do not substitute for data or validate signals |

The lawful alternative to licensed news is the underlying filing or official release, not an unauthorized copy. Headlines and excerpts are distinguished from independently verified financial claims.

## Validation boundaries

Research scores are transparent prioritization scores, not probabilities. Missing consensus/market data reduces ranking. Retain changes and show point-in-time evidence availability; outcome evaluation is unavailable without market data. Full walk-forward predictive validation cannot be claimed while its required inputs are absent. No paid service or model usage is authorized. Cron runs daily under Hobby constraints; collection is scheduled rather than streaming.
