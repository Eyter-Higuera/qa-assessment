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
  // The @e2e journey registers, logs in, searches, adds, opens, deletes and logs
  // out. Any one of those can be slow, and LOGIN_RESPONSE_TIMEOUT alone allows
  // 30s for the login round-trip - half of a 60s budget before the journey has
  // started. The container has to be bigger than the parts it now tolerates.
  timeout: 120_000,
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

  // All four are declared so `--project=<browser>` works, but the npm scripts pin
  // `--project=chromium`: chromium is the gate, and it is the only browser the
  // documented setup (`npx playwright install chromium`) actually installs.
  // Cross-browser is genuinely opt-in - `npm run test:cross-browser`, after
  // `npx playwright install firefox webkit msedge`. See README -> Cross-browser runs.
  //
  // `playwright test` has no --channel flag, so Microsoft Edge is modelled as a
  // project that pins the channel. That keeps CI on a single dispatch mechanism:
  // one dropdown value maps to one --project argument, Edge included.
  projects: [
    { name: 'chromium', use: { ...devices['Desktop Chrome'] } },
    { name: 'firefox', use: { ...devices['Desktop Firefox'] } },
    { name: 'webkit', use: { ...devices['Desktop Safari'] } },
    { name: 'msedge', use: { ...devices['Desktop Edge'], channel: 'msedge' } },
  ],
});
