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

    coverage: {
      provider: 'v8',
      // text-summary for the step log, lcov for any external tool, and
      // json-summary because it is the one a script can read without guessing.
      reporter: ['text-summary', 'lcov', 'json-summary'],
      reportsDirectory: 'coverage',

      // Coverage measures the code UNIT tests are responsible for: pure logic,
      // no browser and no network. The exclusions below are not there to flatter
      // the number - each names a surface that is deliberately covered by a
      // different suite, and counting it here would measure the absence of
      // Playwright rather than the quality of these tests.
      include: ['src/**/*.ts'],
      exclude: [
        // Page objects only have meaning while driving a real browser; the
        // Playwright suite in tests/ is what exercises them.
        'src/pages/**',
        // Network I/O against demoqa. Unit-testing it would mean asserting
        // against a mock of a service the real suites already call for real.
        'src/utils/api-client.ts',
        '**/*.test.ts',
      ],

      // Fails the run, so this is a gate rather than a report. 80% is the floor
      // asked for; the covered surface currently sits well above it.
      thresholds: { statements: 80, branches: 80, functions: 80, lines: 80 },
    },
  },
});
