import { defineConfig, devices } from '@playwright/test';

/**
 * Playwright configuration for the demoqa.com Book Store suite.
 *
 * Design notes
 *  - `baseURL` is env-driven so the same suite can point at a local/staging build.
 *  - Retries only on CI: locally a flake should be seen and fixed, not hidden.
 *  - Trace/video/screenshot are captured on first retry so failures are debuggable
 *    from the CI artifact alone, without re-running anything by hand.
 */
export default defineConfig({
  testDir: './tests',
  outputDir: './test-results',
  timeout: 60_000,
  expect: { timeout: 10_000 },

  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  workers: process.env.CI ? 2 : undefined,

  reporter: [
    ['list'],
    ['html', { outputFolder: 'playwright-report', open: 'never' }],
    ['junit', { outputFile: 'test-results/junit.xml' }],
  ],

  use: {
    baseURL: process.env.BASE_URL ?? 'https://demoqa.com',
    actionTimeout: 15_000,
    navigationTimeout: 30_000,
    trace: 'retain-on-failure',
    screenshot: 'only-on-failure',
    video: 'retain-on-failure',
    viewport: { width: 1600, height: 1000 },
    testIdAttribute: 'data-testid',
  },

  projects: [
    { name: 'chromium', use: { ...devices['Desktop Chrome'] } },
    // Cross-browser coverage is opt-in (`--project=firefox`) to keep the PR gate fast.
    { name: 'firefox', use: { ...devices['Desktop Firefox'] } },
    { name: 'webkit', use: { ...devices['Desktop Safari'] } },
  ],
});
