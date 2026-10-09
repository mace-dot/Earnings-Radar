import { describe, expect, it } from "vitest";
import { crowdCopy, leanCopy, moveSizeCopy } from "./ticker-result";

describe("ticker result copy", () => {
  it("describes a quieter stock and a saved options move", () => {
    const lines = moveSizeCopy({
      compression: 0.5,
      volumeMultiple: 2,
      rangeMultiple: null,
      impliedMove: 0.08,
    });
    expect(lines[0]).toMatch(/quieter/);
    expect(lines.join(" ")).toMatch(/8\.0%/);
    expect(lines.join(" ")).not.toMatch(/\bwill\b/i);
    expect(lines.at(-1)).toMatch(/not a published chance/);
  });

  it("leaves the options move missing when nothing was saved", () => {
    const lines = moveSizeCopy({
      compression: null,
      volumeMultiple: null,
      rangeMultiple: null,
      impliedMove: null,
    });
    expect(lines.join(" ")).toMatch(/not available yet/);
  });

  it("states the lean without a profit percent", () => {
    const lines = leanCopy({
      favored: "BULL",
      return20: -0.04,
      sampleSize: 12,
    });
    expect(lines[0]).toMatch(/lean is up/);
    expect(lines.join(" ")).toMatch(/fell about 4\.0%/);
    expect(lines.join(" ")).toMatch(/No chance of profit/);
    expect(lines.join(" ")).not.toMatch(/\bwill\b/i);
  });

  it("keeps a missing crowd missing and says Reddit is not connected", () => {
    const lines = crowdCopy({ bullPosts: 0, bearPosts: 0, forumCount: 0 });
    expect(lines.join(" ")).toMatch(/not treated as neutral/);
    expect(lines.join(" ")).toMatch(/Reddit is not connected/);
  });
});
