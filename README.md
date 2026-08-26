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

[`.github/workflows/ci.yml`](.github/workflows/ci.yml) is a promotion chain that
runs as **one ordered workflow run**. Every stage is wired to the one before it with
`needs:`, so a stage physically cannot start until its predecessor is green:

```
config → 1. dev tests → promote to release → 2. release tests → promote to main
                                                → 3. deploy production → smoke
```

| Stage | Environment | Runs |
|---|---|---|
| 1. dev | dev | regression suite, chromium |
| 2. release | release | full regression, all four browsers |
| 3. production | production | deploy, then smoke (API + UI) |

Coverage widens as the commit approaches production: one browser on the development
gate to keep it fast, all four before production, smoke afterwards to confirm the
deployment rather than re-test the build.

**The branch you run from picks the entry point.** `eyter_dev` enters at stage 1,
`release` at stage 2, `main` at stage 3; stages before the entry point are skipped and
everything after it keeps its order. So running the workflow from `release` actually
runs the release tests, instead of skipping them because the promotion that normally
precedes them never happened.

That last part is the subtle bit. A skipped job normally skips everything that `needs`
it, which would cascade-skip the whole chain below an unused entry point. The stages
that can be entered directly therefore test `needs.<previous>.result` explicitly rather
than relying on the default needs-semantics.

**Only `eyter_dev` triggers on push.** `release` and `main` deliberately do not, and
that is the point: when all three were push triggers, pushing two branches started two
independent runs and each promotion push started another, so the stages raced instead
of queuing. Promotion now advances the chain through `needs:` — the branch push is
only the *record* of what passed, not the trigger for what happens next. To enter at
stage 2 or 3, run the workflow manually from that branch.

**Promotion is a fast-forward, never a merge commit.** Each promote job pushes the
exact SHA that just passed at the next branch:

```bash
git push origin "$TESTED_SHA:refs/heads/$TARGET"
```

Git rejects that push if the target has diverged, which is the outcome you want — a
loud failure beats a CI-authored merge commit that no stage of the pipeline has ever
run against. The tree that lands on `main` is byte-for-byte the tree that passed on
`eyter_dev`.

Because the chain is held together by `needs:` rather than by push events, the default
`GITHUB_TOKEN` is enough. A `PROMOTION_TOKEN` secret is only needed if branch
protection refuses pushes from that token; the promote jobs prefer it when present.

**Run it by hand** from the Actions tab (*Run workflow*):

| Input | Options | Wired to |
|---|---|---|
| Test suite | `smoke`, `regression` | `-Dtest=SmokeTest` or `-Dtest=BookStoreApiTest`, `--grep @smoke` |
| Browser | `chromium`, `firefox`, `webkit`, `msedge`, `all` | `--project=…` (a matrix leg each; `all` runs the four in parallel) |
| Promote | off by default | whether the run continues past its entry stage |

*Use workflow from* is the fourth input in everything but name: it chooses the entry
stage, which is why there is no target-environment dropdown.

Leave *Promote* unticked and the run tests its entry stage and stops — nothing is
promoted, no branch moves, nothing is deployed. Tick it and the same run continues
from there in order, running your chosen suite and browsers at each test stage it
reaches.

Promote also gates the deployment, not just branch movement. Running from `main` with
it unticked verifies production with the smoke suite and deploys nothing, which is the
mode for "is production still healthy?". Ticking it deploys first, then verifies.

| Run from | Promote off | Promote on |
|---|---|---|
| `eyter_dev` | dev tests | dev → release → deploy → smoke |
| `release` | release tests | release → deploy → smoke |
| `main` | production smoke, no deploy | deploy, then production smoke |

Other triggers: a pull request runs the smoke gate on dev in chromium, and the nightly
schedule runs the full suite across all four browsers on dev. Neither promotes.

The two test stages and the production smoke stage all call
[`test-stage.yml`](.github/workflows/test-stage.yml), a reusable workflow holding the
Karate and Playwright jobs. Three stages sharing one definition beats three copies of
the same twenty lines — the browser install, in particular, has one place to change.
It installs with `npx playwright install --with-deps`, plus
`npx playwright install --with-deps msedge` on the Edge leg, since the bare command
does not fetch the branded channel.

Host names come from the repository variables `DEV_BASE_URL`, `RELEASE_BASE_URL` and
`PRODUCTION_BASE_URL`, falling back to the public demo site so the pipeline runs in a
fresh fork. Each promotion is gated on the GitHub environment it moves towards
(`release`, then `production`), so a required-reviewer approval can be added in
repository settings without touching the workflow — and because the chain is one run,
that approval now pauses the pipeline rather than letting later stages race ahead. The
deploy step is a labelled placeholder — this repository has nothing of its own to ship.

Reports are uploaded for **every** environment: `karate-reports-<env>` and
`playwright-report-<env>-<browser>`, retained 14 days.

## Repository layout

```
Senior_QA_Engineer_Assessment.md   the written submission
docs/assessment.html               the same document, formatted for reading and print
playwright/                        web automation — page objects, fixtures, specs
karate/                            API automation — feature files and JUnit runners
.github/workflows/ci.yml           eyter_dev → release → main promotion chain; see CI/CD above
.github/workflows/test-stage.yml   reusable Karate + Playwright stage, called once per environment
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
