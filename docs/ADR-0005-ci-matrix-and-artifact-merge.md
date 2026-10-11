# ADR-0005: CI matrix per framework, with one report job that merges artifacts

- Status: Accepted
- Date: 2026-10-11

## Context

The UI suites need different toolchains. Playwright needs browsers installed by Playwright, Cypress is an
Electron binary and Selenium uses the runner's Chrome. The report needs every framework's output in one
place, and a failure in one suite must not hide the results of the others.

## Decision

`.github/workflows/ci.yml` has these jobs:

- `unit` and `api` run the stub tests, the report tests and the pytest API suite.
- `ui` is a matrix over `playwright`, `cypress` and `selenium` with `fail-fast: false`. Each job starts
  one stub on port 3100 and uploads `reports/raw/` as `raw-<framework>`.
- `visual` is manual only, until Linux baselines are committed.
- `perf` runs the k6 smoke and a 30 s Locust run.
- `report` runs `always()` after the others. It merges every `raw-*` artifact into `reports/raw/`, runs
  `python3 -m tools.report`, uploads `site/` and deploys to GitHub Pages on pushes to `main`.

Nightly runs set `STUB_FLAKE_RATE=0.05` for the UI matrix, so the flaky detector has failures to find.

## Consequences

- A failing suite shows up in its own job, and the report still runs.
- Sharding is not implemented. Playwright's `--shard` is available, but each framework has one spec file
  today, so splitting by spec would leave a shard empty. Adding shards is future work.
- The workflow has been checked only for YAML structure locally. It has not run on GitHub.
- The k6 and visual jobs have not run anywhere yet. The visual job stays manual until its baselines exist.
