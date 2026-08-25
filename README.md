# Book Store QA Automation

Automation for the [demoqa.com Book Store](https://demoqa.com/books) application, covering
the same journey at two layers:

| Layer | Tool | Location |
|---|---|---|
| Web UI | Playwright + TypeScript | [`web-playwright/`](web-playwright/) |
| REST API | Karate (Java) | [`api-karate/`](api-karate/) |

**The automated flow:** register → login → search & add a book → view the collection →
delete the book → logout.

## Documents

| Document | What it covers |
|---|---|
| [docs/test-plan.md](docs/test-plan.md) | Test plan for the Book Store application (Task A) |
| [docs/defects.md](docs/defects.md) | Defects found while building the suite — with evidence |
| [docs/qa-assessment.md](docs/qa-assessment.md) | Written answers: QA strategy, mentoring, multi-currency settlement |

## Running the tests

### Web (Playwright)

```bash
cd web-playwright
npm ci
npx playwright install chromium
npm test                    # full suite, chromium
npm run test:smoke          # @smoke only
npm run test:headed         # watch it run
npm run report              # open the HTML report
```

Override the target environment with `BASE_URL=https://staging.example.com npm test`.

### API (Karate)

```bash
cd api-karate
mvn test -Dtest=BookStoreApiTest    # full suite
mvn test -Dtest=SmokeTest           # @smoke only
mvn test -Dkarate.env=staging       # point at another environment
```

Reports land in `api-karate/target/karate-reports/karate-summary.html`.

## Test results

Both suites were executed against the live site while this repository was written.

```
Playwright   7 passed (chromium)
Karate      23 scenarios passed, 0 failed
```

## How the suites are put together

* **Page objects** (`web-playwright/src/pages/`) hold every selector; specs read as user
  journeys, so a UI change is a one-file fix.
* **Unique account per test.** The Book Store user namespace is global and shared with
  everyone else using the demo site, so a fixed username would eventually collide.
  Each test provisions its own account and deletes it afterwards.
* **Setup through the API, assertions through the UI.** A test that owns "cancel delete"
  seeds its book over REST rather than clicking through the add flow — it should only
  fail for its own reason.
* **Registration is provisioned over the API.** The UI form is protected by Google
  reCAPTCHA. Bypassing it would only work against this demo site and would give false
  confidence, so the UI suite asserts the form's contract and the happy path runs
  through the API. See [docs/test-plan.md](docs/test-plan.md) → *Known constraints*.
* **No `waitForTimeout`.** Every wait is an assertion on a condition (`toBeVisible`,
  `toHaveText`), which is what keeps the suite honest and fast.
