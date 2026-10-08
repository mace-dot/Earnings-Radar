import { describe, it, expect } from "vitest";
import { formatAsOf, marketDate } from "./time";
describe("Eastern source times", () => {
  it("keeps the exchange date before UTC midnight and handles DST", () => {
    expect(marketDate(new Date("2026-10-08T00:30:00Z"))).toBe("2026-10-07");
    expect(formatAsOf("2026-10-08T13:47:00Z")).toContain("9:47:00 AM Eastern");
    expect(formatAsOf("2026-12-07T15:30:00Z")).toContain("10:30:00 AM Eastern");
    expect(formatAsOf("invalid")).toBe("Time unavailable");
  });
});
