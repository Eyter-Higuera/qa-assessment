# Senior QA Engineer — Assessment

Written submission and working automation for the
[demoqa.com Book Store](https://demoqa.com/books) application.

## The submission

| Deliverable | Where |
|---|---|
| **Written document** — all questions, Parts 1–3, plus test plan and defect log | [Senior_QA_Engineer_Assessment.md](Senior_QA_Engineer_Assessment.md) |
| Same document, formatted — open in a browser, print to PDF | [docs/assessment.html](docs/assessment.html) |
| Web automation (Playwright + TypeScript) | [`playwright/`](playwright/) |
| API automation (Karate + Java) | [`karate/`](karate/) |

**The automated flow:** register → login → search & add a book → view the collection →
delete the book → logout. Automated at both layers.

## Test results

Both suites were executed against the live site while this repository was written.

```
Playwright   7 passed (chromium)
Karate      23 scenarios passed, 0 failed
```

Building them surfaced **11 defects and observations** in the application under test,
documented with reproduction steps in Appendix B of the assessment document.

## Running the tests

> **On Windows PowerShell**, run the lines in each block one at a time. Windows
> PowerShell 5.1 has no `&&` operator, so joining them into a single line fails with
> *"El token '&&' no es un separador de instrucciones válido"* / *"'&&' is not a valid
> statement separator"*. Use `;` to chain, or `; if ($?) { ... }` to stop on the first
> failure. Git Bash and PowerShell 7+ accept `&&` as written.

### Web (Playwright)

```bash
cd playwright
npm ci
npx playwright install chromium
npm test                    # full suite, chromium
npm run test:smoke          # @smoke only
npm run test:headed         # watch it run
npm run report              # open the HTML report
```

Override the target environment with an environment variable:

```bash
BASE_URL=https://staging.example.com npm test        # bash
```

```powershell
$env:BASE_URL='https://staging.example.com'; npm test  # PowerShell
```

The `VAR=value command` prefix is bash-only — PowerShell has no inline env-var syntax.

#### Cross-browser runs

Chromium is the gate and the only browser the setup above installs, so every
`npm` script pins `--project=chromium`. Firefox and WebKit are opt-in and need
their browsers installed first:

```bash
npx playwright install firefox webkit
npm run test:cross-browser
```

All three browsers pass. They stay out of the PR gate to keep it fast, not because
they are broken — but they run against a public demo site, so treat a failure there
as "check the environment" before "check the product".

### API (Karate)

Requires **Java 17** and Maven 3.8+. Karate's GraalJS engine does not support JDK 18+ —
on a newer JDK the suite hangs silently instead of failing, so check `java -version`
first. Java 17 is what CI pins.

```bash
cd karate
mvn test -Dtest=BookStoreApiTest    # full suite
mvn test -Dtest=SmokeTest           # @smoke only
mvn test -Dkarate.env=staging       # point at another environment
```

On Windows PowerShell, quote any `-D` containing a dot — PowerShell ends a parameter
name at the first `.`, so `-Dkarate.env=staging` arrives at Maven split in two and
fails with *"Unknown lifecycle phase '.env=staging'"*:

```powershell
mvn test '-Dkarate.env=staging'
```

Reports land in `karate/target/karate-reports/karate-summary.html`.

## Repository layout

```
Senior_QA_Engineer_Assessment.md   the written submission
docs/assessment.html               the same document, formatted for reading and print
playwright/                        web automation — page objects, fixtures, specs
karate/                            API automation — feature files and JUnit runners
.github/workflows/ci.yml           smoke on every PR, full regression nightly
```

## How the suites are put together

* **Page objects** (`playwright/src/pages/`) hold every selector; specs read as user
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
  through the API. See Appendix A → *Known constraints*.
* **No `waitForTimeout`.** Every wait is an assertion on a condition (`toBeVisible`,
  `toHaveText`), which is what keeps the suite honest and fast.
