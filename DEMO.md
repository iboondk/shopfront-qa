# Demo script: recording a GIF or Loom

Goal: a 60 to 90 second recording that shows the stub storefront, the same three scenarios running in
three frameworks, and the static report site. Record at 1280x800 so it matches the Playwright viewport.

## Before you record

1. Set up once, following the Quick start in [README.md](README.md): `nvm use` (Node 20), `npm ci`,
   the `.venv`, and `npx playwright install chromium`.
2. Use a clean terminal with a large font (16 to 18 pt) and a light theme. Close other windows.
3. Clear old output so the recording shows only this run:
   ```bash
   rm -rf reports/raw site test-results
   ```
4. Pick a recorder: Loom for a shareable link, or LICEcap / Kap / ScreenToGif for a GIF. Keep GIFs under
   about 10 MB by recording only the terminal and the browser window.

## Script

| # | Time | On screen | Say or show | Command or action |
|---|---|---|---|---|
| 1 | 0:00 | Repo root in the editor | "Shopfront-QA: one set of storefront scenarios in three UI frameworks, plus API, perf and reports." | Show the file tree and the README architecture diagram. |
| 2 | 0:10 | Terminal | "The default target is a local stub. No Docker, no database." | `npm run stub` |
| 3 | 0:20 | Browser | "The catalog is server-rendered with stable test IDs." | Open `http://127.0.0.1:3100`. Point at the 8 product cards. |
| 4 | 0:30 | Browser | "Product detail and add-to-cart." | Click "Classic Tee", then "Add to cart". Show the cart count of 1. Then press `Ctrl+C` in the stub terminal, so port 3100 is free for step 5. |
| 5 | 0:40 | Terminal, second tab | "One command runs all three UI suites against one stub, then builds the report." | `bash tools/scripts/run-ui-all.sh` |
| 6 | 0:50 | Terminal | "Playwright runs the three scenarios in parallel." | Let the list output scroll. Pause on the final "3 passed" line. |
| 7 | 1:00 | Terminal | "Cypress and Selenium run the same scenario IDs." | Pause on the Cypress "All specs passed" line and the Selenium "3 passed" line. |
| 8 | 1:10 | Terminal | "The report reads the JUnit XML. It does not hand-type results." | Show the `wrote N files to site` line. |
| 9 | 1:15 | Browser | "The report is a static page. It shows framework totals, timings and flaky tests from the parsed runs." | Open `site/index.html`. Scroll the framework table and the flaky section. |
| 10 | 1:30 | Editor | "Results are kept in `reports/raw`, and CI uploads them as artifacts." | Show `.github/workflows/ci.yml`, the `ui` matrix. |

Stop the recording at about 1:30.

## Fallback script: record now, with Selenium only

The full script above was verified in the last local audit: `run-ui-all.sh` passed under Node 20 (run
`nvm use` first, because Cypress 13 hangs under Node 24). Use this fallback only if Playwright or Cypress
fails on the recording machine.

| # | Time | On screen | Say or show | Command or action |
|---|---|---|---|---|
| 5 | 0:40 | Terminal, second tab | "One command runs the Selenium scenarios against a stub that the suite starts itself." | `RUN_ID=demo npm run test:se` |
| 6 | 0:50 | Terminal | "Selenium runs the same three scenario IDs as the other frameworks." | Pause on the final "3 passed" line. |
| 7 | 1:00 | Terminal | "Playwright and Cypress run the same scenarios. Their results go into the same report." | Do not show their output. Say this line over the Selenium output, or cut it. |
| 8 | 1:10 | Terminal | "The report reads the JUnit XML. It does not hand-type results." | Run `python3 -m tools.report --raw reports/raw --out site` and show the `wrote N files to site` line. |

Steps 1 to 4, 9 and 10 stay as written. Prefer the full script, and cite the CI run if one exists.

## Notes for the editor

- Record the full script only after `npm run test:pw` and `npm run test:cy` pass on your machine. Otherwise
  use the fallback above.
- Cut the stub start-up wait if it runs long. Do not speed up timing output in a way that makes the
  numbers look different from the real run.
- Do not show timing numbers in captions unless they are copied from the generated report.
- The `run-ui-all.sh` run takes a few minutes, mostly for Selenium. Cut the middle of that step and keep
  the first and last lines.
- The stub listens on `127.0.0.1` only. Nothing in the recording needs a real account or a real key.
- Keep `.env` out of frame. The repository only ships `.env.example`, with placeholder values.

## After recording

- Stop the stub: `Ctrl+C` in its terminal. `run-ui-all.sh` stops its own stub automatically.
- Link the recording or the GIF from the README, under the architecture diagram.
