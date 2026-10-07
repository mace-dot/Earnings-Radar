import { it, expect } from "vitest";
import { sourceURL } from "./source-url";
it("allows credible configured sources and rejects unsafe forum links", () => {
  expect(sourceURL("https://www.reuters.com/business/example")).not.toBeNull();
  expect(sourceURL("javascript:alert(1)")).toBeNull();
  expect(sourceURL("https://reuters.com.evil.example/foo")).toBeNull();
  expect(sourceURL("https://user:password@reuters.com/foo")).toBeNull();
});
