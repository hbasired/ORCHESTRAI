import { defineConfig, devices } from "@playwright/test";

/**
 * Playwright smoke config — Stage 1.
 *
 * Runs against a locally-served Next.js dev build on port 3000. The test
 * fleet is deliberately small — one Chromium spec — because the goal at
 * this stage is "page renders, no console errors", not coverage. Stage 12
 * will expand into the operator-override flow once the WebSocket pipe is
 * real instead of mocked.
 */
export default defineConfig({
    testDir: "./e2e",
    timeout: 30_000,
    fullyParallel: true,
    forbidOnly: !!process.env.CI,
    retries: process.env.CI ? 1 : 0,
    workers: process.env.CI ? 1 : undefined,
    reporter: process.env.CI ? "github" : "list",
    use: {
        baseURL: process.env.PLAYWRIGHT_BASE_URL ?? "http://localhost:3000",
        trace: "on-first-retry",
    },
    projects: [
        {
            name: "chromium",
            use: { ...devices["Desktop Chrome"] },
        },
    ],
    webServer: process.env.PLAYWRIGHT_SKIP_WEBSERVER
        ? undefined
        : {
              command: "npm run dev",
              url: "http://localhost:3000",
              timeout: 120_000,
              reuseExistingServer: !process.env.CI,
          },
});
