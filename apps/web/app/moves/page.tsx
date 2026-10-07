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
    rows = await read<Features>("features", {
      order: "as_of.desc",
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
                Alpaca IEX daily bars · {c.values.sample_size} observations ·
                cutoff {new Date(c.as_of).toLocaleString()}
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
