# Web automation — Playwright

```
src/pages/     page objects: one class per screen, all selectors live here
src/utils/     API client (test-data setup/teardown) and test data
tests/         specs + fixtures
```

## Suites

| Tag | What it is | When it runs |
|---|---|---|
| `@smoke` | login, registration form, access control | every PR, must never flake |
| `@e2e` | the full collection journey | every PR |
| `@regression` | secondary paths (cancel delete, …) | nightly |

The `npm` scripts all pin `--project=chromium`, which is the PR gate and the only
browser the documented setup installs. Firefox and WebKit are opt-in.

```bash
npm run test:smoke                         # @smoke, chromium
npm run test:cross-browser                 # firefox + webkit, opt-in
npx playwright test --project=firefox      # requires: npx playwright install firefox
npx playwright test --debug                # step through with the inspector
```

Note that a bare `npx playwright test` runs *all three* projects, because all three
are declared in `playwright.config.ts` so that `--project=firefox` works. Use the
`npm` scripts to get the chromium-only gate.

## Notable choices

**One test for the journey, not five.** The five steps of the flow are one user
journey; splitting them into independent tests would either re-run the whole prefix
each time or leak state. `test.step()` keeps the report per-step, so a failure still
points at the exact stage.

**Locators follow what the user sees.** The app reuses `id="submit"` for three
different buttons and `id="addNewRecordButton"` for two, so ids alone are ambiguous
(see Appendix B of `Senior_QA_Engineer_Assessment.md`). Buttons are addressed by role + accessible name, which is
both unambiguous and closer to how a person uses the page.

**Ads are blocked at the network layer, then swept from the DOM.** demoqa serves
third-party ad frames that float over the page and swallow clicks.
`BasePage.blockAds()` aborts those requests before they load and
`BasePage.suppressAds()` removes anything that still landed. The network block is
the one that matters: the same requests also delay `domcontentloaded`, so blocking
them prevents navigation timeouts as well as stolen clicks. A DOM sweep alone is not
enough, because demoqa injects frames asynchronously *after* the sweep has run and
the reflow stops elements ever settling into an actionable state.

**Cross-layer assertions reuse the browser's token.** The back end keeps a single
valid token per user: calling `GenerateToken` again silently invalidates the UI
session mid-test. `sessionTokenFromBrowser()` reads the session cookie instead.
