import { describe, it, expect } from "vitest";
import {
  historyAuthorized,
  historyRequest,
  historySignature,
} from "./history-relay";
describe("bounded worker history relay", () => {
  it("authenticates exact requests within a narrow time window", () => {
    const key = "fixture-only-key",
      timestamp = "1791475200",
      body = '{"symbol":"FIXTURE"}';
    const signature = historySignature(key, timestamp, body),
      now = Number(timestamp) * 1000;
    expect(historyAuthorized(key, timestamp, signature, body, now)).toBe(true);
    expect(historyAuthorized(key, timestamp, signature, body + " ", now)).toBe(
      false,
    );
    expect(
      historyAuthorized(key, timestamp, signature, body, now + 121000),
    ).toBe(false);
    expect(historyAuthorized("", timestamp, signature, body, now)).toBe(false);
    expect(historyAuthorized(key, timestamp, "bad", body, now)).toBe(false);
  });
  it("rejects host injection, invalid dates and unbounded history", () => {
    expect(
      historyRequest({ symbol: "MU", start: "2026-01-01", end: "2026-10-08" }),
    ).not.toBeNull();
    for (const data of [
      { symbol: "../../evil", start: "2026-01-01", end: "2026-10-08" },
      { symbol: "MU", start: "2020-01-01", end: "2026-10-08" },
      { symbol: "MU", start: "2026-02-30", end: "2026-10-08" },
      { symbol: "MU", start: "2026-10-08", end: "2026-01-01" },
    ])
      expect(historyRequest(data)).toBeNull();
  });
});
