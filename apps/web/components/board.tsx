"use client";
import { useState } from "react";
import Link from "next/link";
import * as Dialog from "@radix-ui/react-dialog";
import { RequestScore } from "@/components/request-score";
import { Button } from "@/components/ui/button";
import { ContractDetails } from "@/components/contract-details";
import type { Security, Line, Side, Event } from "@/lib/types";
export function Board({
  companies,
  lines,
  events,
}: {
  companies: Security[];
  lines: Line[];
  events: Event[];
}) {
  const [selected, setSelected] = useState<{
    company: Security;
    line?: Line;
    side?: Side;
  } | null>(null);
  const [lineup, setLineup] = useState<
    { symbol: string; side: string; kind: string }[]
  >([]);
  const [sector, setSector] = useState("All sectors");
  const visible = companies.filter(
    (c) => sector === "All sectors" || c.sector === sector,
  );
  const sectors = [...new Set(companies.map((c) => c.sector))].sort();
  function open(company: Security, sideName: Side["side"], line?: Line) {
    const chosen =
      line ??
      lines.find((l) => l.symbol === company.symbol && l.kind === "Swing");
    setSelected({
      company,
      line: chosen,
      side: chosen?.sides.find(
        (s) =>
          s.side ===
          (chosen.kind === "Earnings Move" || chosen.kind === "IV Ramp"
            ? sideName === "BEAR" || sideName === "LESS"
              ? "LESS"
              : "MORE"
            : sideName === "LESS" || sideName === "BEAR"
              ? "BEAR"
              : "BULL"),
      ),
    });
  }
  return (
    <>
      <div className="toolbar">
        <label htmlFor="sector" className="muted">
          Browse
        </label>
        <select
          id="sector"
          value={sector}
          onChange={(e) => setSector(e.target.value)}
        >
          <option>All sectors</option>
          {sectors.map((s) => (
            <option key={s}>{s}</option>
          ))}
        </select>
        <span className="pill">{visible.length} matches on this page</span>
      </div>
      <div className="grid">
        {visible.map((c) => {
          const event =
            events.find(
              (e) =>
                e.symbol === c.symbol &&
                e.report_date >= new Date().toISOString().slice(0, 10),
            ) ??
            events
              .filter((e) => e.symbol === c.symbol)
              .sort((a, b) => b.report_date.localeCompare(a.report_date))[0];
          const stockLines = lines.filter((l) => l.symbol === c.symbol);
          return (
            <article className="card" key={c.symbol}>
              <div className="card-top">
                <h2>
                  <Link href={`/stock/${encodeURIComponent(c.symbol)}`}>
                    {c.symbol}
                  </Link>
                </h2>
                <span className="pill">{c.exchange}</span>
              </div>
              <p>{c.name}</p>
              <p className="muted">{c.sector}</p>
              {stockLines.find((l) => l.kind === "Swing")?.payload.metrics
                ?.vol_compression_ratio != null && (
                <p>
                  Volatility ratio{" "}
                  <strong>
                    {stockLines
                      .find((l) => l.kind === "Swing")
                      ?.payload.metrics?.vol_compression_ratio?.toFixed(2)}
                    ×
                  </strong>
                  <br />
                  <small>
                    Alpaca IEX · 10 vs. 60 sessions · not a move probability
                  </small>
                </p>
              )}
              <div className="badges">
                <span className="pill">
                  {event
                    ? `${event.report_date} · ${event.date_status}`
                    : "Calendar date unavailable"}
                </span>
                <span className="pill">
                  {stockLines.length
                    ? "Price research ready"
                    : "Open to request research"}
                </span>
              </div>
              <p className="muted">
                {stockLines.find((l) => l.kind === "Swing")?.payload.favored
                  ? `${stockLines.find((l) => l.kind === "Swing")?.payload.favored} price lean · model not validated`
                  : "Explore both sides of the case"}
              </p>
              <div className="sides">
                <Button className="bull" onClick={() => open(c, "BULL")}>
                  ↑ BULL
                </Button>
                <Button className="bear" onClick={() => open(c, "BEAR")}>
                  ↓ BEAR
                </Button>
              </div>
              <small>
                Identifiers: SEC · {new Date(c.as_of).toLocaleDateString()}
              </small>
            </article>
          );
        })}
      </div>
      {!visible.length && (
        <div className="notice">
          No matching companies. Search a ticker or part of a company name.
        </div>
      )}
      <section className="panel lineup">
        <h2>Your research lineup</h2>
        <p className="muted">
          Compare cases here. This session-only list places no orders and
          suggests no position size.
        </p>
        {lineup.length ? (
          lineup.map((item, i) => (
            <div
              className="row"
              key={`${item.symbol}:${item.kind}:${item.side}`}
            >
              <span>
                {item.symbol} · {item.kind} · {item.side}
              </span>
              <Button
                onClick={() =>
                  setLineup(lineup.filter((_, index) => index !== i))
                }
              >
                Remove
              </Button>
            </div>
          ))
        ) : (
          <p>Select a side on a company card to start.</p>
        )}
        {lineup.length > 3 && (
          <div className="notice">
            Several picks can move together. Review overlapping sectors and
            event dates.
          </div>
        )}
      </section>
      <Dialog.Root
        open={!!selected}
        onOpenChange={(open) => {
          if (!open) setSelected(null);
        }}
      >
        <Dialog.Portal>
          <Dialog.Overlay className="dialog-overlay" />
          <Dialog.Content className="dialog-content">
            <Dialog.Close asChild>
              <Button className="close" aria-label="Close research">
                ×
              </Button>
            </Dialog.Close>
            <Dialog.Title>
              {selected?.company.symbol} ·{" "}
              {selected?.side?.side ?? "Case research"}
            </Dialog.Title>
            <Dialog.Description className="muted">
              {selected?.company.name}. Review the case, the other side and the
              limits.
            </Dialog.Description>
            <div className="line-tabs">
              {lines
                .filter((l) => l.symbol === selected?.company.symbol)
                .map((l) => (
                  <Button
                    key={l.id}
                    onClick={() =>
                      selected &&
                      open(selected.company, selected.side?.side ?? "BULL", l)
                    }
                  >
                    {l.kind}
                  </Button>
                ))}
            </div>
            {selected?.side ? (
              <>
                <p>{selected.line?.payload.subtitle}</p>
                <div className="sides">
                  {selected.line?.sides.map((side) => (
                    <Button
                      key={side.id}
                      className={
                        side.side === "BULL" || side.side === "MORE"
                          ? "bull"
                          : "bear"
                      }
                      onClick={() => setSelected({ ...selected, side })}
                    >
                      {side.side}
                    </Button>
                  ))}
                </div>

                <div className="badges">
                  {selected.side.payload.badges.map((b) => (
                    <span className="pill" key={b}>
                      {b}
                    </span>
                  ))}
                </div>
                <h3>
                  {selected.side.payload.tier} ·{" "}
                  {selected.side.payload.sample_size} validated cases
                </h3>
                <ul>
                  {selected.side.payload.bullets.map((b) => (
                    <li key={b}>{b}</li>
                  ))}
                </ul>
                <h3>What could go wrong</h3>
                <ul>
                  {selected.side.payload.countercase.map((b) => (
                    <li key={b}>{b}</li>
                  ))}
                </ul>
                <section className="panel">
                  <h3>{selected.side.payload.trade.instrument}</h3>
                  <p>{selected.side.payload.trade.explanation}</p>
                  <ContractDetails trade={selected.side.payload.trade} />
                  {selected.side.payload.trade.entry !== null && (
                    <p>
                      Last close: $
                      {Number(selected.side.payload.trade.entry).toFixed(2)} ·
                      Stop context:{" "}
                      {selected.side.payload.trade.stop !== null
                        ? `$${Number(selected.side.payload.trade.stop).toFixed(2)}`
                        : "not available"}
                    </p>
                  )}
                  {selected.side.payload.trade.estimate && (
                    <>
                      <p>
                        Strike $
                        {selected.side.payload.trade.estimate.strike.toFixed(2)}{" "}
                        · expiry {selected.side.payload.trade.estimate.expiry}
                      </p>
                      <p>
                        Estimated paired debit $
                        {selected.side.payload.trade.estimate.debit_per_share.toFixed(
                          2,
                        )}{" "}
                        per share · one assumed standard pair $
                        {selected.side.payload.trade.estimate.estimated_one_standard_contract_cost.toFixed(
                          2,
                        )}
                      </p>
                      <p>
                        Expiry breakevens: $
                        {selected.side.payload.trade.estimate.lower_breakeven.toFixed(
                          2,
                        )}{" "}
                        / $
                        {selected.side.payload.trade.estimate.upper_breakeven.toFixed(
                          2,
                        )}
                      </p>
                      <small>
                        {selected.side.payload.trade.estimate.quote_kind}.{" "}
                        {
                          selected.side.payload.trade.estimate
                            .multiplier_assumption
                        }
                        . A pre-expiry exit has different economics.
                      </small>
                    </>
                  )}
                  <p>{selected.side.payload.trade.exit}</p>
                  {selected.side.payload.trade.missing.map((m) => (
                    <p className="muted" key={m}>
                      {m}
                    </p>
                  ))}
                  <small>
                    Data cutoff:{" "}
                    {new Date(selected.side.as_of).toLocaleString()}. Last close
                    is not a live entry quote.
                  </small>
                </section>
                <h3>When to review</h3>
                <p>{selected.side.payload.invalidation}</p>
                <Button
                  onClick={() => {
                    if (!selected.line || !selected.side) return;
                    const item = {
                      symbol: selected.company.symbol,
                      side: selected.side.side,
                      kind: selected.line.kind,
                    };
                    setLineup([
                      ...lineup.filter(
                        (x) =>
                          !(
                            x.symbol === item.symbol &&
                            x.kind === item.kind &&
                            x.side === item.side
                          ),
                      ),
                      item,
                    ]);
                    setSelected(null);
                  }}
                >
                  Add to research lineup
                </Button>
              </>
            ) : (
              <div className="notice">
                {selected && <RequestScore symbol={selected.company.symbol} />}
              </div>
            )}
            <p>
              <Link
                href={`/stock/${encodeURIComponent(selected?.company.symbol ?? "")}`}
              >
                Open full company research →
              </Link>
            </p>
          </Dialog.Content>
        </Dialog.Portal>
      </Dialog.Root>
    </>
  );
}
