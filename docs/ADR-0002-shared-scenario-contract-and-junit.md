# ADR-0002: One scenario contract, and JUnit XML as the result format

- Status: Accepted
- Date: 2026-10-11

## Context

Three UI frameworks (Playwright, Cypress, Selenium) need to be compared. A comparison only means
something if each framework runs the same steps and reports under the same names.

## Decision

- Every UI framework implements the same three scenarios: `catalog.lists-products`,
  `product.shows-detail` and `cart.add-item`. The scenario ID appears in the test name.
- Each suite writes JUnit XML to `reports/raw/<framework>/<run-id>/junit.xml`. Playwright uses its
  built-in junit reporter, Cypress uses the mocha `junit` reporter, and pytest uses `--junitxml`. The k6
  smoke writes `summary.json` into `reports/raw/k6/<run-id>/`.
- A "run-id" is one attempt. Locally it is `RUN_ID` (default `local`). In CI it is
  `<run_id>-<run_attempt>-<framework>`.

## Consequences

- The report generator reads one format and does not need a plugin for each framework.
- Flaky detection compares the same test ID across run-ids, and it can also read Playwright's
  retry-annotated results.
- Scenario IDs in test names are a convention, not something the framework enforces. A rename in one
  suite breaks the comparison silently, so the names are checked by review and by the report tests.
- JUnit has no standard field for timings beyond the test case duration. The timing comparison relies on
  that field only.
