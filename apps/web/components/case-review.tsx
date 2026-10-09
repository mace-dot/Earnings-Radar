"use client";

import { useState } from "react";
import * as Dialog from "@radix-ui/react-dialog";
import { formatAsOf } from "@/lib/time";
import { Button } from "@/components/ui/button";
import { ContractDetails } from "@/components/contract-details";
import { RequestScore } from "@/components/request-score";
import type { Line, Security, Side } from "@/lib/types";

function sideFor(line: Line | undefined, sideName: Side["side"]) {
  return line?.sides.find(
    (side) =>
      side.side ===
      (line.kind === "Earnings Move" || line.kind === "IV Ramp"
        ? sideName === "BEAR" || sideName === "LESS"
          ? "LESS"
          : "MORE"
        : sideName === "LESS" || sideName === "BEAR"
          ? "BEAR"
          : "BULL"),
  );
}

export function CaseReview({
  company,
  lines,
}: {
  company: Security;
  lines: Line[];
}) {
  const [selected, setSelected] = useState<{ line?: Line; side?: Side } | null>(
    null,
  );
  function open(sideName: Side["side"], line?: Line) {
    const chosen = line ?? lines.find((item) => item.kind === "Swing");
    setSelected({ line: chosen, side: sideFor(chosen, sideName) });
  }
  return (
    <section className="panel">
      <h2>Open the case</h2>
      <p className="muted">
        Read both sides. This is paper research, and it places no order.
      </p>
      <div className="sides">
        <Button className="bull" onClick={() => open("BULL")}>
          ↑ BULL
        </Button>
        <Button className="bear" onClick={() => open("BEAR")}>
          ↓ BEAR
        </Button>
      </div>
      <Dialog.Root
        open={!!selected}
        onOpenChange={(next) => {
          if (!next) setSelected(null);
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
              {company.symbol} · {selected?.side?.side ?? "Case research"}
            </Dialog.Title>
            <Dialog.Description className="muted">
              {company.name}. Review the case, the other side, and the limits.
            </Dialog.Description>
            <div className="line-tabs">
              {lines.map((line) => (
                <Button
                  key={line.id}
                  onClick={() => open(selected?.side?.side ?? "BULL", line)}
                >
                  {line.kind}
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
                <h3>
                  {selected.side.payload.tier} ·{" "}
                  {selected.side.payload.sample_size} validated cases
                </h3>
                <p className="muted">
                  No chance of profit is published for this case.
                </p>
                <ul>
                  {selected.side.payload.bullets.map((item) => (
                    <li key={item}>{item}</li>
                  ))}
                </ul>
                <h3>What could go wrong</h3>
                <ul>
                  {selected.side.payload.countercase.map((item) => (
                    <li key={item}>{item}</li>
                  ))}
                </ul>
                <section className="panel">
                  <h3>{selected.side.payload.trade.instrument}</h3>
                  <p>{selected.side.payload.trade.explanation}</p>
                  <ContractDetails trade={selected.side.payload.trade} />
                  <p>{selected.side.payload.trade.exit}</p>
                  <small>
                    Data cutoff: {formatAsOf(selected.side.as_of)}. Last close
                    is not a live entry quote.
                  </small>
                </section>
                <h3>When to review</h3>
                <p>{selected.side.payload.invalidation}</p>
              </>
            ) : (
              <div className="notice">
                <RequestScore symbol={company.symbol} />
              </div>
            )}
          </Dialog.Content>
        </Dialog.Portal>
      </Dialog.Root>
    </section>
  );
}
