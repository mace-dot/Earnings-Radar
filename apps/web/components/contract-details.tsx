import type { Trade } from "@/lib/types";

export function ContractDetails({ trade }: { trade: Trade }) {
  const c = trade.contract;
  if (!c) return null;
  return (
    <section className="panel">
      <h3>Buy a {c.kind}: the paper comparison</h3>
      <p>
        Strike ${c.strike.toFixed(2)} · expires {c.expiry}
      </p>
      <p>
        Quoted bid ${c.bid.toFixed(2)} / ask ${c.ask.toFixed(2)} per share.
      </p>
      <p>
        One assumed standard contract: ${c.cost.toFixed(2)} at the ask
        reference. The full premium could be lost.
      </p>
      <p>
        Expiration breakeven: ${c.breakeven.toFixed(2)}. A sale before
        expiration has different economics.
      </p>
      <p>{trade.exit}</p>
      <small>
        {c.source} · source timestamp{" "}
        {new Date(c.quote_as_of).toLocaleString("en-US", {
          timeZone: "America/New_York",
        })}{" "}
        Eastern. Indicative, not executable. The 100-share deliverable is
        assumed and must be verified. No fill, fee, quantity recommendation, or
        order is implied.
      </small>
      <p className="muted">
        A correct stock direction can still lose money because of time decay,
        changing volatility, or an expensive entry.
      </p>
    </section>
  );
}
