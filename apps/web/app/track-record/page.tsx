import { read } from "@/lib/db";
import type { Pick, Outcome } from "@/lib/types";
export default async function Record() {
  let picks: Pick[] = [];
  let outcomes: Outcome[] = [];
  let error = false;
  try {
    picks = await read<Pick>("picks", { order: "as_of.desc", limit: "100" });
    if (picks.length)
      outcomes = await read<Outcome>("pick_outcomes", {
        pick_id: `in.(${picks.map((p) => p.id).join(",")})`,
        limit: "100",
      });
  } catch {
    error = true;
  }
  return (
    <>
      <p className="eyebrow">WINNERS AND LOSERS</p>
      <h1>Track record</h1>
      <p className="muted">
        The latest 100 published paper cases, winners and losers. These rules
        are unvalidated. Hypothetical expiration results are separate from
        underlying direction and are not executed trading performance.
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
                  {outcome?.payload.hypothetical_pnl !== undefined && (
                    <>
                      <br />
                      <small>
                        ${outcome.payload.hypothetical_pnl.toFixed(2)}{" "}
                        hypothetical expiration P&amp;L, before fees
                      </small>
                    </>
                  )}
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
                <details>
                  <summary>Evaluation details</summary>
                  <p>
                    Review horizon:{" "}
                    {new Date(p.expires_at).toLocaleString("en-US", {
                      timeZone: "America/New_York",
                    })}{" "}
                    Eastern
                  </p>
                  <p>{outcome?.payload.note ?? p.payload.grading_rule}</p>
                  {outcome && (
                    <small>
                      {outcome.source} · graded{" "}
                      {new Date(outcome.graded_at).toLocaleString("en-US", {
                        timeZone: "America/New_York",
                      })}{" "}
                      Eastern
                    </small>
                  )}
                </details>
              </div>
            );
          })}
        </section>
      )}
    </>
  );
}
