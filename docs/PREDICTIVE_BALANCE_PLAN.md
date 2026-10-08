# Predictive balance plan

Current build specification as of 2026-10-08, commit `cb1875a`. This file is the plan for the operational research pipeline and for predictive large-move research. `docs/MASTER_PLAN.md` remains the earlier product handoff. Where they conflict, this file and `docs/DECISIONS.md` win.

The product still explains research in plain language. A crowd reading is a research input. It is not a chance of profit.

## 0. What this revision changes

Earlier plans collect prices, filings, news, and a Stocktwits sample, then score lines. Prediction is a gate at the end: freeze features, wait for outcomes, and refuse a published probability until validation passes. That gate stays. It is not the whole research design.

The research question is now explicit:

**Which liquid common stocks are set up for a large price move, and does the case get stronger or weaker when retail discussion, authorized news, verified filings, observed trading, and — once licensed — options-market expectations disagree?**

Institutional research processes are the model for *how* the platform works: separate data desks, point-in-time features, a pre-registered target, simple baselines, walk-forward tests, and a written record of losses. The platform does not copy a hedge-fund book, and it does not claim one. The difference in *what* it looks for is deliberate. Many institutional factor books target small, slow return differences. This platform looks for large moves and for trading that is unusually heavy or unusually quiet relative to that stock’s own history. Retail discussion is included because a crowd can be early, late, crowded, or wrong, and that disagreement with filings and price is itself a testable feature.

Three statements are fixed before any model is fit:

1. A large stock move and an option profit are different outcomes. The existing forward test already labels an absolute close-to-close move over five later exchange sessions above 5 percent. That label stays the first prediction target. Option payoff is graded separately and is never inferred from the stock label.
2. Retail popularity is not an edge. A burst of posts can be a small number of accounts, a repost, a joke, or a change in what the collector was allowed to download.
3. Missing discussion is missing data. It is not a neutral reading, a quiet stock, or evidence against a move.

## 1. Current state the next build must respect

Verified at `cb1875a` and recorded in `docs/PROGRESS.md`:

- `apps/web` is the Next.js app on Vercel. `engine/` does ingestion, research, scoring, grading, and validation. Supabase is the shared database. GitHub Actions runs scheduled workers. Heavy collection stays out of Vercel request handlers.
- Finnhub current quotes work.
- Massive archive: 1,035,343 observations, 83 sessions, 2026-06-10 through 2026-10-07. Migration `019` indexes history by symbol. Do not expand the whole archive on every scan.
- Coverage at the last check: 7,185 identifiers covered, 3,254 unavailable, none failed or waiting.
- Market bootstrap run `37820124982` failed because scan shard 5 returned HTTP 500. Other scan jobs finished. The dependent research job was skipped. CI run `37820125812` passed. Vercel deployed `cb1875a`.
- Stocktwits collection is `engine/providers/community.py`. Rows land in `forum_posts`. The stock page reads them in `apps/web/components/context.tsx`. Last verified sample: 1,505 posts across 44 companies. That is a bounded recent sample, not continuous market-wide discussion.
- Predictive models are unvalidated. `engine/validation.py` version `forward-price-magnitude-v1` freezes price features only: `return_5`, `return_20`, `rv_10`, `rv_60`, `vol_compression_ratio`. It does not publish probabilities. Reports cannot approve themselves.

Operating constraints that this plan does not relax:

- No paid service without explicit authorization.
- No broker execution.
- No external notification without opt-in.
- Never commit or print credentials, authenticated URLs, or unrestricted provider bodies.
- Do not bypass paywalls, CAPTCHA, authentication, licensing, or access denials.
- A source is connected only after a real collection is normalized. Placeholder adapters stay blocked.
- Missing numbers stay missing.
- Keep publication time, first observed availability, and the decision cutoff as three different timestamps.

## 2. Five desks, kept separate

Every research case is built from five desks. A desk can be present, partial, or missing. Desks are not averaged into one mood score.

| Desk | What it is allowed to say | What it must not say | Existing code |
|---|---|---|---|
| Filings | Dated revenue, margins, cash, and balance-sheet facts from SEC filings | A price forecast, or “the business is fine” when a ratio is missing | `engine/fundamentals.py`, stock fundamentals UI |
| News | Authorized headlines, excerpts, publisher, and time | Paywalled article text, or a tone label treated as a probability | Finnhub company news path |
| Retail | Permitted posts and comments, author-declared tags, and measured activity versus that source’s own baseline | “The crowd is right,” or interest inferred from a wider API pull | `engine/providers/community.py`, `forum_posts` |
| Market | Returns, realized volatility, volume, range, and compression or expansion versus the same symbol’s history | A liquidity sweep, unless the data actually shows one | `engine/features.py`, `engine/move_features.py`, Massive archive |
| Expectations | What a licensed options and earnings feed says the market is pricing: announced report dates, implied volatility, and option-trade activity | A forecast owned by Earnings Radar, or a liquidity sweep | Not connected. Market Chameleon is the intended source and is `LICENSE_REQUIRED` |

Market Chameleon is the expectations desk, not a retail community. Its job is the institutional counterweight to the crowd: what option prices and announced events imply, set next to what forums are saying and what filings report. Until a license is purchased and a file delivery succeeds, the desk stays missing. The card says the source is not connected. It does not estimate an implied move to fill the gap.

**Balance rule.** A case is called balanced only when the market desk is present and at least one of filings, news, retail, or expectations is present, and the write-up states where they agree and where they do not. Retail alone can prioritize a symbol for collection. It cannot publish a research case. Expectations alone cannot publish one either. Filings alone can describe the business. They cannot claim a move is coming.

**Disagreement is a feature, not a defect.** These are the first cross-desk patterns to compute. Each one is a hypothesis until the validation program in §8 says otherwise.

| Pattern | Plain meaning | Required evidence | Invalid if |
|---|---|---|---|
| Crowd up, business down | People are optimistic while the latest comparable filing is weaker | Declared or inferred retail tilt, and a matched-period filing deterioration | Either side is a small sample, or the filing periods do not match |
| Crowd down, business up | People are pessimistic while the latest comparable filing is stronger | The mirror of the row above | Same |
| Talk spike, heavy trading | Discussion jumped and the session’s volume and range are unusual for this stock | Activity versus the source baseline, plus a volume and range dislocation | The collector covered more of the site than usual, or volume is missing |
| Split crowd, vol changing | Bullish and bearish posts both have weight, and realized volatility is compressing or expanding | Disagreement score and `vol_compression_ratio` | One author cluster dominates, or volatility history is short |
| Quiet crowd, coiled price | Little eligible discussion and volatility is compressed versus this stock’s own baseline | Explicit low-coverage state, not a fake zero, plus compression | Discussion was not collected, so “quiet” is unknown |
| Headlines and crowd diverge | Authorized news tone and retail tags point opposite ways | Both sources present inside the same window | One source failed and was stored as empty |
| Crowd excited, options quiet | Retail is leaning up while the licensed implied-volatility or event snapshot does not show a large priced move | Retail sample rules pass, and a Market Chameleon field contracted for that symbol is present | Expectations desk is unlicensed or the field was not in the feed |
| Crowd quiet, options busy | Eligible discussion is scarce while licensed option-trade activity or implied volatility is elevated versus that feed’s own history for the symbol | Explicit low-coverage retail state, plus the licensed options field | Discussion was not collected, so “quiet” is unknown |

Popularity or disagreement alone does not mean a move is imminent.

## 3. What “big move” and “liquidity sweep” mean here

Use a ladder. Do not skip a level because the words sound more precise.

### 3.1 Large-move targets

Pre-register these labels. Do not retune the threshold after seeing results and then present the new threshold as the original test.

| Label | Definition | Status |
|---|---|---|
| `large_move_5d` | Absolute adjusted close-to-close change over the next five exchange sessions exceeds 5 percent | Already the forward-validation target. Stock move only. |
| `large_move_direction` | Sign of that five-session change, scored only on names that realized a large move, and separately on all names | Not implemented. Direction is expected to be harder than magnitude. Report it even if it fails. |
| `earnings_event_move` | Absolute move from the pre-report close to the post-report close, compared with that symbol’s own prior event moves | Separate from `large_move_5d`. Needs a confirmed report timestamp. Do not borrow the five-day label. |
| `option_payoff` | Hypothetical intrinsic or paper contract result at a defined horizon | Already graded apart from direction. Never a substitute for `large_move_5d`. |

The user-facing phrase before validation is “research case for a large move,” not “big move likely,” and not a Move Meter.

### 3.2 Liquidity, in three levels

| Level | Name used in the product | Data required | Action |
|---|---|---|---|
| 0 | Volume-and-range dislocation | Completed daily bars already in the Massive archive: volume versus the symbol’s own 20-session median, true range versus its own 20-session median, and where the close sits in the day’s range | Implement with the price desk. This is unusual trading, not a sweep. |
| 1 | Intraday reversal versus the session average | A permitted intraday or VWAP series | Do not build until a free, authorized feed is proven. |
| 2 | Liquidity sweep | Trades that lift resting bids or offers, stop-runs, or depth leaving the book | Blocked. Needs licensed tick or depth data. Do not label Level 0 as a sweep in the interface, the model, or a commit message. |

A liquidity sweep in institutional language is an order-flow event. Daily volume cannot show it. The honest free-data analogue is: “this stock traded much more, and over a much wider range, than it usually does.” That can be studied as a predictor of later large moves. It is not evidence that stops were run.

Market Chameleon’s paid option-trades feed, if later licensed, is still not a sweep. The public feed description is end-of-day option prints with a bid/ask snapshot and greeks. That can measure unusual options activity. It does not show stock orders clearing a book.

### 3.3 Provisional windows

These are research defaults, not trading rules. Store them on every snapshot so a later change is visible.

- Recent discussion window: 24 hours.
- Comparison window: 7 days.
- Activity baseline: about 20 distinct days on which that source actually returned an eligible sample for that symbol.
- Minimum sample before a tilt is shown: at least 8 eligible posts and at least 5 distinct authors in the recent window. Below that, the card says “Small sample.”
- Before 20 baseline days exist, the card says “Building baseline,” including when the recent window is busy.

Do not infer a change in interest from a change in how much of the source the job was allowed to read. Store the request budget and the count of symbols attempted beside the post counts.

## 4. How a prediction is formed

The published object, once validation allows it, is a large-move research score. Until then the same object is stored and shown as an unvalidated case.

### 4.1 Feature blocks

Blocks stay identifiable inside the frozen vector. A later ablation must be able to drop one block without guessing which columns belonged to it.

**Market block, available now**

- Existing keys: `return_5`, `return_20`, `rv_10`, `rv_60`, `vol_compression_ratio`.
- Add only from sourced bars: 20-session volume multiple, 20-session range multiple, close location in the session range, and dollar volume. Null when the bar has no volume or the baseline is shorter than 20 sessions.
- Earnings proximity only when the calendar date is confirmed. An estimated date is a separate flag, not a number of days treated as exact.

**Filings block**

- Matched-period revenue growth and margin change, already computed as facts.
- Encode agreement with the market block as categories: improving, weakening, mixed, unavailable. Do not turn a missing filing into zero growth.

**News block**

- Count of authorized items, share of items with a permitted tone label, and whether the feed failed.
- A failed feed is a missingness flag. It is not a count of zero headlines.

**Retail block**

- Source-specific declared bullish, bearish, and unlabeled shares.
- Inferred tone, stored apart from declared tags, with an uncertain bit for sarcasm, negation, and quoted opinions.
- Distinct authors, author-concentration share, duplicate-cluster count, and activity versus that source’s own baseline.
- A coverage flag: collected, empty, failed, rate-limited, approval required, license required, credential required.
- One-hot or explicit mask for “not collected.” Never impute the neutral midpoint.

**Expectations block, only after a Market Chameleon license**

- Fields limited to the contract. The public catalog confirms an earnings feed of announced events, and an option-trades feed with bid/ask snapshots, delta, vega, implied volatility, and that day’s implied-volatility change. Do not add historical move averages, unusual-activity scores, or a Web API response shape that the signed feed does not actually contain.
- Store the file delivery time as availability. A later download of older rows is not point-in-time history unless the file itself carries the original publication time.
- Missing because the license was not bought stays a coverage flag. It is not a null implied move treated as “no expected move.”

**Regime block**

- One market-wide flag from a sourced index or volatility series if that series is already permitted. If it is not in the database, leave the block absent. Do not download a new paid index.

### 4.2 Models, in the order they are allowed to ship

| Step | Model | Job | Ship when |
|---|---|---|---|
| P0 | No model | Show the five desks, the disagreement patterns, and the data gaps, including Market Chameleon as not connected | As soon as the features exist. This is the interface default now. |
| P1 | Transparent rules | Fire a pattern from §2 only when every required input is non-null | Unit tests pass. The card says the rule is unvalidated. |
| P2 | Price-only logistic | Existing forward test. Predict `large_move_5d` from the market block | Already scaffolded. Stays a challenger until §8 passes. |
| P3 | Ablation logistics | Same label, same splits: price only; price plus filings; price plus news; price plus retail; price plus expectations; all available blocks | Another block may be added only if it improves out-of-sample Brier score against the price-only model on the untouched test, with overlapping outcome windows purged. The expectations block waits until licensed rows exist. |
| P4 | Direction model | Separate label, same freeze rules | Reported beside magnitude. A failure is a result. It does not get hidden. |
| P5 | Tree challenger | Only after P3 has a real test set | Promote only if it beats P3 on Brier and on a pre-registered utility that counts false large-move calls, not on in-sample accuracy. |

An optional language model may later summarize the permitted sentences already on the card. It may not add a fact, a citation, a number, or a confidence.

### 4.3 What the score is allowed to mean

Follow `AGENTS.md`: show a probability only after at least 200 out-of-sample cases and a stored calibration. Otherwise show a tier word only when a documented rule produced it, plus the sample size, and the sentence “This is not a chance of making money.”

Expected value per dollar, option structures, and position size stay out of this predictive program until a payoff distribution and costs exist. `docs/DECISIONS.md` already forbids inventing that ranking from direction.

### 4.4 Baselines every report must include

- Base rate: how often `large_move_5d` happened in the eligible universe, with no features.
- Volatility-only: the current five price keys.
- Momentum-only: `return_20` sign, as a directional baseline, not as a large-move model.
- Retail-only: retail block alone. This report exists to show that crowd data by itself is not the product. If it loses to the base rate, say so on the validation page.
- Expectations-only, once licensed: Market Chameleon block alone, same honesty rule.
- Full model: only the blocks that were actually non-missing for that row. List the dropped blocks per case.

If the full model does not beat the price-only model, retail, news, and expectations stay on the card as evidence and drop out of the score. The card must say that.

## 5. Phase 1 — Finish the pipeline that prediction depends on

Prediction cannot be fit on a scan that died and skipped research.

1. Inspect GitHub run `37820124982`, shard 5, and the current `market_coverage` counts. Record the safe HTTP status, Postgres error code if present, and elapsed time. Do not log keys or response bodies.
2. Keep migration `019`. Scans read the per-symbol index. They do not re-expand 1,035,343 archive rows to refresh one batch.
3. Add a short, bounded retry only for transient database failures (deadlock, statement timeout, connection reset). Retry at most three times, with recorded attempts. Authentication failures, HTTP 401 and 403, and provider denials are not retried in a loop.
4. Repair workflow dependencies. A failed shard stays failed. Research, chart refresh, scoring, grading, and validation may run when a completeness check shows enough usable covered symbols for the batch being scored. A failed collection is never stored as success. Empty coverage and failed coverage remain different statuses.
5. Run the skipped research, price and chart refresh, scoring, grading, and validation. Record the real counts.
6. Classify the 3,254 unavailable identifiers into inactive or unsupported listings, non-common-stock instruments, unresolved aliases, and genuinely missing history. Resolve an alias only with authoritative identity evidence from the exchange directory or SEC record. Do not rewrite punctuation and hope.
7. Open the deployed site and confirm a covered symbol shows sourced history and an unavailable symbol shows a missing-data state.

Acceptance: the workflow status matches the shard outcomes; research runs after a confirmed coverage floor; one transient-error test proves retry; one authentication-failure test proves no retry loop.

## 6. Phase 2 — Source access

Shared provider interface, used by Stocktwits and every later adapter:

- `collect(symbols, cursor, request_budget)`
- `normalize(record)`
- `health()`
- `capabilities()`

Capability states: `CONNECTED`, `APPROVAL_REQUIRED`, `CREDENTIAL_REQUIRED`, `LICENSE_REQUIRED`, `RATE_LIMITED`, `UNAVAILABLE`.

A capability may be `CONNECTED` only after a live or recorded successful collect and a normalize test. Tests that only prove the blocked state are required, and they must not be described as a connection.

Document each source, in `docs/PROVIDERS.md`, with access method, credential names (never values), permitted fields, refresh budget, retention and deletion duties, verified status, and whether it can run with no payment.

### Stocktwits

Extend `engine/providers/community.py`. Keep the bounded symbol sample and the original `created_at` separate from retrieval time. Add the provider’s permitted cursor if the current official API documents one. Deduplicate on provider message id. Record when the sample is only the latest page. Surface source failures on the job, not as an empty crowd.

Verify the current Stocktwits API terms before adding fields beyond body, time, id, declared sentiment, and the canonical message URL.

### Reddit

Use the approved Reddit API and OAuth. Before coding a live client, read the current official API rules on approval, pricing, rate limits, retention, and deletion. Support the required client credentials and an identifying User-Agent. Collect permitted posts and comments from a configured list of finance communities. Resolve tickers conservatively: a cashtag or a clear company name can match; a bare common word cannot. If the app is not approved, ship the adapter tests and show `APPROVAL_REQUIRED` or `CREDENTIAL_REQUIRED`. Do not scrape the website as a substitute.

### TradingView

Confirm whether any authorized community-content feed exists for this use. Do not assume a public discussion API. User-owned alerts and webhooks, if the user opts in later, are that user’s alerts, not community opinion. Embedded charts are display tools. If community text requires a contract, record `LICENSE_REQUIRED` and stop.

### Seeking Alpha

Use an authorized API, a licensed feed, or a currently permitted official RSS feed. Verify the endpoint and the rights before storing text. Allowed analysis fields are only those the terms grant: headline, excerpt, rating, or body. Do not fetch paywalled bodies. Store editorial and analyst items on the news desk, not the retail desk.

### Market Chameleon

Checked 2026-10-08 against Market Chameleon’s public developer, data-feed, and subscription pages. A direct fetch of those pages from this environment returned HTTP 403, so the notes below follow the pages as publicly indexed that day. Re-read the live pages before writing an adapter. Do not treat this section as a successful connection.

Official position on the developer page: MarketChameleon.com is display-only for a person using a browser. A Web/REST API is not available. Automated harvesting of the website is against the terms and is enforced. The stated exceptions are limited, metered CSV downloads for Premium subscribers, and bulk data feeds sold separately.

Public catalog prices seen that day, month-to-month:

| Product | Listed price | What the catalog says it contains | Plan status |
|---|---|---|---|
| Premium website | $99 | Site access, plus metered CSV downloads | Paid. Display use. Not a collection API. |
| Earnings Data Feed, internal use | $500 | Announced corporate earnings events | Paid. `LICENSE_REQUIRED` |
| Option Trades Data Feed, internal use | $500 | End-of-day OPRA option prints, bid/ask snapshot at the trade, delta, vega, implied volatility, and the day’s implied-volatility change | Paid. `LICENSE_REQUIRED` |
| Dividend feeds, internal use | $500 each | Announced, forecast, or guidance dividends | Out of scope unless a later plan needs them |
| Subscriber-specified feed | Quote only | Can combine site data, including a Web API if they build one | Do not invent that API. Email `data@marketchameleon.com` only after payment is authorized |

Feeds are licensed as personal use, internal use, or external redistribution. Internal use does not authorize publishing the numbers on the public Earnings Radar site. A public card needs the redistribution license, or it can say only that the feed is connected without reprinting licensed figures. Confirm which one the invoice covers.

Implementation rules if Mason explicitly authorizes a subscription:

- Collect through the documented file method for that feed (manual download, FTP, or WebDAV, and the vendor’s own automation notes). Do not scrape HTML. Do not bypass the 403.
- Normalize only columns present in the delivered file. Keep the symbol, event or contract identifier, the vendor’s event time, and the time the file was first retrieved.
- Put announced earnings on the expectations desk. Put option prints and implied volatility on that same desk. Do not file them as retail sentiment.
- Respect the feed’s refresh schedule. The option-trades description says publication is shortly after the close, so it is not an intraday sweep detector.
- Store credentials only in GitHub Actions or the worker environment.

Until that authorization, ship a capability record of `LICENSE_REQUIRED` and a card line: “Options-market expectations from Market Chameleon are not connected. They require a paid license.” No fixture numbers in production.

### Other retail communities

A community can be added only after the same access check. Do not add Discord, Telegram, X, or forum scrapers under this plan. Each would need its own official access decision and a row in `docs/PROVIDERS.md`.

## 7. Phase 3 — Storage and provenance

Reuse `forum_posts` for permitted post text. Add migrations for what that table cannot represent cleanly. Service role writes only. Public reads, if any, return display fields and never credentials.

Store, where the source allows it:

- provider and provider record id
- resolved symbol and the resolution method (`cashtag`, `company_name`, `unresolved`)
- publication time and first retrieval time
- canonical URL
- permitted text or excerpt, and content type (post, comment, headline, excerpt)
- author-declared sentiment and inferred sentiment in separate fields
- engagement counts with the time they were observed
- a pseudonymous author key when the source allows storing it
- duplicate cluster, language, quality flags, adapter version

Collection runs record scope, coverage interval, cursor, counts, request budget, failures, access status, and missing reasons. A run that attempted 40 symbols must not be described as the whole market.

Sentiment snapshots are versioned and immutable once written for a cutoff. Each snapshot stores symbol, cutoff, source-specific counts, distinct authors, bullish and bearish and unlabeled balance, activity versus baseline, disagreement, concentration flags, supporting record ids, and missing reasons.

Deletion and retention follow the provider’s current terms. If a provider requires deletion, delete the content. Do not keep a forbidden body in an audit table. The audit record can keep the provider id, the time of deletion, and the reason.

## 8. Phase 4 — Sentiment math, then the predictive join

Implement deterministic functions with tests before any model reads them.

- Conservative cashtag and company matching.
- Reject ambiguous mentions.
- Collapse reposts and near-duplicates so one claim is one piece of evidence.
- Mark sarcasm, negation, and quoted opinions as uncertain rather than bullish or bearish.
- Flag author concentration and a promotional burst (many similar posts, few authors, short interval).
- Compute each source’s own bullish versus bearish balance.
- Compare mention counts with that source’s own collected baseline, not with a different source and not with a later, wider crawl.
- Measure the change in balance only across snapshots that used the same adapter version and a comparable request budget.
- Measure disagreement inside a source and between sources.

Then join the snapshot to the market, filing, and news blocks at the same cutoff. The join is the input to §4. A sentiment job that finishes without writing the market join has not finished the predictive feature.

## 9. Phase 5 — Research flags the interface can show before a model is approved

Flags are sentences plus evidence, not scores dressed up as odds.

Every flag includes supporting evidence, counterevidence, missing information, source names, cutoff time, a plain-English meaning, and what would make the reading wrong.

Required first flags:

- Bearish discussion with a stronger comparable filing.
- Bullish discussion with a weaker comparable filing.
- Discussion surge with a volume-and-range dislocation.
- Strong disagreement while realized volatility is compressing or expanding.
- Large-move research case: market block shows compression or a fresh unusual return, and at least one other desk is present. The sentence names which desks are missing.

The invalidation line is concrete. Examples: “This reading fails if the next comparable filing is weaker,” “This reading fails if the volume multiple was a one-print error,” “This reading fails if the posts are removed or were mostly one account.”

## 10. Phase 6 — Automation

Integrate with `engine/discovery.py` and the existing workflows.

- Quantitative screens choose a bounded, rotating set of liquid common stocks for deeper retail collection. Quietness, recent range, volume multiple, and fair rotation are priority for research time. They are not a prediction.
- Each source has its own budget, cursor, lease, dedupe key, and backoff.
- One blocked source does not cancel the others.
- Empty and failed stay distinct in the run record.
- The run report states how many symbols were attempted and how many returned posts. It must not say the platform monitors all retail discussion.

Scheduled order after this plan:

1. History completeness check, without a full archive expansion.
2. Market features and forward-validation freeze for symbols that meet the existing eligibility rules.
3. Retail and news collection for the bounded priority set.
4. Sentiment snapshots and cross-desk flags.
5. Ablation training only when new labeled outcomes exist. Training never runs inside a web request.

## 11. Phase 7 — Interface

Add a “Crowd and evidence” card on the company page and on the board rows that already show research. Eighth-grade language. Technical counts sit behind a disclosure.

The card shows:

- “Crowd leaning up,” “Crowd leaning down,” or “Mixed,” and only when the sample rules in §3.3 pass.
- “Building baseline” or “Small sample” otherwise.
- Activity versus the measured baseline.
- How many posts and authors, and the clock times of the window.
- Which sources were read, which were blocked, and which were not configured. Market Chameleon appears as “not connected — paid license required,” not as a neutral options reading.
- Whether price and volume agree with that story, in a separate sentence.
- Why it matters, as one of the §2 patterns.
- What would make it wrong.
- Links that already pass the outbound URL allow-list.

Do not show raw JSON, internal ids, credentials, or provider error bodies.

The validation page gains an ablation section when real rows exist: price-only versus price plus retail, with the case count. If the count is below the promotion rule, the page says the test is still collecting.

## 12. Phase 8 — Validation and release

Extend `engine/validation.py` without backdating availability.

- Freeze every block that existed at the decision cutoff. A post retrieved later cannot enter an earlier snapshot.
- Compare the sentiment-enhanced vector with the price-only vector on the same untouched dates.
- Keep chronological separation. Purge train rows whose outcome window overlaps the test window.
- Keep stock-move metrics in one table and option-payoff metrics in another.
- Include losses and flags that did not precede a large move.
- Do not publish a calibrated probability until the existing rule passes: enough completed sessions, at least 200 untouched test cases, stored Brier score and reliability buckets, and a report that a human promotes. The job that trained the model cannot set `promoted`.
- No historical forum archive is invented to enlarge the training set. Retail features begin on the first day they are actually stored. Earlier cases stay price-only, and the report says the retail block was unavailable then.

Required tests:

- A post timestamped after the cutoff is rejected from that snapshot.
- A duplicate provider id is counted once.
- An ambiguous ticker stays unresolved.
- A missing source does not become a neutral balance.
- Denied access stores the blocked capability and no body text.
- Publication time and retrieval time can differ and both survive a round trip.
- Low coverage renders “Small sample” or “Building baseline.”
- A many-post, one-author cluster raises the concentration flag.
- A deletion request removes prohibited content.
- Secrets are read from the environment in the worker only.
- Playwright on the deployed site opens a company with real posts and a company with a blocked source, and both states are understandable without reading a stack trace.

Also run the Python suite, frontend unit tests, and the production build.

## 13. Release record

After the checks above, commit by phase, update `docs/PROGRESS.md` and `docs/DECISIONS.md`, push to `main`, and confirm the Vercel deployment that GitHub produced. The final progress note separates:

1. Working and verified, with counts and commit hashes.
2. Waiting on free credentials or provider approval.
3. Blocked because it needs a license or a paid feed.
4. Validation still open, including any model that ran but was not promoted.

Do not write that Reddit, TradingView, Seeking Alpha, or Market Chameleon are integrated. Do not write that liquidity sweeps or unusual options activity are detected from daily stock bars. Do not write that the platform matches a hedge fund’s results.

## 14. Implementation order

The next session should execute in this order, and stop with an honest progress note if a credential or a provider denial blocks a step:

1. Phase 1 pipeline repair and the unavailable-identifier review.
2. Stocktwits extension on the shared provider interface, with tests.
3. Reddit, TradingView, Seeking Alpha, and Market Chameleon access checks. Implement a live client only for a source whose official terms allow it at no charge. Market Chameleon stays `LICENSE_REQUIRED` unless a paid internal-use or redistribution subscription is explicitly authorized. Otherwise commit the blocked capability and the documentation row.
4. Migrations, sentiment math, and cross-desk flags.
5. Wire flags into discovery and the company card.
6. Extend forward validation with masked retail and news blocks, still unpublished.
7. Deploy and verify the card against production data.

P3 ablation training waits until labeled forward cases exist. Do not synthesize those cases from the June–October archive by pretending forum posts were collected then.
