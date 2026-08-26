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
`npm` script pins `--project=chromium`. Firefox, WebKit and Microsoft Edge are
opt-in and need their browsers installed first:

```bash
npx playwright install firefox webkit msedge
npm run test:cross-browser
npx playwright test --project=msedge
```

Edge is a branded channel rather than a bundled engine, so `npx playwright install`
on its own does not fetch it — it has to be named. `playwright test` has no
`--channel` flag either, so the config models Edge as a project that pins
`channel: 'msedge'`; one `--project` argument then selects any of the four.

All four browsers pass. They stay out of the PR gate to keep it fast, not because
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
mvn test -Dkarate.env=production -DbaseUrl=https://demoqa.com   # host override
```

On Windows PowerShell, quote any `-D` containing a dot — PowerShell ends a parameter
name at the first `.`, so `-Dkarate.env=staging` arrives at Maven split in two and
fails with *"Unknown lifecycle phase '.env=staging'"*:

```powershell
mvn test '-Dkarate.env=staging'
```

Reports land in `karate/target/karate-reports/karate-summary.html`.

## CI/CD

[`.github/workflows/ci.yml`](.github/workflows/ci.yml) is a staging-to-production
delivery pipeline. A single `config` job resolves *which environment, which suite,
which browsers, and does this run promote* from the trigger and inputs, and every
other job reads its parameters from there — so there is one place to change, not six.

**On push to `main`** the full Karate and Playwright suites run against **staging**.
Only if both are green does `promote-to-production` deploy, and post-deployment
**smoke** tests then run against production at both layers — API and UI.

```
config → api-tests (staging) → ui-tests (staging) → promote → ┬ verify: API (production)
                                                              └ verify: Web (production)
```

**Run it by hand** from the Actions tab (*Run workflow*), which offers four dropdowns:

| Input | Options | Wired to |
|---|---|---|
| Execution mode | `single_env`, `staging_to_prod` | whether the promotion stage runs at all |
| Target environment | `staging`, `production` | `-Dkarate.env=…` and `BASE_URL` |
| Test suite | `smoke`, `full` | `-Dtest=SmokeTest` or `-Dtest=BookStoreApiTest`, `--grep @smoke` |
| Browser | `chromium`, `firefox`, `webkit`, `msedge`, `all` | `--project=…` (a matrix leg each; `all` runs the four in parallel) |

The two modes:

* **`single_env`** — run the chosen suite and browsers against **target environment**
  and stop. Nothing is promoted and no production job runs, whether the target was
  staging or production. This is the mode for "re-run the API suite against
  production in Edge" without touching a deployment.
* **`staging_to_prod`** — the manual equivalent of the push flow. Stage A runs the
  chosen suite and browsers against staging; only if it is green does stage B
  promote and then verify production with **the same suite and browsers**. Target
  environment is ignored here, because this mode always starts at staging.

The one asymmetry worth knowing: an automatic promotion from a push to `main` runs
`full` on staging but verifies production with `smoke`, keeping the post-deploy check
fast. A `staging_to_prod` run verifies with whatever suite the operator picked, since
they asked for it explicitly.

Other triggers keep their previous behaviour: a pull request runs the smoke gate on
staging in chromium, and the nightly schedule runs the full suite on staging across
all four browsers. Neither promotes.

The runner installs browsers with `npx playwright install --with-deps`, plus
`npx playwright install --with-deps msedge` on the Edge leg, since the bare command
does not fetch the branded channel.

Host names come from the repository variables `STAGING_BASE_URL` and
`PRODUCTION_BASE_URL`, falling back to the public demo site so the pipeline runs in
a fresh fork. `promote-to-production` targets a GitHub `production` environment, so a
required-reviewer gate can be added there without touching the workflow. Its deploy
step is a labelled placeholder — this repository has nothing of its own to ship.

Reports are uploaded for **both** environments: `karate-reports-<env>` and
`playwright-report-<env>-<browser>`, retained 14 days.

## Repository layout

```
Senior_QA_Engineer_Assessment.md   the written submission
docs/assessment.html               the same document, formatted for reading and print
playwright/                        web automation — page objects, fixtures, specs
karate/                            API automation — feature files and JUnit runners
.github/workflows/ci.yml           staging → production CD pipeline; see CI/CD above
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
