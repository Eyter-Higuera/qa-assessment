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

[`.github/workflows/ci.yml`](.github/workflows/ci.yml) is a branch-per-environment
promotion chain. The branch decides the environment; a single `config` job resolves
*which environment, which suite, which browsers, and does this run promote*, and
every other job reads its parameters from there — one place to change, not six.

| Branch | Environment | On push |
|---|---|---|
| `eyter_dev` | dev | full suite, chromium — then promote to `release` |
| `release` | release | full regression, all four browsers — then promote to `main` |
| `main` | production | deploy, then post-deployment smoke (API + UI) |

```
push eyter_dev → api + ui (dev)      → promote ─┐
push release   → api + ui (release)  → promote ─┤   each promotion is a push,
push main      → deploy → smoke (production)  ←─┘   which starts the next stage
```

Coverage widens as the code approaches production: one browser on the development
gate to keep it fast, all four before production, smoke afterwards to confirm the
deployment rather than re-test the build.

**Promotion is a fast-forward, never a merge commit.** The promote job pushes the
exact SHA that just passed at the next branch:

```bash
git push origin "$TESTED_SHA:refs/heads/$TARGET"
```

Git rejects that push if the target has diverged, which is the outcome you want — a
loud failure beats a CI-authored merge commit that no stage of the pipeline has ever
run against. The tree that lands on `release` is byte-for-byte the tree that passed
on `eyter_dev`.

> **Set a `PROMOTION_TOKEN` secret** (a PAT or app token with `contents: write`) for
> the chain to flow on its own. A push made with the default `GITHUB_TOKEN` does not
> trigger another workflow run — by design, to prevent recursion — so without it the
> branch is updated but the next stage never starts. The job warns when it is running
> on the fallback token. If the target branches are protected, that token also needs
> permission to push to them.

**Run it by hand** from the Actions tab (*Run workflow*). There is no
target-environment input: choosing the ref already says which environment you mean,
which is the point of mapping branches to environments.

| Input | Options | Wired to |
|---|---|---|
| Branch (*Use workflow from*) | any ref | `-Dkarate.env=…` and `BASE_URL`, via the branch map above |
| Test suite | `smoke`, `full` | `-Dtest=SmokeTest` or `-Dtest=BookStoreApiTest`, `--grep @smoke` |
| Browser | `chromium`, `firefox`, `webkit`, `msedge`, `all` | `--project=…` (a matrix leg each; `all` runs the four in parallel) |
| Promote | off by default | whether a green run moves the branch on |

Promotion is opt-in on manual runs, so re-running a suite to check something can
never move a branch by accident. Feature branches and PR refs map to dev and never
promote, whatever that checkbox says — promotion is a property of the chain, not of
any branch that happens to run the suite.

Other triggers: a pull request runs the smoke gate on dev in chromium, and the
nightly schedule runs the full suite across all four browsers on dev regardless of
the ref it fires on. Neither promotes.

The runner installs browsers with `npx playwright install --with-deps`, plus
`npx playwright install --with-deps msedge` on the Edge leg, since the bare command
does not fetch the branded channel.

Host names come from the repository variables `DEV_BASE_URL`, `RELEASE_BASE_URL` and
`PRODUCTION_BASE_URL`, falling back to the public demo site so the pipeline runs in a
fresh fork. Each promotion is gated on the GitHub environment it moves towards
(`release`, then `production`), so a required-reviewer approval can be added in
repository settings without touching the workflow. The deploy step is a labelled
placeholder — this repository has nothing of its own to ship.

Reports are uploaded for **every** environment: `karate-reports-<env>` and
`playwright-report-<env>-<browser>`, retained 14 days.

## Repository layout

```
Senior_QA_Engineer_Assessment.md   the written submission
docs/assessment.html               the same document, formatted for reading and print
playwright/                        web automation — page objects, fixtures, specs
karate/                            API automation — feature files and JUnit runners
.github/workflows/ci.yml           eyter_dev → release → main promotion chain; see CI/CD above
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
