import { LivePrice } from "@/components/live-price";
import { sourceURL } from "@/lib/source-url";
export type Market = {
  source: string;
  observed_at: string;
  retrieved_at: string;
  feed: string;
  payload: {
    latestTrade?: { p: number; t: string };
    option_estimate?: {
      source?: string;
      implied_move: number;
      event_specific: boolean;
      expiry: string;
      strike: number;
      as_of: string;
    };
  };
};
export type News = {
  id: string;
  headline: string;
  url: string;
  source: string;
  published_at: string;
  retrieved_at: string;
};
export type Forum = {
  id: string;
  published_at: string;
  retrieved_at: string;
  payload: { text: string; url: string; sentiment?: { basic?: string } };
};
export function Context({
  symbol,
  market,
  news,
  forums,
}: {
  symbol: string;
  market: Market[];
  news: News[];
  forums: Forum[];
}) {
  const latest = market[0];
  const option = latest?.payload.option_estimate;
  const bull = forums.filter(
    (p) => p.payload.sentiment?.basic === "Bullish",
  ).length;
  const bear = forums.filter(
    (p) => p.payload.sentiment?.basic === "Bearish",
  ).length;
  return (
    <>
      <div className="two-column">
        <LivePrice
          symbol={symbol}
          initialSource={latest?.source}
          initialPrice={latest?.payload.latestTrade?.p}
          initialTime={latest?.observed_at}
        />
        <section className="panel">
          <h2>What paired options cost</h2>
          {option ? (
            <>
              <p className="metric">
                ±{(option.implied_move * 100).toFixed(1)}%
              </p>
              <p>Indicative ATM pair · expiry {option.expiry}</p>
              <p>
                {option.event_specific
                  ? "Matched to a provider-estimated report date"
                  : "General expiry range; not an earnings-move estimate"}
              </p>
              <small>
                {option.source ?? "Stored option source"} · as of{" "}
                {new Date(option.as_of).toLocaleString()}. This is a cost
                comparison, not a predicted move.
              </small>
            </>
          ) : (
            <p>No paired option estimate available.</p>
          )}
        </section>
      </div>
      <div className="two-column" style={{ marginTop: 24 }}>
        <section className="panel">
          <h2>News to investigate</h2>
          <p className="muted">
            Published headlines, not verified catalysts or model predictions.
          </p>
          {news.length ? (
            news.slice(0, 8).map((n) => {
              const href = sourceURL(n.url);
              return (
                <article key={n.id} className="row">
                  <div>
                    {href ? (
                      <a href={href} target="_blank" rel="noopener noreferrer">
                        {n.headline} ↗
                      </a>
                    ) : (
                      <span>{n.headline}</span>
                    )}
                    <br />
                    <small>
                      {n.source} · published{" "}
                      {new Date(n.published_at).toLocaleString()} · retrieved{" "}
                      {new Date(n.retrieved_at).toLocaleString()}
                    </small>
                  </div>
                </article>
              );
            })
          ) : (
            <p>No recent headlines collected.</p>
          )}
        </section>
        <section className="panel">
          <h2>What a sampled crowd says</h2>
          <p>
            {bull} bullish tags · {bear} bearish tags · {forums.length} recent
            sampled posts
          </p>
          <p className="muted">
            Stocktwits opinions are not a representative market survey. Untagged
            posts are not treated as neutral. Popularity alone is not an edge.
          </p>
          {forums.slice(0, 5).map((f) => (
            <article key={f.id} className="row">
              <div>
                <p>{f.payload.text.slice(0, 300)}</p>
                <small>
                  {new Date(f.published_at).toLocaleString()} · collected{" "}
                  {new Date(f.retrieved_at).toLocaleString()}
                </small>
              </div>
            </article>
          ))}
        </section>
      </div>
    </>
  );
}
