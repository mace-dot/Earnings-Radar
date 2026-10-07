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
    page.getByRole("heading", { name: "Shares with stop" }),
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
