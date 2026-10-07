import { describe, it, expect } from "vitest";
import { premiumExposure } from "./risk";
describe("approved risk context", () => {
  it("does not invent position sizing", () => {
    expect(premiumExposure(2, 100)).toEqual({
      oneContract: 200,
      quantity: null,
    });
  });
  it("uses an explicitly provided budget", () => {
    expect(premiumExposure(2, 100, 20000).quantity).toBe(1);
  });
  it("rejects invalid contract values", () => {
    expect(() => premiumExposure(-1, 100)).toThrow();
  });
});
