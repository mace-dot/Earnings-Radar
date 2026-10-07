import Link from "next/link";
import { notFound } from "next/navigation";
import { read } from "@/lib/db";
import type { Security, Bar, Event, Line, Side } from "@/lib/types";
import { PriceChart } from "@/components/chart";
import { Board } from "@/components/board";
export default async function Stock({
  params,
}: {
  params: Promise<{ symbol: string }>;
}) {
  const { symbol: raw } = await params;
  const symbol = raw.toUpperCase();
  if (!/^[A-Z0-9][A-Z0-9.-]{0,14}$/.test(symbol)) notFound();
  const companies = await read<Security>("securities", {
    symbol: `eq.${symbol}`,
    limit: "1",
  });
  if (!companies.length) notFound();
  const company = companies[0];
  const [bars, events, rawLines, sides] = await Promise.all([
    read<Bar>("daily_bars", {
      symbol: `eq.${symbol}`,
      order: "session_date.desc",
      limit: "252",
    }),
    read<Event>("earnings_events", {
      symbol: `eq.${symbol}`,
      order: "report_date.desc",
      limit: "12",
    }),
    read<Line>("lines", {
      symbol: `eq.${symbol}`,
      order: "as_of.desc",
      limit: "5",
    }),
    read<Side>("line_sides", { order: "as_of.desc", limit: "1000" }),
  ]);
  const lines = rawLines.map((l) => ({
    ...l,
    sides: sides.filter((s) => s.id.startsWith(`${l.id}:`)),
  }));
  return (
    <>
      <Link href="/">← Board</Link>
      <p className="eyebrow">COMPANY RESEARCH</p>
      <h1>
        {symbol} <span className="muted">{company.name}</span>
      </h1>
      <p>
        {company.sector} · {company.exchange}
      </p>
      <div className="two-column">
        <section className="panel">
          <h2>What the price has done</h2>
          <PriceChart bars={[...bars].reverse()} />
        </section>
        <section className="panel">
          <h2>Report dates</h2>
          {events.length ? (
            events.map((e) => (
              <div className="row" key={e.id}>
                <span>
                  {e.report_date}
                  <br />
                  <small>
                    {e.timing} · {e.date_status}
                  </small>
                </span>
                <small>As of {new Date(e.as_of).toLocaleDateString()}</small>
              </div>
            ))
          ) : (
            <p className="muted">
              No earnings calendar connected yet. Filing dates are not used as
              upcoming report dates.
            </p>
          )}
        </section>
      </div>
      <h2>Explore a case</h2>
      <Board companies={companies} lines={lines} events={events} />
      <section className="panel">
        <h2>Company identity</h2>
        <p>
          Directory source:{" "}
          <a
            href="https://www.sec.gov/edgar/search/"
            target="_blank"
            rel="noopener noreferrer"
          >
            SEC company search ↗
          </a>
        </p>
        <p className="muted">
          Verified directory as of {new Date(company.as_of).toLocaleString()}.
          Asset type: {company.asset_type}. Business fundamentals, estimates and
          executable contract quotes still need collection.
        </p>
      </section>
    </>
  );
}
