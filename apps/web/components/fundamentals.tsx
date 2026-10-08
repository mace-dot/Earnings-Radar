import { sourceURL } from "@/lib/source-url";
export type FinancialContext = {
  retrieved_at: string;
  values: {
    quarter_revenue_yoy: number | null;
    quarter_net_margin: number | null;
    current_ratio: number | null;
    cash: number | null;
  };
  periods: Record<
    string,
    { end: string; filed: string; filing_url?: string } | null
  >;
};
export function Fundamentals({
  context,
  sector,
}: {
  context?: FinancialContext;
  sector: string;
}) {
  if (!context)
    return (
      <section className="panel">
        <h2>What the business reported</h2>
        <p>
          Company filing research is not collected yet. Missing financial
          evidence is not treated as a healthy balance sheet.
        </p>
      </section>
    );
  const f = context.values;
  const revenue = context.periods.revenue;
  const cash = context.periods.cash;
  const link = sourceURL(revenue?.filing_url ?? cash?.filing_url ?? "");
  return (
    <section className="panel">
      <h2>What the business reported</h2>
      {f.quarter_revenue_yoy !== null && (
        <p>
          Quarterly revenue {f.quarter_revenue_yoy >= 0 ? "grew" : "fell"}{" "}
          {Math.abs(f.quarter_revenue_yoy * 100).toFixed(1)}% against the
          matched year-earlier quarter, ending {revenue?.end}.
        </p>
      )}
      {f.quarter_net_margin !== null && (
        <p>
          Net income was {(f.quarter_net_margin * 100).toFixed(1)}% of revenue
          in that same quarter.
        </p>
      )}
      {f.cash !== null && (
        <p>
          Reported cash: $
          {(f.cash / 1_000_000).toLocaleString("en-US", {
            maximumFractionDigits: 1,
          })}{" "}
          million at {cash?.end}.
        </p>
      )}
      {sector !== "Financials" && f.current_ratio !== null && (
        <p>
          Current assets were {f.current_ratio.toFixed(2)} times current
          liabilities at {context.periods.assets?.end}. This ratio alone does
          not establish solvency.
        </p>
      )}
      <p className="muted">
        Revenue growth and profits support the business case, but the stock may
        already price them in. Cash must be assessed alongside debt, cash burn,
        and financing access. Bank balance sheets require different measures.
      </p>
      {link && (
        <a href={link} target="_blank" rel="noopener noreferrer">
          Read the SEC filing summary
        </a>
      )}
      <p>
        <small>
          SEC company facts · filing dates have day precision · retrieved{" "}
          {new Date(context.retrieved_at).toLocaleString("en-US", {
            timeZone: "America/New_York",
          })}{" "}
          Eastern. Unmatched or unavailable periods are omitted.
        </small>
      </p>
    </section>
  );
}
