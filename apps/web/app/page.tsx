import { marketDate } from "@/lib/time";
import { read } from "@/lib/db";
import type { Security, Line, Side, Event, Pick } from "@/lib/types";
import { chooseBoard } from "@/lib/board-selection";
import { ResearchSwitch } from "@/components/research-switch";

function pack(
  symbols: string[],
  companies: Security[],
  lines: Line[],
  events: Event[],
) {
  const wanted = new Set(symbols);
  const reportDate = new Map(
    events.map((event) => [event.symbol, event.report_date]),
  );
  return {
    companies: companies
      .filter((company) => wanted.has(company.symbol))
      .sort(
        (a, b) =>
          (reportDate.get(a.symbol) ?? "9999-99-99").localeCompare(
            reportDate.get(b.symbol) ?? "9999-99-99",
          ) || a.symbol.localeCompare(b.symbol),
      ),
    lines: lines.filter((line) => wanted.has(line.symbol)),
    events: events.filter((event) => wanted.has(event.symbol)),
  };
}

export default async function Page({
  searchParams,
}: {
  searchParams: Promise<{ q?: string; view?: string }>;
}) {
  const { q = "", view = "radar" } = await searchParams;
  const term = q
    .trim()
    .replace(/[^a-zA-Z0-9 .-]/g, "")
    .slice(0, 60);
  let companies: Security[] = [];
  let lines: Line[] = [];
  let events: Event[] = [];
  let unavailable = false;
  let choice = chooseBoard([], [], marketDate(), view);
  let pickSymbols: string[] = [];
  try {
    const today = marketDate();
    if (term) {
      companies = await read<Security>("securities", {
        order: "symbol.asc",
        limit: "60",
        or: `(symbol.ilike.*${term}*,name.ilike.*${term}*)`,
      });
    } else {
      const [calendar, published] = await Promise.all([
        read<Event>("earnings_events", {
          report_date: `gte.${today}`,
          order: "report_date.asc",
          limit: "80",
        }),
        read<Pick>("picks", {
          order: "as_of.desc",
          expires_at: `gt.${new Date().toISOString()}`,
          limit: "60",
        }),
      ]);
      choice = chooseBoard(calendar, published, today, view);
      pickSymbols = [...new Set(published.map((pick) => pick.symbol))];
      const symbols = [
        ...new Set([
          ...choice.symbols,
          ...published.map((pick) => pick.symbol),
        ]),
      ];
      const earningsSymbols = [
        ...new Set(
          calendar
            .filter((event) => event.report_date >= today)
            .slice(0, 60)
            .map((event) => event.symbol),
        ),
      ];
      const boardSymbols = [...new Set([...symbols, ...earningsSymbols])].slice(
        0,
        80,
      );
      if (boardSymbols.length) {
        companies = await read<Security>("securities", {
          order: "symbol.asc",
          limit: "80",
          symbol: `in.(${boardSymbols.join(",")})`,
        });
      }
      events = calendar;
    }
    const symbols = companies.map((company) => company.symbol).join(",");
    if (symbols) {
      const [rawLines, sides, calendar] = await Promise.all([
        read<Line>("lines", {
          symbol: `in.(${symbols})`,
          order: "as_of.desc",
          limit: "400",
        }),
        read<Side>("line_sides", {
          or: `(${companies.map((company) => `id.like.${company.symbol}:*`).join(",")})`,
          order: "as_of.desc",
          limit: "800",
        }),
        term
          ? read<Event>("earnings_events", {
              symbol: `in.(${symbols})`,
              order: "report_date.asc",
              limit: "100",
            })
          : Promise.resolve(events),
      ]);
      const seen = new Set<string>();
      lines = rawLines
        .filter((line) => {
          const key = `${line.symbol}:${line.kind}`;
          if (
            ![
              "Swing",
              "Run-Up",
              "Earnings Move",
              "Direction",
              "IV Ramp",
              "Drift",
            ].includes(line.kind) ||
            seen.has(key)
          )
            return false;
          seen.add(key);
          return true;
        })
        .map((line) => ({
          ...line,
          sides: sides.filter((side) => side.id.startsWith(`${line.id}:`)),
        }));
      events = calendar;
    }
  } catch {
    unavailable = true;
  }
  const earningsSymbols = [
    ...new Set(
      events
        .filter((event) => event.report_date >= marketDate())
        .map((event) => event.symbol),
    ),
  ];
  const radarSymbols = pickSymbols.length ? pickSymbols : choice.symbols;
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
          <strong>Before earnings · Earnings reaction · After earnings</strong>
          <p className="muted">Volatility · Longer swing</p>
        </div>
      </section>
      <form className="toolbar" role="search">
        <input type="hidden" name="view" value={view} />
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
      {term ? (
        <ResearchSwitch
          initial="earnings"
          earningsLabel="Search results"
          radar={{ companies, lines, events }}
          earnings={{ companies, lines, events }}
        />
      ) : (
        <ResearchSwitch
          initial={choice.mode}
          earningsLabel={choice.earningsLabel}
          radar={pack(radarSymbols, companies, lines, events)}
          earnings={pack(earningsSymbols, companies, lines, events)}
        />
      )}
    </>
  );
}
