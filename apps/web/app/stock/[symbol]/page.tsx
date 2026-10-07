import Link from "next/link";
import { notFound } from "next/navigation";
import { read } from "@/lib/db";
import type { Security, Bar, Event, Line, Side } from "@/lib/types";
import { PriceChart } from "@/components/chart";
import { RequestScore } from "@/components/request-score";
import {
  Context,
  type Market,
  type News,
  type Forum,
} from "@/components/context";
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
  const [bars, events, rawLines, sides, market, news, forums] =
    await Promise.all([
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
        limit: "20",
      }),
      read<Side>("line_sides", {
        id: `like.${symbol}:*`,
        order: "as_of.desc",
        limit: "1000",
      }),
      read<Market>("market_observations", {
        symbol: `eq.${symbol}`,
        order: "retrieved_at.desc",
        limit: "1",
      }),
      read<News>("news_items", {
        symbol: `eq.${symbol}`,
        order: "published_at.desc",
        limit: "12",
      }),
      read<Forum>("forum_posts", {
        symbol: `eq.${symbol}`,
        order: "published_at.desc",
        limit: "30",
      }),
    ]);
  const seen = new Set<string>();
  const lines = rawLines
    .filter((l) => {
      if (seen.has(l.kind)) return false;
      seen.add(l.kind);
      return [
        "Swing",
        "Run-Up",
        "Earnings Move",
        "Direction",
        "IV Ramp",
        "Drift",
      ].includes(l.kind);
    })
    .map((l) => ({
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
      {(!lines.length ||
        !market.length ||
        Date.now() - Date.parse(market[0].retrieved_at) > 1800000) && (
        <RequestScore symbol={symbol} />
      )}
      <Context symbol={symbol} market={market} news={news} forums={forums} />
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
