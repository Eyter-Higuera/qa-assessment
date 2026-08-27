# Screenshots for the testing manual

The manual in [`../../README.md`](../../README.md) references the images below.
They are intentionally not committed — capture them yourself and drop them in
here, and both the README and `testing_manual_report.pdf` pick them up with no
further changes.

Until a file exists, the PDF renders a labelled placeholder box in its place
rather than a broken image, so the report is always publishable.

| File | What to capture |
|---|---|
| `local-unit-coverage.png` | `npm run test:unit -- --coverage` — the coverage summary table in the terminal |
| `local-karate-dev.png` | `mvn test -Dtest=SmokeTest -Dkarate.env=dev` — the scenario summary |
| `local-karate-release.png` | `mvn test -Dtest=BookStoreApiTest -Dkarate.env=release` |
| `local-karate-production.png` | `mvn test -Dtest=SmokeTest -Dkarate.env=production` |
| `local-playwright-dev.png` | Playwright smoke on chromium |
| `local-playwright-release.png` | Playwright regression across all four browsers |
| `local-playwright-production.png` | Playwright smoke on msedge |
| `ci-scenario-a-eyter-dev.png` | Actions graph of a full chain run from `eyter_dev` |
| `ci-scenario-b-release-main.png` | Actions graph of a run started from `release` or `main` |
| `ci-job-summary.png` | The run summary page showing the coverage, Karate and Playwright tables |

Keep them narrow enough to stay legible on an A4 page — roughly 1200px wide is
plenty.
