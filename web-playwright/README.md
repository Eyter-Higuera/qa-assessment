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

```bash
npx playwright test --grep @smoke
npx playwright test --project=firefox      # requires: npx playwright install firefox
npx playwright test --debug                # step through with the inspector
```

## Notable choices

**One test for the journey, not five.** The five steps of the flow are one user
journey; splitting them into independent tests would either re-run the whole prefix
each time or leak state. `test.step()` keeps the report per-step, so a failure still
points at the exact stage.

**Locators follow what the user sees.** The app reuses `id="submit"` for three
different buttons and `id="addNewRecordButton"` for two, so ids alone are ambiguous
(see `docs/defects.md`). Buttons are addressed by role + accessible name, which is
both unambiguous and closer to how a person uses the page.

**Ads are stripped after navigation.** demoqa serves third-party ad frames that float
over the page and swallow clicks. `BasePage.suppressAds()` removes them — the
difference between a suite that fails one run in five and one that doesn't.

**Cross-layer assertions reuse the browser's token.** The back end keeps a single
valid token per user: calling `GenerateToken` again silently invalidates the UI
session mid-test. `sessionTokenFromBrowser()` reads the session cookie instead.
