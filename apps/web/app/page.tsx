import { read } from "@/lib/db";
import type { Security, Line, Side, Event } from "@/lib/types";
import { Board } from "@/components/board";
export default async function Page({
  searchParams,
}: {
  searchParams: Promise<{ q?: string }>;
}) {
  const { q = "" } = await searchParams;
  const term = q
    .trim()
    .replace(/[^a-zA-Z0-9 .-]/g, "")
    .slice(0, 60);
  let companies: Security[] = [],
    lines: Line[] = [],
    events: Event[] = [],
    unavailable = false;
  try {
    companies = await read<Security>("securities", {
      order: "symbol.asc",
      limit: "60",
      ...(term
        ? { or: `(symbol.ilike.*${term}*,name.ilike.*${term}*)` }
        : { symbol: "in.(AAPL,MSFT,NVDA,AMZN,META,GOOGL,TSLA,JPM,XOM,SPY)" }),
    });
    const symbols = companies.map((c) => c.symbol).join(",");
    if (symbols) {
      const [rawLines, sides, calendar] = await Promise.all([
        read<Line>("lines", {
          symbol: `in.(${symbols})`,
          order: "as_of.desc",
          limit: "500",
        }),
        read<Side>("line_sides", { order: "as_of.desc", limit: "1000" }),
        read<Event>("earnings_events", {
          symbol: `in.(${symbols})`,
          order: "report_date.asc",
          limit: "100",
        }),
      ]);
      const seen = new Set<string>();
      lines = rawLines
        .filter((l) => {
          const key = `${l.symbol}:${l.kind}`;
          if (seen.has(key)) return false;
          seen.add(key);
          return true;
        })
        .map((l) => ({
          ...l,
          sides: sides.filter((s) => s.id.startsWith(`${l.id}:`)),
        }));
      events = calendar;
    }
  } catch {
    unavailable = true;
  }
  return (
    <>
      <section className="hero">
        <div>
          <p className="eyebrow">YOUR EARNINGS PLAYBOOK</p>
          <h1>
            Find the setup.
            <br />
            Understand the risk.
          </h1>
          <p className="muted">
            Choose a company. Explore both sides. See the evidence in plain
            English.
          </p>
        </div>
        <div className="panel">
          <strong>Five ways to study a move</strong>
          <p className="muted">
            Before earnings · Earnings reaction · After earnings
            <br />
            Volatility · Longer swing
          </p>
        </div>
      </section>
      <form className="toolbar" role="search">
        <label className="sr-only" htmlFor="search">
          Company name or ticker
        </label>
        <input
          id="search"
          name="q"
          defaultValue={q}
          placeholder="Search any company or ticker — Apple, AAPL…"
        />
        <button className="button" type="submit">
          Find company
        </button>
      </form>
      {unavailable && (
        <div className="notice">
          The database could not be read. Cached research is temporarily
          unavailable; no data is invented.
        </div>
      )}
      <Board companies={companies} lines={lines} events={events} />
    </>
  );
}
