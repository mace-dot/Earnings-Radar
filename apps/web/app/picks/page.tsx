import { read } from "@/lib/db";
import type { Pick } from "@/lib/types";
import Link from "next/link";
import { ContractDetails } from "@/components/contract-details";
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
      <p className="muted">
        Automatically selected paper research, not validated predictions. Every
        published setup stays in the record, including losses. No brokerage
        order is placed.
      </p>
      {error ? (
        <div className="notice">Pick history is temporarily unavailable.</div>
      ) : !picks.length ? (
        <div className="notice">
          No qualifying paper setups have been published yet. A setup needs
          measured price history and a usable option quote; missing inputs are
          not replaced with invented contracts.
        </div>
      ) : (
        <div className="grid">
          {picks.map((p) => (
            <article className="card" key={p.id}>
              <h2>
                <Link href={`/stock/${p.symbol}`}>{p.symbol}</Link> · {p.side}
              </h2>
              <p>
                {p.payload.line_kind} · {p.payload.tier}
              </p>
              <span className="pill">
                Unvalidated paper research · no probability
              </span>
              {p.payload.trade && <ContractDetails trade={p.payload.trade} />}
              <h3>Why it was selected</h3>
              <ul>
                {p.payload.bullets?.map((b) => (
                  <li key={b}>{b}</li>
                ))}
              </ul>
              <h3>What could go wrong</h3>
              <ul>
                {p.payload.countercase?.map((b) => (
                  <li key={b}>{b}</li>
                ))}
              </ul>
              <p>{p.payload.invalidation}</p>
              <details>
                <summary>Selection and grading rules</summary>
                <p>{p.payload.selection_rule}</p>
                <p>{p.payload.grading_rule}</p>
              </details>
              <small>Published {new Date(p.as_of).toLocaleString()}</small>
            </article>
          ))}
        </div>
      )}
    </>
  );
}
