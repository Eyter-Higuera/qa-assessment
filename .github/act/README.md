# Running the workflow with `act`

`act` executes the real `ci.yml` in a container, which is the closest thing to a
GitHub runner you can get locally. It needs Docker, so it is the *optional*
route — [`scripts/pipeline.mjs`](../../scripts/pipeline.mjs) reproduces the same
stages, order and parameters with no container and is what the manual documents.

Install `act` and Docker, then from the repository root:

```bash
# Dev smoke on chromium — the pull-request gate
act workflow_dispatch -W .github/workflows/ci.yml -e .github/act/dev-smoke.json

# Release regression across every browser
act workflow_dispatch -W .github/workflows/ci.yml -e .github/act/release-regression.json

# Production smoke
act workflow_dispatch -W .github/workflows/ci.yml -e .github/act/production-smoke.json
```

The event files set `inputs` exactly as the Run workflow form would, and
`.actrc` pins an image with Java and Node already present so the Maven and
Playwright steps do not have to install a toolchain on every run.

Two caveats worth knowing before you rely on this:

- **The promotion jobs push branches.** `act` will attempt real `git push`
  commands against `origin`. Run promoting configurations only if you mean it,
  or keep `promote` false — every event file here does.
- **`act` runs the whole graph**, including the browser matrix. A
  `release-regression` run is four browser legs in containers; expect it to be
  considerably slower than the local runner.
