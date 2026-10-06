# Sources, capabilities and access

The dedicated `data/research.db` stores evidence, source registry, revisions, jobs,
analyses, alerts, delivery state and evaluations. The existing `earnings_radar.db`
remains the user's CSV/notes/paper journal. Demo data uses `demo.db` only.
Reputation is not proof; claims retain attribution and source references.

Official documentation checked on 2026-10-06:

| Source | Adapter / coverage | Access, delay and retention |
|---|---|---|
| SEC | Submissions: 8-K, 10-K, 10-Q and amendments for watchlist CIKs | Public metadata. Real contact User-Agent required. At most 4 requests/sec per worker, below SEC's 10/sec aggregate limit. Not a future earnings calendar. |
| Federal Reserve | Official press-release and speech RSS | Public titles, URLs, publication dates; speeches labeled opinion. Poll every 5 minutes; publisher delay measured separately. No full-document crawling. |
| Alpaca news | `/v1beta1/news`, bounded checkpointed pagination | Key/secret and entitled news subscription. Metadata only, no article bodies. News access may be delayed; no real-time assertion. |
| Alpaca IEX | `/v2/stocks/quotes/latest?feed=iex` | Key/secret. Single-exchange data classified indicative, not consolidated executable option quotes. Options entitlement not assumed. |
| Bloomberg | Registry entry | Licensed API/feed and retention agreement required; no scraper. |
| WSJ / Dow Jones | Registry entry | Authorized feed/API required; no paywall bypass. |
| EarningsHub | Registry entry | Exact site/API identity requested; integration not guessed. |
| Seeking Alpha | Registry entry | Authorized/licensed content feed required; contributor opinion separate from primary evidence. |
| Yahoo Finance | Registry entry | Authorized API/terms not verified. Unofficial endpoints/cookie workarounds not used. |
| Google Finance | Registry entry | No supported authorized API verified. No scraper. |
| Truth Social | Registry entry | Direct API eligibility, pricing, credentials and rights unverified. Original statements cannot be inferred from a secondary headline. |

References checked successfully:
- https://www.sec.gov/search-filings/edgar-application-programming-interfaces
- https://www.sec.gov/about/developer-resources
- https://www.federalreserve.gov/feeds/feeds.htm
- https://docs.alpaca.markets/docs/market-data-faq
- https://docs.alpaca.markets/reference/news-3
- https://docs.alpaca.markets/reference/stocklatestquotes-1
- https://docs.alpaca.markets/reference/optionsnapshots (examined; no live options adapter claimed)
- https://core.telegram.org/bots/api

SEC submissions and Fed RSS returned real HTTP 200 responses. Alpaca adapters have
not been tested live because credentials are absent. Feed/API access is not a
redistribution license: this initial tool stores reference metadata for personal research.
Confirm provider contracts before retaining additional licensed data or publishing.
Bloomberg, WSJ, Seeking Alpha, Yahoo, Google, model documentation and corporate Truth
API documentation were blocked by network policy during inspection. Registry entries
are requirements, not functioning integrations. Required domains were added to the
cloud configuration draft; saving that draft does not apply or publish it.

## Configuration

`RADAR_WATCHLIST=AAPL,MSFT,NVDA` (maximum 20 tickers). Seed mappings use SEC CIKs
0000320193 / 0000789019 / 0001045810. Custom mappings require explicit
`RADAR_CIK_MAP` JSON and must be verified against SEC before use.
Set `SEC_USER_AGENT` to your actual name/organization and contact email.
Set `ALPACA_API_KEY` and `ALPACA_API_SECRET` securely; never commit values.
Poll collection is a reconnect strategy; no websocket latency claim is made.
Run one collector per machine initially; multiple machines must share an aggregate
rate limiter and move durable state to Postgres before deployment.

## Model and political coverage

The optional Anthropic Messages interface was checked against the official
https://github.com/anthropics/anthropic-sdk-python README. Model calls use a fixed HTTPS
host, no tools, bounded context and 2,000 output tokens. Set `ANTHROPIC_API_KEY` securely,
`RADAR_MODEL_ENABLED=true`, an available `RADAR_MODEL`, and a daily reservation budget.
Each call reserves $0.10 pessimistically; this is not measured invoice spending. Confirm
current model pricing is within that ceiling before enabling. Model faults fall back to
factual notices. No live call or model efficacy claim has been made.

EarningsHub was identified by the user as https://earningshub.com/. Access was blocked
by the environment network policy; authorized API terms remain unverified. No endpoint
was invented. SEC now uses the user's provided real contact through local ignored
configuration; it does not require a SEC account.

Political headlines remain statements/proposals/unknown unless evidence supports a
more specific status. Secondary news never proves policy enactment. Direct Truth Social
API access is unverified; no scraping workaround is implemented. An entitled news
adapter can supply attributed secondary coverage after live access is verified.
