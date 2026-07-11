import { defineConfig, devices } from "@playwright/test";

const baseURL = process.env.NOVISCOPE_E2E_BASE_URL;

if (!baseURL) {
  throw new Error("NOVISCOPE_E2E_BASE_URL must point to a running NoviScope Web instance");
}

export default defineConfig({
  testDir: "./e2e",
  outputDir: "../.omo/evidence/compact-canvas-workbench/test-results",
  fullyParallel: false,
  workers: 1,
  timeout: 45_000,
  use: {
    baseURL,
    trace: "retain-on-failure",
    screenshot: "only-on-failure",
  },
  projects: [
    {
      name: "mobile",
      use: { ...devices["Desktop Chrome"], viewport: { width: 390, height: 844 } },
    },
    {
      name: "tablet",
      use: { ...devices["Desktop Chrome"], viewport: { width: 768, height: 1024 } },
    },
    {
      name: "desktop",
      use: { ...devices["Desktop Chrome"], viewport: { width: 1440, height: 1000 } },
    },
  ],
});
