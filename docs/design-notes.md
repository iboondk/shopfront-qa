# Design notes

## Scope

The suite runs the same three storefront scenarios (catalog listing, product detail, add to cart) in
Playwright, Cypress and Selenium. Each test name carries the scenario ID, and each suite writes JUnit
XML to `reports/raw/<framework>/<run-id>/`. The API tests (pytest, REST and GraphQL), the k6 and Locust
smoke tests, and a static report site cover the rest.

## Target

The default target is a local stub storefront: a Node server on `node:http` with no database. It serves
server-rendered HTML with stable `data-testid` hooks, a Medusa v2-shaped REST API and a Saleor-shaped
GraphQL API, with environment-controlled fault injection (latency, flaky responses, seeded).

Suites read `BASE_URL`, `API_URL` and `GRAPHQL_URL`, so the optional Saleor stack in
`infra/saleor/` needs no test changes.

## Decisions

- **Stub first.** A full commerce stack is slow to start and needs Docker. A stub gives deterministic
  data, so assertions can be exact. Saleor is kept as an optional target (see ADR-0004).
- **One contract, one format.** Shared scenario IDs and JUnit XML make the three UI frameworks
  comparable (see ADR-0002).
- **Stdlib-only report.** The generator reads the JUnit XML and k6 summaries with the Python standard
  library, so there is no install step, and the output deploys as a static page (see ADR-0003).
- **No hand-typed timings.** Timing numbers come from the generated report site, not from the docs.

## Open items

- Linux visual baselines are not committed yet, so the visual job is manual only.
- Playwright sharding in CI, and splitting the Cypress and Selenium suites by spec as they grow.
- Running the k6 smoke and the Saleor stack in CI.
