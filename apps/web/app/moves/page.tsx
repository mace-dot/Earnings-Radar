import { formatAsOf } from "@/lib/time";
export const dynamic = "force-dynamic";
import Link from "next/link";
import { read } from "@/lib/db";
type Features = {
  id: string;
  symbol: string;
  as_of: string;
  values: {
    vol_compression_ratio: number | null;
    bb_width_percentile: number | null;
    sample_size: number;
    rv_10: number | null;
    rv_60: number | null;
  };
};
export default async function Moves() {
  let rows: Features[] = [];
  let error = false;
  try {
    rows = await read<Features>("latest_price_features", {
      order: "values->vol_compression_ratio.asc.nullslast",
      "values->>vol_compression_ratio": "lt.0.8",
      select: "id,symbol,as_of,values",
      limit: "1000",
    });
  } catch {
    error = true;
  }
  const seen = new Set<string>();
  const candidates = rows
    .filter((r) => {
      if (seen.has(r.symbol)) return false;
      seen.add(r.symbol);
      return (
        r.values.vol_compression_ratio !== null &&
        r.values.vol_compression_ratio < 0.8
      );
    })
    .sort(
      (a, b) =>
        (a.values.vol_compression_ratio ?? 1) -
        (b.values.vol_compression_ratio ?? 1),
    )
    .slice(0, 30);
  return (
    <>
      <p className="eyebrow">MOVE RESEARCH</p>
      <h1>Find unusually quiet setups.</h1>
      <p className="muted">
        This screen compares the last 10 sessions with 60 sessions. Quiet prices
        can persist; this is not a calibrated forecast of a large move.
      </p>
      <div className="notice">
        Predictive Move Meter is not active. Historical earnings data and
        out-of-sample validation are still required.
      </div>
      <Coverage />
      {error ? (
        <p>Screen data temporarily unavailable.</p>
      ) : (
        <div className="grid">
          {candidates.map((c) => (
            <article className="card" key={c.id}>
              <h2>
                <Link href={`/stock/${c.symbol}`}>{c.symbol}</Link>
              </h2>
              <p>
                Recent/longer volatility:{" "}
                {c.values.vol_compression_ratio?.toFixed(2)}×
              </p>
              <p>
                Band-width percentile:{" "}
                {c.values.bb_width_percentile !== null
                  ? `${((c.values.bb_width_percentile ?? 0) * 100).toFixed(0)}%`
                  : "not available"}
              </p>
              <small>
                Sourced daily bars · {c.values.sample_size} observations ·
                cutoff {formatAsOf(c.as_of)}
              </small>
            </article>
          ))}
        </div>
      )}
      {!error && !candidates.length && (
        <p>No measured setups meet the current compression filter.</p>
      )}
    </>
  );
}

async function Coverage() {
  try {
    const [c] = await read<{
      total_identifiers: number;
      covered: number;
      recently_checked: number;
      unavailable: number;
      failed: number;
      waiting: number;
      latest_check: string | null;
    }>("market_coverage_summary");
    if (!c) return null;
    return (
      <section className="panel">
        <h2>Market coverage</h2>
        <p>
          {c.covered.toLocaleString()} of {c.total_identifiers.toLocaleString()}{" "}
          directory identifiers have price observations.{" "}
          {c.recently_checked.toLocaleString()} checked within 36 hours;{" "}
          {c.waiting.toLocaleString()} waiting; {c.unavailable.toLocaleString()}{" "}
          unavailable in this feed; {c.failed.toLocaleString()} failed attempts.
        </p>
        <small>
          Automatic rotating batches. Completed Nasdaq daily sessions, not
          whole-market streaming. SEC directory membership includes instruments
          whose common-share eligibility is not verified.{" "}
          {c.latest_check &&
            `Last check ${new Date(c.latest_check).toLocaleString("en-US", { timeZone: "America/New_York" })} Eastern.`}
        </small>
      </section>
    );
  } catch {
    return <p>Coverage totals are temporarily unavailable.</p>;
  }
}
