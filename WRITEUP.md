# Shopfront-QA: write-up

## Problem

Teams often pick a UI test framework by opinion rather than evidence. A fair comparison of Playwright,
Cypress and Selenium needs the same scenarios, the same report format and the same target. Shopfront-QA
provides all three, and adds API, performance and flakiness coverage so the comparison goes beyond clicks.

## Architecture

A small Node server (`stub/`, `node:http`, no database) acts as the storefront. It serves server-rendered
HTML with stable `data-testid` hooks, a Medusa-shaped REST API and a Saleor-shaped GraphQL API. The suites
are Playwright, Cypress and Selenium for the UI, pytest for API tests, and k6 and Locust for performance.
Each suite writes JUnit XML to `reports/raw/<framework>/<run-id>/`. A stdlib-only Python generator turns
that output into a static HTML site with timing comparisons and flaky-test detection.

## Key decisions

- **Stub first (ADR-0001).** A full commerce stack needs Postgres, Redis and a Next.js build. The stub is
  deterministic, so assertions can be exact, and it runs without Docker.
- **One scenario contract (ADR-0002).** Scenario IDs appear in every test name, and JUnit XML is the only result format.
- **Stdlib-only report (ADR-0003).** No install step, and the output deploys as a plain static page.
- **Saleor as an optional real target (ADR-0004).** The GraphQL tests can run against the official image with `TARGET=saleor`.
- **CI matrix with artifact merge (ADR-0005).** A failing framework does not hide the others' results.

## Results

Run on macOS (Python 3.10); only executed suites are reported.

- Unit tests: stub 16 of 16, report generator 31 of 31. API tests (REST and GraphQL): 20 of 20.
- UI scenarios, one `run-ui-all.sh` pass on Node 20: Playwright 3 of 3, Cypress 3 of 3, Selenium 3 of 3.
  Playwright visual tests: 2 of 2 against the darwin baselines.
- Locust 20 s smoke: 0 failures.
- Cypress 13 hangs under Node 24, so the project pins Node 20 (`.nvmrc`, as CI does).
- Not run: k6 (not installed), Saleor compose (no Docker), CI workflow (not run on GitHub).

No benchmark or timing numbers are stated in this project. Timings come only from the generated report site.

## What I would do next

1. Get a green CI run on GitHub and link it from the README.
2. Commit Linux visual baselines so the visual job can run automatically.
3. Add Playwright sharding, and split the Cypress and Selenium suites by spec as they grow.
4. Run the k6 smoke and the Saleor stack in CI, and publish the first real results through the report.
5. Add a Medusa target once an official image or a reliable build is available.
