import { read } from "@/lib/db";
import type { Pick } from "@/lib/types";
export default async function Picks() {
  let picks: Pick[] = [];
  let error = false;
  try {
    picks = await read<Pick>("picks", { order: "as_of.desc", limit: "50" });
  } catch {
    error = true;
  }
  return (
    <>
      <p className="eyebrow">PUBLISHED SETUPS</p>
      <h1>Radar picks</h1>
      {error ? (
        <div className="notice">Pick history is temporarily unavailable.</div>
      ) : !picks.length ? (
        <div className="notice">
          No validated picks have been published. The board has two-sided price
          research; model validation and contract inputs are still pending.
        </div>
      ) : (
        <div className="grid">
          {picks.map((p) => (
            <article className="card" key={p.id}>
              <h2>
                {p.symbol} · {p.side}
              </h2>
              <p>
                {p.payload.line_kind} · {p.payload.tier}
              </p>
              <small>Published {new Date(p.as_of).toLocaleString()}</small>
            </article>
          ))}
        </div>
      )}
    </>
  );
}
