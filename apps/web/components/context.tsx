import { formatAsOf } from "@/lib/time";
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
}: {
  symbol: string;
  market: Market[];
  news: News[];
}) {
  const latest = market[0];
  return (
    <>
      <LivePrice
        symbol={symbol}
        initialSource={latest?.source}
        initialPrice={latest?.payload.latestTrade?.p}
        initialTime={latest?.observed_at}
      />
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
                      {n.source} · published {formatAsOf(n.published_at)} ·
                      retrieved {formatAsOf(n.retrieved_at)}
                    </small>
                  </div>
                </article>
              );
            })
          ) : (
            <p>No recent headlines collected.</p>
          )}
        </section>
      </div>
    </>
  );
}
