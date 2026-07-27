import { test, expect } from "@playwright/test";

/**
 * Dashboard smoke — Stage 1.
 *
 * Loads the root page and asserts that at least one KPI card label is
 * present. The intent is "the build did not crash"; we deliberately do
 * not assert specific metric values because those are still theatrical
 * in Stage 1. Real value assertions arrive with Stage 4's metrics swap.
 */
test("dashboard loads and renders at least one KPI card", async ({ page }) => {
    const consoleErrors: string[] = [];
    page.on("console", (msg) => {
        if (msg.type() === "error") consoleErrors.push(msg.text());
    });

    await page.goto("/", { waitUntil: "domcontentloaded" });

    await expect(page).toHaveTitle(/.+/);

    // Heuristic: every dashboard page has at least one heading with a KPI-ish
    // word. Loose-matching keeps the test useful through Stage-4 redesigns.
    const heading = page.getByRole("heading", { name: /throughput|robots|stages|kpi|dashboard/i }).first();
    await expect(heading).toBeVisible({ timeout: 10_000 });

    expect(consoleErrors, `console errors detected: ${consoleErrors.join("\n")}`).toHaveLength(0);
});
