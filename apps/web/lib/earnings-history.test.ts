import { describe, expect, it } from "vitest";
import { describeSurprise } from "./earnings-history";

describe("past earnings wording", () => {
  it("keeps a missing estimate missing", () => {
    expect(
      describeSurprise({
        period: "2026-06-30",
        as_of: "2026-10-08T00:00:00Z",
        payload: {
          reported_date: "2026-07-30",
          reported_eps: 1.25,
          estimated_eps: null,
        },
      }),
    ).toContain("No estimate was included");
  });

  it("describes a past report that came in above the estimate", () => {
    expect(
      describeSurprise({
        period: "2026-06-30",
        as_of: "2026-10-08T00:00:00Z",
        payload: {
          reported_date: "2026-07-30",
          reported_eps: 1.4,
          estimated_eps: 1.1,
        },
      }),
    ).toContain("above the 1.1 estimate");
  });
});
