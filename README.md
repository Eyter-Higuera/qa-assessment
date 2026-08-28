# Senior QA Engineer — Assessment

Written submission and working automation for the
[demoqa.com Book Store](https://demoqa.com/books) application.

## The submission

| Deliverable | Where |
|---|---|
| **Written document** — all questions, Parts 1–3, plus test plan and defect log | [Senior_QA_Engineer_Assessment.md](Senior_QA_Engineer_Assessment.md) |
| Same document, formatted | [docs/test_strategy_design.pdf](https://github.com/Eyter-Higuera/qa-assessment/raw/main/docs/test_strategy_design.pdf) — 52 pages · source [docs/test_strategy_design.html](docs/test_strategy_design.html) |
| Web automation (Playwright + TypeScript) | [`playwright/`](playwright/) |
| API automation (Karate + Java) | [`karate/`](karate/) |

**The automated flow:** register → login → search & add a book → view the collection →
delete the book → logout. Automated at both layers.

> **The PDF links above are absolute raw URLs on purpose.** GitHub's in-browser file
> viewer does not reliably display these PDFs — it answers *"Unable to render code
> block"* — and a relative link resolves to exactly that viewer. The raw URL serves
> the file itself, so the browser opens or downloads it. The cost is that the links
> name this repository, so a fork has to update them.

## Test results

Both suites were executed against the live site while this repository was written.

```
Playwright   7 passed (chromium)
Karate      23 scenarios passed, 0 failed
```

Building them surfaced **11 defects and observations** in the application under test,
documented with reproduction steps in Appendix B of the assessment document.

## Executive test metrics

<!-- metrics:start -->
**14 test cases, 14 passed, 0 failed — a 100% pass rate** on the smoke gate, measured at commit `479aa3d` by executing every suite rather than by counting source.

```mermaid
pie showData title Smoke gate test cases by layer (14 total)
    "Unit (Vitest)" : 7
    "API (Karate)" : 2
    "UI (Playwright)" : 5
```

| Test suite / layer | Tool | Total cases | Passed | Failed | Coverage / scope |
|---|---|--:|--:|--:|---|
| **Unit** | Vitest | 7 | 7 | 0 | Pure logic in src/ - 100% of the covered surface |
| **API (smoke)** | Karate | 2 | 2 | 0 | @smoke scenarios - the deployment gate |
| **UI (smoke)** | Playwright | 5 | 5 | 0 | @smoke journeys on chromium |
| **Smoke gate total** | — | **14** | **14** | **0** | Runs on every pull request and verifies every production deploy |
| API (regression) | Karate | 23 | 23 | 0 | Every scenario, all tags |
| UI (regression) | Playwright | 7 | 7 | 0 | Every spec on chromium |

Unit coverage on the surface unit tests own: Statements 100%, Branches 100%, Functions 100%, Lines 100% — floor 80%.

The regression rows are listed apart from the gate on purpose: reporting "2 API cases" without saying *smoke* would misrepresent a suite that has 23. Regenerate every figure here with `python scripts/collect_test_metrics.py`.
<!-- metrics:end -->

## Testing manual

<!-- testing-manual:start -->

### 1. Testing architecture

Three layers, run in a strict sequence. Each is cheaper and more certain than the
one after it, so the pipeline learns the cheapest thing first and stops as soon as
it knows enough.

| Layer | Tool | Scope | Needs a target URL? | Fails the stage below it |
|---|---|---|---|---|
| **Unit** | Vitest | Pure logic in `playwright/src` — no browser, no network | No | Skips API **and** UI |
| **API** | Karate (Java 17 + Maven) | Book Store REST contract, per scenario | Yes | Skips UI |
| **UI** | Playwright | Browser journeys, one leg per browser | Yes | — |

```
0. unit (Vitest)  →  api (Karate)  →  ui (Playwright, one leg per browser)
```

**Why unit tests run once, not per environment.** Unit tests assert pure logic —
they never open a browser, never make a request, never touch demoqa.com. Their
answer therefore *cannot* differ between dev, release and production. Running them
inside each stage bought three identical answers to the same question, and made the
API suite wait behind a redundant `npm ci` every time. They now run once, straight
after the run configuration is resolved, as job `0. Unit tests (Vitest)`.

Because they run once, they have to gate *every* way into the chain. `dev` inherits
that through ordinary job dependencies, but `release` and `production` are entry
points in their own right and their conditions use a status function, which opts out
of the implicit "all dependencies succeeded" rule. Both therefore name the result
explicitly — without that, starting a run from `release` would walk straight past
the gate.

### 2. Local execution

Three parameters run through everything: **environment** (which host), **suite**
(smoke or regression) and **browser**.

> **Windows PowerShell.** Run the lines in each block one at a time. PowerShell 5.1
> has no `&&`, so joining them fails with *"'&&' is not a valid statement
> separator"*. Use `;` to chain, or `; if ($?) { … }` to stop on the first failure.
> Git Bash and PowerShell 7+ accept `&&` as written. PowerShell also has no inline
> `VAR=value command` prefix — use `$env:VAR='…'` on its own statement.
>
> **Quote Playwright's tags on PowerShell too.** `@` is the splatting operator, so a
> bare `--grep @smoke` expands the undefined variable `$smoke` to nothing and the
> argument silently disappears — Playwright then reports
> *"option '-g, --grep <grep>' argument missing"*. Write `--grep '@smoke'`.

#### Unit tests and coverage (Vitest)

```bash
cd playwright
npm ci
npm run test:unit                 # tests only
npm run test:unit -- --coverage   # tests + coverage gate
npm run test:unit:watch           # re-run on save while developing
```

Coverage is scoped to the code unit tests are responsible for. `src/pages/**` and
`src/utils/api-client.ts` are excluded by rule, because the Playwright suite and the
live API are what exercise them — counting them here would measure the absence of
Playwright rather than the quality of these tests.

| Metric | Covered | Total | % | Floor |
|---|--:|--:|--:|--:|
| Statements | 2 | 2 | 100% | 80% |
| Branches | 1 | 1 | 100% | 80% |
| Functions | 1 | 1 | 100% | 80% |
| Lines | 2 | 2 | 100% | 80% |

Vitest fails the run itself when any metric drops below the floor, so the gate is
the runner's and not a later script's reading of a report. Read the figure as *"the
pure logic is covered"*, not *"the project is covered"* — the covered surface is
deliberately small.

<p align="center">
  <img src="docs/images/local-unit-coverage.png" width="100%" alt="Unit test coverage in the terminal" />
</p>

#### API tests (Karate)

Requires **Java 17** and Maven 3.8+. Karate's GraalJS engine does not support
JDK 18+ — on a newer JDK the suite hangs silently instead of failing, so check
`java -version` first.

```bash
cd karate
```

Quote any `-D` containing a dot on PowerShell: it ends a parameter name at the first
`.`, so `-Dkarate.env=dev` arrives at Maven split in two and fails with *"Unknown
lifecycle phase '.env=dev'"*.

**Dev** — smoke:

```bash
mvn test -Dtest=SmokeTest -Dkarate.env=dev
```
```powershell
mvn test '-Dtest=SmokeTest' '-Dkarate.env=dev'
```

<p align="center">
  <img src="docs/images/local-karate-dev.png" width="100%" alt="Karate smoke against dev" />
</p>

**Release** — full regression:

```bash
mvn test -Dtest=BookStoreApiTest -Dkarate.env=release -DbaseUrl=https://demoqa.com
```
```powershell
mvn test '-Dtest=BookStoreApiTest' '-Dkarate.env=release' '-DbaseUrl=https://demoqa.com'
```

<p align="center">
  <img src="docs/images/local-karate-release.png" width="100%" alt="Karate regression against release" />
</p>

**Production** — smoke, with an explicit host:

```bash
mvn test -Dtest=SmokeTest -Dkarate.env=production -DbaseUrl=https://demoqa.com
```
```powershell
mvn test '-Dtest=SmokeTest' '-Dkarate.env=production' '-DbaseUrl=https://demoqa.com'
```

<p align="center">
  <img src="docs/images/local-karate-production.png" width="100%" alt="Karate smoke against production" />
</p>

`-Dtest` picks the runner class and therefore the tag set: `SmokeTest` runs `@smoke`,
`BookStoreApiTest` runs everything.

`release` and `production` both need `-DbaseUrl` locally. `dev` defaults to the demo
site, but `release` falls back to a placeholder host that does not resolve, so the
command would fail with a connection error rather than a test failure. In CI the
host comes from the `RELEASE_BASE_URL` repository variable instead. Reports land in
`karate/target/karate-reports/karate-summary.html`.

#### UI tests (Playwright)

> **Run every command in this section from `playwright/`**, not from the repository
> root. Playwright is a dev dependency of that package, and its config lives there.
>
> Two symptoms tell you that you are in the wrong directory. `npx` offers to download
> a throwaway copy — *"Need to install the following packages: playwright@…  Ok to
> proceed?"* — and, having found no config, it then reports
>
> ```
> Error: Project(s) "chromium" not found. Available projects: ""
> ```
>
> An empty *available projects* list always means the config was not found, never
> that the project is misspelled. `cd playwright` and run it again.

```bash
cd playwright
npx playwright install chromium              # or: firefox webkit msedge
```
```powershell
Set-Location playwright
npx playwright install chromium
```

**Dev** — smoke on chromium:

```bash
BASE_URL=https://demoqa.com npx playwright test --project=chromium --grep @smoke
```
```powershell
$env:BASE_URL='https://demoqa.com'; npx playwright test --project=chromium --grep '@smoke'
```

<p align="center">
  <img src="docs/images/local-playwright-dev.png" width="100%" alt="Playwright smoke against dev" />
</p>

**Release** — regression across every browser:

```bash
BASE_URL=https://demoqa.com npx playwright test --project=chromium --project=firefox --project=webkit --project=msedge
```
```powershell
$env:BASE_URL='https://demoqa.com'; npx playwright test --project=chromium --project=firefox --project=webkit --project=msedge
```

<p align="center">
  <img src="docs/images/local-playwright-release.png" width="100%" alt="Playwright regression across browsers" />
</p>

**Production** — smoke on Edge:

```bash
BASE_URL=https://demoqa.com npx playwright test --project=msedge --grep @smoke
```
```powershell
$env:BASE_URL='https://demoqa.com'; npx playwright test --project=msedge --grep '@smoke'
```

<p align="center">
  <img src="docs/images/local-playwright-production.png" width="100%" alt="Playwright smoke against production" />
</p>

**UI mode** — pick and re-run tests interactively:

```bash
npx playwright test --ui
npm run test:headed     # or just watch chromium drive
npm run report          # open the last HTML report
```

Edge is a branded channel rather than a bundled engine, so `npx playwright install`
alone does not fetch it — it has to be named. `playwright test` has no `--channel`
flag either, so the config models Edge as a project pinning `channel: 'msedge'`; one
`--project` argument then selects any of the four.

#### The whole sequence in one line

Unit → API → UI, stopping at the first failure:

```bash
cd playwright && npm run test:unit -- --coverage && cd ../karate && mvn test -Dtest=SmokeTest -Dkarate.env=dev && cd ../playwright && BASE_URL=https://demoqa.com npx playwright test --project=chromium --grep @smoke
```

```powershell
cd playwright; if ($?) { npm run test:unit -- --coverage }; if ($?) { cd ../karate }; if ($?) { mvn test '-Dtest=SmokeTest' '-Dkarate.env=dev' }; if ($?) { cd ../playwright }; if ($?) { $env:BASE_URL='https://demoqa.com'; npx playwright test --project=chromium --grep '@smoke' }
```

### 3. GitHub Actions pipeline

Run it from **Actions → QA Automation → Run workflow**. Four things decide what
happens, and the first of them is the branch:

| Input | Options | Effect |
|---|---|---|
| **Use workflow from** | `eyter_dev`, `release`, `main` | Chooses the entry stage — this is why there is no environment dropdown |
| **Test suite** | `smoke`, `regression` | `-Dtest=SmokeTest`/`BookStoreApiTest`, and `--grep @smoke` |
| **Playwright browser** | `chromium`, `firefox`, `webkit`, `msedge`, `all browsers` | One matrix leg each; `all browsers` runs four in parallel |
| **Promote** | checkbox, off by default | Whether the run continues past its entry stage |

#### Scenario A — running from `eyter_dev`

The full chain. Unit tests gate everything; the dev stage runs against the dev host;
if it is green and *Promote* is ticked, the tested commit is fast-forwarded onto
`release`, the release stage runs, and the same happens onto `main` before
production is deployed and verified.

```
0. unit → 1. dev → promote → 2. release → promote → 3. deploy → verify
```

With *Promote* unticked the run stops after the dev stage: nothing is promoted, no
branch moves, nothing is deployed.

<p align="center">
  <img src="docs/images/ci-scenario-a-eyter-dev.png" width="345" alt="Scenario A — full chain from eyter_dev" />
</p>

#### Scenario B — running from `release` or `main`

The branch is the entry point, so earlier stages are skipped and the run starts
where you pointed it. **Promotion is bound to `eyter_dev`**: ticking *Promote* on a
run started from `release`, `main` or a feature branch fails the run in seconds,
before any suite starts, with

> Promotion is only allowed when triggered from the eyter_dev branch.

That guard matters most in the case that looks harmless — a feature branch enters at
the dev stage exactly like `eyter_dev` does, so without it a green feature-branch run
would push its own commit straight at `release`.

Two things to know before running from `main`: entering at stage 3 **deploys**,
promote or not, because `main` has nowhere further to promote to; and a `Pipeline
result` job fails the run if production was deployed but its verification did not
pass, so a deploy can never report green unverified.

<p align="center">
  <img src="docs/images/ci-scenario-b-release-main.png" width="100%" alt="Scenario B — single stage from release or main" />
</p>

#### What the run summary shows

Every job writes its results to the run summary page, so a failure is readable
without downloading an artifact: the Vitest coverage table with a tick or cross per
metric, then a Karate table and a Playwright table per stage — totals, a row per
suite with pass/fail/skip counts and durations, and, when something fails, a second
table naming each failing test with the first line of its error.

<p align="center">
  <img src="docs/images/ci-job-summary.png" width="520" alt="The GitHub job summary" />
</p>

### 4. Local pipeline simulation & multi-environment matrix guide

The pipeline can be run end to end on a laptop, with the same stages, the same
order and the same parameters as CI. One entry point covers the whole matrix:

```bash
node scripts/pipeline.mjs --stage <dev|release|production> \
                          --suite <unit|api|ui|smoke|regression> \
                          --browser <chromium|firefox|webkit|msedge|all>
```

```powershell
node scripts/pipeline.mjs --stage dev --suite smoke --browser chromium
```

The same line works in both shells, and from any directory in the repository.
That is deliberate — see *Why a runner rather than raw commands* below.

<p align="center">
  <img src="docs/images/local-pipeline-matrix.png" width="100%" alt="Resolving a matrix combination with --dry-run" />
</p>

#### The three parameters

| Parameter | Values | What it changes |
|---|---|---|
| `--stage` | `dev`, `release`, `production` | `BASE_URL` for Playwright and `-Dkarate.env` / `-DbaseUrl` for Karate |
| `--suite` | `unit`, `api`, `ui`, `smoke`, `regression` | Which layers run, and how deep |
| `--browser` | `chromium`, `firefox`, `webkit`, `msedge`, `all` | One Playwright project each; `all` runs the four together |

`unit`, `api` and `ui` run that layer **alone and in full**. `smoke` and
`regression` run **all three layers** in the CI order — shallow or deep:

```
unit (Vitest)  →  api (Karate)  →  ui (Playwright)
```

A failing layer stops the run and the later ones are reported as skipped, exactly
as the workflow does. Add `--dry-run` to print the resolved commands without
executing anything — the quickest way to check what a combination will do.

#### Where BASE_URL comes from

Hosts are read from the environment first and fall back to the public demo site,
mirroring the repository variables CI uses. The runner prints which source it
used, so a run never leaves you guessing what it tested:

| Stage | Environment variable | Fallback |
|---|---|---|
| `dev` | `DEV_BASE_URL`, then `STAGING_BASE_URL` | `https://demoqa.com` |
| `release` | `RELEASE_BASE_URL` | `https://demoqa.com` |
| `production` | `PRODUCTION_BASE_URL` | `https://demoqa.com` |

```bash
DEV_BASE_URL=https://dev.internal node scripts/pipeline.mjs --stage dev --suite smoke
```

```powershell
$env:DEV_BASE_URL='https://dev.internal'; node scripts/pipeline.mjs --stage dev --suite smoke
```

#### npm shortcuts

Run these from the repository root. They are thin wrappers over the same script,
so anything below can also be spelled out with explicit flags:

```bash
npm run dev:smoke              # unit → api → ui, smoke, chromium
npm run dev:regression         # the same, full depth
npm run dev:regression:all     # full depth on all four browsers
npm run release:smoke
npm run release:regression     # full depth, all browsers
npm run production:smoke
npm run test:unit              # one layer only
npm run test:api
npm run test:ui
npm run pipeline -- --stage release --suite ui --browser webkit
npm run pipeline:help
```

The `--` in the last example matters: without it npm keeps the flags for itself
rather than passing them on.

#### The matrix, and what each combination is for

| Combination | Command | Use |
|---|---|---|
| Dev smoke, chromium | `npm run dev:smoke` | The pull-request gate. Fastest useful signal |
| Dev regression, firefox | `node scripts/pipeline.mjs --stage dev --suite regression --browser firefox` | Engine-specific check before promoting |
| Dev regression, all | `npm run dev:regression:all` | What the release stage runs in CI |
| Release regression, all | `npm run release:regression` | Full pre-production sweep |
| Production smoke, webkit | `node scripts/pipeline.mjs --stage production --suite smoke --browser webkit` | Post-deployment verification |
| Unit only | `npm run test:unit` | Sub-second feedback while editing helpers |
| API only | `npm run test:api` | Contract work without a browser |

<p align="center">
  <img src="docs/images/local-pipeline-dev-smoke.png" width="100%" alt="Dev smoke on chromium through the local runner" />
</p>

<p align="center">
  <img src="docs/images/local-pipeline-regression-firefox.png" width="100%" alt="Dev regression on firefox through the local runner" />
</p>

<p align="center">
  <img src="docs/images/local-pipeline-production-webkit.png" width="100%" alt="Production smoke on webkit through the local runner" />
</p>

#### Running it from VS Code

Two panels reach the same commands without typing anything.

**Tasks** — `Ctrl+Shift+P` → **Tasks: Run Task**. Thirteen entries are defined in
[`.vscode/tasks.json`](.vscode/tasks.json):

| Task | Runs |
|---|---|
| **Pipeline: dev smoke (chromium)** | the pull-request gate — also the default test task |
| Pipeline: dev regression (chromium) | full depth, one browser |
| Pipeline: dev regression (all browsers) | what the release stage runs in CI |
| Pipeline: release smoke / regression | pre-production |
| Pipeline: production smoke | post-deployment verification |
| Layer: unit / API / UI only | one layer at a time |
| **Pipeline: custom…** | prompts for stage, suite and browser, then runs it |
| Pipeline: custom… (dry run) | the same prompts, printing the commands instead |
| Docs: collect test metrics | re-runs the suites and rewrites the metrics section |
| Docs: regenerate testing_report.pdf | rebuilds the PDF |

*Pipeline: dev smoke* is the default test task, so `Ctrl+Shift+P` →
**Tasks: Run Test Task** starts it directly. *Pipeline: custom…* uses VS Code's
`pickString` inputs, so the three parameters arrive as dropdowns rather than
remembered flags.

**NPM Scripts** — the panel in the Explorer sidebar (enable with
`"npm.enableScriptExplorer": true` if you do not see it) lists every script in
the root [`package.json`](package.json): `dev:smoke`, `release:regression`,
`production:smoke`, `test:unit`, and so on. Clicking one runs it in a terminal.
Scripts from `playwright/package.json` appear there too, under that folder.

Both routes end up at the same `scripts/pipeline.mjs`, so a task, an npm script
and a hand-typed command produce identical runs.

One detail in the task definitions worth keeping if you edit them: every task is
`"type": "process"`, not `"shell"`. VS Code launches shell tasks with your
default shell, so on Windows a `shell` task would hand `--grep @smoke` to
PowerShell and the tag would vanish — the same bug documented above. `process`
passes the argument array straight to the executable, with nothing in between.

#### Why a runner rather than raw commands

Two bugs in this repository came from shells rather than from tests, and the
runner exists so neither can happen again.

- **`--grep @smoke` silently loses its argument in PowerShell.** `@` is the
  splatting operator, so a bare `@smoke` expands the undefined variable `$smoke`
  to nothing and Playwright reports *"option '-g, --grep <grep>' argument
  missing"* — an error that names Playwright for the shell's doing.
- **Running from the wrong directory** makes `npx` download a throwaway copy of
  Playwright, which then finds no config and reports
  *`Project(s) "chromium" not found. Available projects: ""`*.

The runner spawns every command with an argument array and **no shell**, so
nothing is re-parsed and no quoting rule applies. Paths resolve from the script's
own location rather than the working directory, so it behaves the same from the
root or a subfolder. Inputs are checked against allow-lists before they reach a
command line:

```
--stage staging     →  must be one of: dev, release, production
--browser safari    →  must be one of: chromium, firefox, webkit, msedge, all
```

The network-bound layers get one retry and a per-layer timeout, because
demoqa.com has been measured answering a login in 25–30s and one slow response
should not read as a red suite.

#### Running the real workflow with `act`

[`act`](https://github.com/nektos/act) executes `ci.yml` itself in a container,
which is closer to a GitHub runner than any wrapper can be. It needs Docker, so
it is the optional route; [`.github/act/`](.github/act/) holds the event payloads
and `.actrc` pins an image that already has Java and Node:

```bash
act workflow_dispatch -W .github/workflows/ci.yml -e .github/act/dev-smoke.json
act workflow_dispatch -W .github/workflows/ci.yml -e .github/act/release-regression.json
act workflow_dispatch -W .github/workflows/ci.yml -e .github/act/production-smoke.json
```

Two cautions. `act` runs the promotion jobs too, and those execute real
`git push` commands — every event file here sets `promote: false` for that
reason. And it runs the full browser matrix in containers, so a regression
configuration is considerably slower than the local runner.

<!-- testing-manual:end -->

### Regenerating the PDF

[`testing_report.pdf`](https://github.com/Eyter-Higuera/qa-assessment/raw/main/testing_report.pdf) is this manual, styled, with
the three suites executed and their real output appended:

```bash
python scripts/build_testing_report.py             # run the suites, then render
python scripts/build_testing_report.py --no-run    # render the manual alone
```

The manual is not duplicated in the script — it is read from this README between the
`testing-manual` markers, so the PDF cannot drift from what you are reading now.
Rendering prefers WeasyPrint and falls back to the Chromium that Playwright already
installs, because WeasyPrint needs GTK natively and will not install on a stock
Windows machine without an elevated system install.

## CI/CD

[`.github/workflows/ci.yml`](.github/workflows/ci.yml) is a promotion chain that
runs as **one ordered workflow run**. Every stage is wired to the one before it with
`needs:`, so a stage physically cannot start until its predecessor is green:

```
config → 1. dev tests → promote to release → 2. release tests → promote to main
                                                → 3. deploy production → smoke
```

Unit tests run **once**, before any environment is touched, and gate every entry
point into the chain:

```
config → 0. unit (Vitest) → 1. dev → 2. release → 3. production
                                api (Karate) → ui (Playwright, one leg per browser)
```

They assert pure logic — no browser, no network, no demoqa.com — so their answer
cannot differ between dev, release and production, and running them per stage only
bought three identical answers to the same question. Within each stage the browsers
still wait on the API suite. That job also carries a **coverage gate**: Vitest fails it if statements, branches, functions or lines drop under 80%,
and the run summary shows the four figures with a per-file breakdown.

Coverage is scoped to the code unit tests are responsible for — `src/pages/**` and
`src/utils/api-client.ts` are excluded because the Playwright suite is what
exercises them, and counting them here would measure the absence of Playwright
rather than the quality of these tests. Read the percentage as *"the pure logic is
covered"*, not *"the project is 100% covered"* — most of `src/` is browser-driven
by design. A failed unit job skips the API suite;
a failed API suite skips every browser leg — with `all browsers` selected that is
four runners not spent learning what the first job already knew.

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
| Browser | `chromium`, `firefox`, `webkit`, `msedge`, `all browsers` | `--project=…` (a matrix leg each; `all browsers` runs the four in parallel) |
| Promote | off by default, `eyter_dev` only | whether the run continues past its entry stage |

*Use workflow from* is the fourth input in everything but name: it chooses the entry
stage, which is why there is no target-environment dropdown.

Leave *Promote* unticked and the run tests its entry stage and stops — nothing is
promoted, no branch moves, nothing is deployed. Tick it and the same run continues
from there in order, running your chosen suite and browsers at each test stage it
reaches.

**Promotion is bound to `eyter_dev`.** Ticking *Promote* on a run started from
`release`, `main` or a feature branch fails the run in seconds, before any suite
starts:

> Promotion is only allowed when triggered from the eyter_dev branch.

That guard matters most in the case that looks harmless. A feature branch enters at
the dev stage exactly like `eyter_dev` does, so without it a green feature-branch
run would push its own commit straight at `release` — a commit that never passed the
dev gate as the chain defines it. Manual runs from `release` and `main` are for
testing those stages, not for promoting out of them.

Entering at stage 3 still deploys, promote or not: running this workflow from `main`
is a deployment, not a dry run.

Stage 3 verifies with the suite you selected. A manual run choosing `regression`
runs the regression suite against production after deploying; anything automated —
a push, or a promotion that reached production on its own — confirms the deployment
with `smoke` rather than re-testing the build. Worth knowing before selecting it:
the regression suite registers users and creates data, so on a real production host
it is not a read-only check.

A final `Pipeline result` job asserts that a deployment was actually verified. If
production was deployed and its verification did not pass — failed, or skipped for
any reason — the run goes red. Without it a deploy whose verification never ran
reports green, which is the one way this pipeline can lie to you.

| Run from | Promote off | Promote on |
|---|---|---|
| `eyter_dev` | dev tests | dev → release → deploy → smoke |
| `release` | release tests | release → deploy → smoke |
| `main` | deploy, then production smoke | deploy, then production smoke |

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

Every stage writes a results table to the **run summary page**, so a failure is
readable without downloading anything:

```
## Playwright - dev - smoke - chromium
passed - 5 tests in 19.5s: 5 passed, 0 failed, 0 skipped

| Suite                | Passed | Failed | Skipped | Duration |
| login.spec.ts        |      3 |      0 |       0 |    15.8s |
| registration.spec.ts |      2 |      0 |       0 |     3.7s |
```

When something fails, a second table lists each failing test with the first line
of its error. Both suites feed the same reader
([`.github/scripts/junit-summary.py`](.github/scripts/junit-summary.py)) because both
emit JUnit XML — Playwright through its `junit` reporter, Karate through
`outputJunitXml(true)` on the runners. The step runs under `if: always()`, since the
summary matters most exactly when the suite before it failed.

The full HTML reports are still uploaded for every environment —
`karate-reports-<env>` and `playwright-report-<env>-<browser>`, retained 14 days —
for when the summary is not enough and you want the trace viewer.

## Repository layout

```
Senior_QA_Engineer_Assessment.md   the written submission
docs/test_strategy_design.html     the same document, formatted for reading and print
docs/test_strategy_design.pdf      that document rendered to PDF
playwright/                        web automation — page objects, fixtures, specs
karate/                            API automation — feature files and JUnit runners
testing_report.pdf                 the testing manual as a styled PDF, with real captured output
                                   (linked by absolute raw URL — see the note under The submission)
scripts/build_testing_report.py    regenerates that PDF from the manual below
docs/images/                       screenshots the manual references
.vscode/tasks.json                 pipeline shortcuts for the VS Code task runner
package.json                       npm entry points for the local pipeline
scripts/pipeline.mjs               the local pipeline runner
.github/act/                       event payloads for running ci.yml under act
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
