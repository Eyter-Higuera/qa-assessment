# Screenshots for the testing manual

The manual in [`../../README.md`](../../README.md) references the images below.
**The seven `local-*.png` files are real captures.** Each is the actual terminal
output of the command it sits under, produced by running it:

```bash
python ../../scripts/capture_terminal_screenshots.py                 # all seven
python ../../scripts/capture_terminal_screenshots.py unit karate-dev # just these
```

That script executes the command, converts its ANSI colour to HTML, renders a
terminal window and screenshots it at 2x. It captures whatever happened — a
failing command produces a screenshot of it failing, which is the point: the
manual then shows the truth and someone fixes the command.

**The three `ci-*.png` files are still placeholders**, and have to be captured by
hand: they are screenshots of GitHub's own UI from a signed-in browser. Drawing
something that resembled them would be a fabrication rather than a capture.
Generate or regenerate placeholders with:

```bash
python ../../scripts/make_placeholder_images.py           # only what is missing
python ../../scripts/make_placeholder_images.py --force   # rewrite every one
```

Without `--force` an existing file is left alone, so the generator can never
overwrite a real capture.

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
