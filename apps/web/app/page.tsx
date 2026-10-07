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
    const today = new Date().toISOString().slice(0, 10);
    const weekEnd = new Date(Date.now() + 7 * 86400000)
      .toISOString()
      .slice(0, 10);
    const weekly = term
      ? []
      : await read<Event>("earnings_events", {
          and: `(report_date.gte.${today},report_date.lte.${weekEnd})`,
          order: "report_date.asc",
          limit: "60",
        });
    const weeklySymbols = [...new Set(weekly.map((e) => e.symbol))].join(",");
    companies = await read<Security>("securities", {
      order: "symbol.asc",
      limit: "60",
      ...(term
        ? { or: `(symbol.ilike.*${term}*,name.ilike.*${term}*)` }
        : { ...(weeklySymbols ? { symbol: `in.(${weeklySymbols})` } : {}) }),
    });
    const symbols = companies.map((c) => c.symbol).join(",");
    if (symbols) {
      const [rawLines, sides, calendar] = await Promise.all([
        read<Line>("lines", {
          symbol: `in.(${symbols})`,
          order: "as_of.desc",
          limit: "500",
        }),
        read<Side>("line_sides", {
          or: `(${companies.map((c) => `id.like.${c.symbol}:*`).join(",")})`,
          order: "as_of.desc",
          limit: "1000",
        }),
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
          if (
            ![
              "Swing",
              "Run-Up",
              "Earnings Move",
              "Direction",
              "IV Ramp",
              "Drift",
            ].includes(l.kind) ||
            seen.has(key)
          )
            return false;
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
          <strong>Reporting this week · automatic calendar coverage</strong>
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
