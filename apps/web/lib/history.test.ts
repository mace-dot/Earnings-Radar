import { expect, it } from "vitest";
import { selectHistory } from "./history";
import type { Bar } from "./types";
function fixture(count: number, source: string, feed: string): Bar[] {
  return Array.from({ length: count }, (_, index) => ({
    session_date: new Date(Date.UTC(2026, 6, index + 1))
      .toISOString()
      .slice(0, 10),
    close: 100 + index,
    source,
    feed,
    as_of: "2026-10-07T20:00:00Z",
    available_at: "2026-10-08T12:00:00Z",
  }));
}
it("shows adjusted coverage despite older stored history", () => {
  const result = selectHistory(
    fixture(83, "Nasdaq", "nasdaq_history"),
    fixture(61, "Massive", "massive_daily_adjusted"),
  );
  expect(result).toHaveLength(61);
  expect(result.every((bar) => bar.source === "Massive")).toBe(true);
});
it("keeps a complete series during partial bootstrap without mixing feeds", () => {
  const result = selectHistory(
    fixture(83, "Nasdaq", "nasdaq_history"),
    fixture(3, "Massive", "massive_daily_adjusted"),
  );
  expect(result).toHaveLength(83);
  expect(result.every((bar) => bar.source === "Nasdaq")).toBe(true);
});
it("deduplicates sessions and preserves chronological order", () => {
  const bars = fixture(61, "Massive", "massive_daily_adjusted");
  const result = selectHistory([...bars].reverse(), bars);
  expect(result).toHaveLength(61);
  expect(result[0].session_date < result[60].session_date).toBe(true);
});
