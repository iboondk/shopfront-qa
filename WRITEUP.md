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
that output into a static HTML site with timing comparisons and flaky-test detection. The README has the diagram.

## Key decisions

- **Stub first (ADR-0001).** A full commerce stack needs Postgres, Redis and a Next.js build. The stub is
  deterministic, so assertions can be exact, and it runs without Docker.
- **One scenario contract (ADR-0002).** Scenario IDs appear in every test name, and JUnit XML is the only result format.
- **Stdlib-only report (ADR-0003).** No install step, and the output deploys as a plain static page.
- **Saleor as an optional real target (ADR-0004).** The GraphQL tests can run against the official image with `TARGET=saleor`.
- **CI matrix with artifact merge (ADR-0005).** A failing framework does not hide the others' results.

## Results

Only what was actually run is reported. The packaging session ran these on a macOS machine (Node 24, Python 3.10). A later review session re-ran the stub, report, API and Selenium suites on the same machine with the same counts; the API and Selenium runs started their own stub. The stub start-up wait is configurable (`STUB_HEALTH_TIMEOUT_S`, default 60 s), because the external volume was slow to start the stub in one run:

- Stub unit tests: 16 of 16 passed.
- Report generator tests: 31 of 31 passed.
- API tests (REST and GraphQL): 20 of 20 passed.
- Selenium scenarios: 3 of 3 passed.
- Playwright scenarios: 0 of 3 passed here. The suite could not open a page (`browserContext.newPage` timed out).
  In a separate probe, the `load` event never fired, while DOMContentLoaded did and all 8 product cards rendered.
  The root cause is not yet known.
- Cypress: the full pipeline hung after an Electron network-service crash, so it is not verified this session.
- Not run: k6 (not installed), the Saleor compose stack (no Docker), and the CI workflow (not run on GitHub).

No benchmark or timing numbers are stated in this project. Timings come only from the generated report site.

## What I would do next

1. Fix the Playwright `load` hang and re-run all three UI suites in one clean pass.
2. Commit Linux visual baselines so the visual job can run automatically.
3. Add Playwright sharding, and split the Cypress and Selenium suites by spec as they grow.
4. Run the k6 smoke and the Saleor stack in CI, and publish the first real results through the report.
5. Add a Medusa target once an official image or a reliable build is available.
