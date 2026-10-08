import { test, expect } from "@playwright/test";
test("search, both-sided case, price history and lineup", async ({ page }) => {
  await page.goto("/");
  await expect(
    page.getByRole("heading", { name: /Find the setup/ }),
  ).toBeVisible();
  await page
    .getByRole("textbox", { name: "Company name or ticker" })
    .fill("AAPL");
  await page.getByRole("button", { name: "Find company" }).click();
  await expect(
    page.getByRole("link", { name: "AAPL", exact: true }),
  ).toBeVisible();
  await page.getByRole("button", { name: "↑ BULL", exact: true }).click();
  await expect(page.getByRole("dialog")).toBeVisible();
  await expect(
    page.getByRole("heading", { name: "What could go wrong" }),
  ).toBeVisible();
  await expect(
    page.getByRole("heading", {
      name: /^(Shares with stop|Long call research)$/,
    }),
  ).toBeVisible();
  await page.getByRole("button", { name: "Add to research lineup" }).click();
  await expect(
    page.getByText("AAPL · Swing · BULL", { exact: true }),
  ).toBeVisible();
  await page.getByRole("link", { name: "AAPL", exact: true }).click();
  await expect(
    page.getByRole("img", { name: /Closing price history/ }),
  ).toBeVisible();
  await expect(
    page.getByText(/Daily history, not a live entry quote/),
  ).toBeVisible();
});

test("Micron has distinct sides, source context and a refreshed observed price", async ({
  page,
}) => {
  await page.goto("/stock/MU");
  await expect(
    page.getByRole("heading", { name: "What a sampled crowd says" }),
  ).toBeVisible();
  await expect(
    page.getByRole("heading", { name: "Observed market price" }),
  ).toBeVisible();
  await page.getByRole("button", { name: "↑ BULL", exact: true }).click();
  const bull = await page
    .getByRole("dialog")
    .locator("ul")
    .first()
    .textContent();
  await page
    .getByRole("dialog")
    .getByRole("button", { name: "BEAR", exact: true })
    .click();
  const bear = await page
    .getByRole("dialog")
    .locator("ul")
    .first()
    .textContent();
  expect(bull).not.toEqual(bear);
  await page
    .getByRole("button", { name: "Earnings Move", exact: true })
    .click();
  await expect(
    page.getByRole("dialog").getByRole("button", { name: "MORE", exact: true }),
  ).toBeVisible();
  await page
    .getByRole("dialog")
    .getByRole("button", { name: "MORE", exact: true })
    .click();
  await expect(
    page.getByRole("heading", { name: "Long straddle estimate" }),
  ).toBeVisible();
});

test("live-price relay rejects other origins and returns a real observed trade", async ({
  request,
  baseURL,
}) => {
  const denied = await request.post("/api/market", {
    headers: { Origin: "https://untrusted.example" },
    data: { symbol: "MU" },
  });
  expect(denied.status()).toBe(403);
  const response = await request.post("/api/market", {
    headers: { Origin: new URL(baseURL ?? "http://127.0.0.1:3100").origin },
    data: { symbol: "MU" },
  });
  expect(response.status()).toBe(200);
  const quote = await response.json();
  expect(quote.price).toBeGreaterThan(0);
  expect(quote.feed).toBe("Finnhub");
  expect(Number.isFinite(Date.parse(quote.as_of))).toBe(true);
});

test("published option research has concrete economics and a pending public record", async ({
  page,
}) => {
  await page.goto("/picks");
  const pick = page.locator("article").first();
  await expect(
    pick.getByText("Unvalidated paper research · no probability"),
  ).toBeVisible();
  await expect(pick.getByText(/One assumed standard contract:/)).toBeVisible();
  await expect(pick.getByText(/Expiration breakeven:/)).toBeVisible();
  await expect(
    pick.getByRole("heading", { name: "What could go wrong" }),
  ).toBeVisible();
  const symbol = await pick.getByRole("link").first().textContent();
  await page.goto("/track-record");
  const row = page
    .locator(".row")
    .filter({ hasText: symbol ?? "" })
    .first();
  await expect(row).toBeVisible();
  await expect(row.getByText("Pending evaluation")).toBeVisible();
  await row.getByText("Evaluation details").click();
  await expect(row.getByText(/Review horizon:/)).toBeVisible();
});
