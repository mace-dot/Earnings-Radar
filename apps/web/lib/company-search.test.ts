import { describe, expect, it } from "vitest";
import { matchesCompany, narrowestWord } from "./company-search";

describe("company search", () => {
  const astera = { symbol: "ALAB", name: "Astera Labs, Inc." };

  it("matches a multi-word name even though the ticker is different", () => {
    expect(matchesCompany(astera, "astera labs")).toBe(true);
    expect(matchesCompany(astera, "ALAB")).toBe(true);
    expect(narrowestWord("astera labs")).toBe("astera");
  });

  it("does not match a company that only shares one word", () => {
    expect(
      matchesCompany(
        { symbol: "EBC", name: "Eastern Bankshares, Inc." },
        "astera labs",
      ),
    ).toBe(false);
  });
});
