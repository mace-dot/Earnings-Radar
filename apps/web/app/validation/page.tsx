import Link from "next/link";
import { read } from "@/lib/db";
import { formatAsOf } from "@/lib/time";
export const dynamic = "force-dynamic";
type Report = {
  trained_at: string;
  payload: {
    frozen_cases: number;
    labeled_cases: number;
    eligible_cases: number;
    out_of_sample_n: number;
    reason?: string;
    brier?: number;
    blocked_corporate_action_cases: number;
  };
};
export default async function Validation() {
  let row: Report | undefined;
  let unavailable = false;
  try {
    [row] = await read<Report>("model_registry", {
      line_kind: "eq.stock_move_5_sessions",
      order: "trained_at.desc",
      limit: "1",
    });
  } catch {
    unavailable = true;
  }
  return (
    <>
      <p className="eyebrow">FORECAST TESTING</p>
      <h1>Confidence has to earn its place.</h1>
      <p className="muted">
        We are testing whether a stock could finish five trading sessions more
        than 5% above or below its starting close. This tests the size of a
        stock move, not a call or put&apos;s profit.
      </p>
      <section className="panel">
        <h2>Current stage: collecting and checking evidence</h2>
        <p>
          Each case freezes the information available when it was created. We
          wait for later prices, then test on later cases that were kept out of
          training. No model probability is approved for trading yet.
        </p>
        {row ? (
          <>
            <div className="grid">
              {[
                ["Frozen research cases", row.payload.frozen_cases],
                ["Recorded outcomes", row.payload.labeled_cases],
                ["Cases passing data checks", row.payload.eligible_cases],
                ["Untouched test cases", row.payload.out_of_sample_n],
              ].map(([label, value]) => (
                <article className="card" key={label}>
                  <h3>{label}</h3>
                  <p>{Number(value).toLocaleString()}</p>
                </article>
              ))}
            </div>
            <p>
              Testing needs at least 30 completed decision days and 200
              untouched test cases, with separate training and calibration
              periods.
            </p>
            {row.payload.blocked_corporate_action_cases > 0 && (
              <p>
                {row.payload.blocked_corporate_action_cases.toLocaleString()}{" "}
                outcomes cannot enter validation because their price-adjustment
                checks have not passed.
              </p>
            )}
            {row.payload.brier !== undefined && (
              <p>
                Probability error: {row.payload.brier.toFixed(4)}. Lower is
                better; this result still requires independent review.
              </p>
            )}
            <small>
              Evaluation source: frozen research records ·{" "}
              {formatAsOf(row.trained_at)}
            </small>
          </>
        ) : (
          <p>
            {unavailable
              ? "Testing records are temporarily unavailable."
              : "The first testing report has not been recorded yet."}
          </p>
        )}
      </section>
      <section className="panel">
        <h2>What can hold a case back?</h2>
        <p>
          Missing fresh price history, incomplete split checks, too few
          completed outcomes, or poor calibration. Recalculating an old price
          does not make it fresh. A stock-only result cannot validate an options
          strategy.
        </p>
        <Link href="/track-record">
          See the separate public paper-pick record →
        </Link>
      </section>
    </>
  );
}
