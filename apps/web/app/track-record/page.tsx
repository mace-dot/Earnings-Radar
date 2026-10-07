import { read } from "@/lib/db";
import type { Pick, Outcome } from "@/lib/types";
export default async function Record() {
  let picks: Pick[] = [];
  let outcomes: Outcome[] = [];
  let error = false;
  try {
    [picks, outcomes] = await Promise.all([
      read<Pick>("picks", { order: "as_of.desc", limit: "100" }),
      read<Outcome>("pick_outcomes", { order: "graded_at.desc", limit: "100" }),
    ]);
  } catch {
    error = true;
  }
  return (
    <>
      <p className="eyebrow">WINNERS AND LOSERS</p>
      <h1>Track record</h1>
      <p className="muted">
        Actual published cases only. Fixtures and unvalidated model results are
        not a trading record.
      </p>
      {error ? (
        <div className="notice">Track record is temporarily unavailable.</div>
      ) : (
        <section className="panel">
          <h2>
            {outcomes.length} evaluated cases · {picks.length} published in this
            view
          </h2>
          {!picks.length && (
            <p>
              No published performance yet. There is no historical hit rate to
              report.
            </p>
          )}
          {picks.map((p) => {
            const outcome = outcomes.find((o) => o.pick_id === p.id);
            return (
              <div className="row" key={p.id}>
                <span>
                  {p.symbol} · {p.side}
                  <br />
                  <small>{new Date(p.as_of).toLocaleDateString()}</small>
                </span>
                <span>
                  {outcome?.payload.result ?? "Pending evaluation"}
                  {outcome?.payload.return_fraction !== undefined && (
                    <>
                      <br />
                      <small>
                        {(outcome.payload.return_fraction * 100).toFixed(2)}%
                        underlying direction, not option P&amp;L
                      </small>
                    </>
                  )}
                </span>
              </div>
            );
          })}
        </section>
      )}
    </>
  );
}
