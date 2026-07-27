/**
 * Smoke test — Stage 1.
 *
 * Mounts a representative page export under JSDOM with the WebSocket and
 * fetch APIs stubbed so the test never reaches the network. The intent is
 * to catch obvious render-time crashes (broken imports, missing providers,
 * client-only hooks misused) before they reach CI integration tests.
 *
 * NOTE: This file presumes Jest + @testing-library are installed. The
 * Stage-1 acceptance criteria specify `npm test -- --watchAll=false` runs
 * green; if Jest is not yet wired in package.json, this test will be
 * skipped by CI until Stage 2 lands the test runner config. See KB_TASK_LOG.
 */
import React from "react";
import { render } from "@testing-library/react";

// Stub network so the page is never tempted to reach out at test time.
beforeAll(() => {
    // @ts-expect-error — JSDOM lacks WebSocket; we only need the constructor.
    global.WebSocket = class {
        constructor() { /* noop */ }
        addEventListener() { /* noop */ }
        send() { /* noop */ }
        close() { /* noop */ }
    };
    global.fetch = jest.fn(() =>
        Promise.resolve({
            ok: true,
            status: 200,
            json: () => Promise.resolve({}),
        })
    ) as unknown as typeof fetch;
});

describe("app shell smoke", () => {
    it("renders a Navigation-only landmark without crashing", () => {
        const Navigation = require("@/components/Navigation").default;
        const { container } = render(<Navigation />);
        expect(container).toBeTruthy();
    });
});
