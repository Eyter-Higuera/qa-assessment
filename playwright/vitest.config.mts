import { defineConfig } from 'vitest/config';

/**
 * Unit tests for the helpers the suites are built on.
 *
 * Kept strictly separate from Playwright, which owns `./tests`: these files live
 * beside the code they cover as `*.test.ts` under `src/`, so neither runner ever
 * collects the other's files. Vitest here means no browser, no network and no
 * demoqa.com - if a test in this project needs any of those, it belongs in
 * `tests/` instead.
 */
export default defineConfig({
  test: {
    include: ['src/**/*.test.ts'],
    // The junit file feeds the same run-summary reader as Karate and Playwright,
    // so all three stages report identically.
    reporters: ['default', 'junit'],
    outputFile: { junit: 'test-results/unit-junit.xml' },
  },
});
