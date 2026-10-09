import { describe, expect, it } from "vitest";
import { chooseBoard } from "./board-selection";

const today = "2026-10-09";

describe("chooseBoard", () => {
  it("shows the next saved reports when nothing reports this week", () => {
    const choice = chooseBoard(
      [
        { symbol: "NVDA", report_date: "2026-11-17" },
        { symbol: "OLD", report_date: "2026-09-01" },
      ],
      [{ symbol: "AAPL" }],
      today,
      "earnings",
    );
    expect(choice.calendarConnected).toBe(true);
    expect(choice.earningsLabel).toBe("Next saved reports");
    expect(choice.symbols).toEqual(["NVDA"]);
  });

  it("keeps researched names on the automatic board", () => {
    const choice = chooseBoard(
      [{ symbol: "NVDA", report_date: "2026-10-12" }],
      [{ symbol: "AAPL" }],
      today,
      "radar",
    );
    expect(choice.mode).toBe("radar");
    expect(choice.symbols).toEqual(["AAPL"]);
    expect(choice.earningsLabel).toBe("Earnings this week");
  });
});
