import { it, expect } from "vitest";
import { sameOrigin } from "./same-origin";
it("matches the routed host when Next normalizes the internal URL", () => {
  expect(
    sameOrigin(
      "http://127.0.0.1:3100",
      "http://localhost:3100/api/market",
      "127.0.0.1:3100",
    ),
  ).toBe(true);
  expect(
    sameOrigin(
      "https://evil.example",
      "https://radar.vercel.app/api/market",
      "radar.vercel.app",
    ),
  ).toBe(false);
  expect(
    sameOrigin(null, "https://radar.vercel.app/api/market", "radar.vercel.app"),
  ).toBe(false);
});
