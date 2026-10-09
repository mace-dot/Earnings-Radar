"use client";

import { useState } from "react";
import { Board } from "@/components/board";
import type { Event, Line, Security } from "@/lib/types";

export function ResearchSwitch({
  initial,
  earningsLabel,
  radar,
  earnings,
}: {
  initial: "radar" | "earnings";
  earningsLabel: string;
  radar: { companies: Security[]; lines: Line[]; events: Event[] };
  earnings: { companies: Security[]; lines: Line[]; events: Event[] };
}) {
  const [view, setView] = useState(initial);
  const current = view === "earnings" ? earnings : radar;
  const status =
    view === "radar" && radar.companies.length
      ? "Automatically researched setups"
      : earningsLabel;
  return (
    <>
      <p className="panel">
        <strong>{status}</strong>
      </p>
      <nav className="toolbar" aria-label="Research board views">
        <button
          className="button"
          type="button"
          aria-pressed={view === "radar"}
          onClick={() => setView("radar")}
        >
          Automatic research
        </button>
        <button
          className="button"
          type="button"
          aria-pressed={view === "earnings"}
          onClick={() => setView("earnings")}
        >
          {earningsLabel}
        </button>
      </nav>
      <Board
        companies={current.companies}
        lines={current.lines}
        events={current.events}
      />
    </>
  );
}
