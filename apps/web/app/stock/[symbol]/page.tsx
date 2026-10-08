import { formatAsOf } from "@/lib/time";
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
import { Fundamentals, type FinancialContext } from "@/components/fundamentals";
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
  const financial = await read<{ payload: FinancialContext }>(
    "market_observations",
    {
      symbol: `eq.${symbol}`,
      feed: "eq.sec_fundamentals",
      order: "retrieved_at.desc",
      limit: "1",
    },
  );
  const [storedBars, events, rawLines, sides, market, news, forums, coverage] =
    await Promise.all([
      read<Bar>("daily_bars", {
        symbol: `eq.${symbol}`,
        order: "session_date.desc",
        limit: "1000",
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
        feed: "in.(iex,finnhub_free)",
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
      read<{
        payload: {
          observations: {
            source: string;
            feed: string;
            observed_at: string;
            available_at: string;
            values: { c: number; t: string };
          }[];
        };
      }>("market_coverage", {
        symbol: `eq.${symbol}`,
        select: "payload",
        limit: "1",
      }),
    ]);
  const preferredBars = storedBars.filter((b) => b.source === "Nasdaq");
  const bars: Bar[] = storedBars.length
    ? (preferredBars.length ? preferredBars : storedBars).slice(0, 252)
    : [...(coverage[0]?.payload.observations ?? [])].reverse().map((o) => ({
        session_date: o.values.t.slice(0, 10),
        close: o.values.c,
        source: o.source,
        feed: o.feed,
        as_of: o.observed_at,
        available_at: o.available_at,
      }));
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
      <Fundamentals context={financial[0]?.payload} sector={company.sector} />
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
                <small>As of {formatAsOf(e.as_of)}</small>
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
          Verified directory as of {formatAsOf(company.as_of)}.
          {company.asset_type === "common_stock"
            ? " Exchange directory identifies this as common shares."
            : " Common-share classification is not confirmed; company research remains available."}
          {company.listing_metadata?.retrieved_at &&
            ` Listing checked ${new Date(company.listing_metadata.retrieved_at).toLocaleString("en-US", { timeZone: "America/New_York" })} Eastern.`}{" "}
          Current executable option quotes are separate from the delayed
          research snapshots.
        </p>
      </section>
    </>
  );
}
