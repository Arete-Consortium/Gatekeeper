import { defineConfig, devices } from '@playwright/test';

/**
 * Playwright E2E test configuration for EVE Gatekeeper web frontend.
 *
 * By default, tests run against the live production URL.
 * Set BASE_URL=http://localhost:3099 to test against a local dev server.
 *
 * @see https://playwright.dev/docs/test-configuration
 */

const baseURL = process.env.BASE_URL || 'https://gatekeeper.aretedriver.dev';
const isLocal = baseURL.includes('localhost');

export default defineConfig({
  testDir: './e2e',
  outputDir: './test-results',

  // Run tests in files in parallel
  fullyParallel: true,

  // Fail the build on CI if you accidentally left test.only in the source code
  forbidOnly: !!process.env.CI,

  // Retry on CI, once locally
  retries: process.env.CI ? 2 : 1,

  // Opt out of parallel tests on CI
  workers: process.env.CI ? 1 : undefined,

  // 30s per test
  timeout: 30_000,

  // Reporter to use
  reporter: [
    ['html', { open: 'never', outputFolder: './playwright-report' }],
    ['list'],
  ],

  // Shared settings for all the projects below
  use: {
    baseURL,

    // Collect trace when retrying the failed test
    trace: 'on-first-retry',

    // Screenshot on failure
    screenshot: 'only-on-failure',
  },

  // Configure projects for major browsers
  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
    },
  ],

  // Only start local dev server when testing locally
  ...(isLocal
    ? {
        webServer: {
          command: 'npm run dev -- -p 3099',
          url: 'http://localhost:3099',
          reuseExistingServer: !process.env.CI,
          timeout: 120 * 1000,
          cwd: __dirname,
        },
      }
    : {}),
});
