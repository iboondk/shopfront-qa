# ADR-0001: A local stub storefront first, a real storefront as an option

- Status: Accepted
- Date: 2026-10-11

## Context

The suite has to run the same shopping scenarios across three UI frameworks, an API suite and
performance tests. A full Medusa or Saleor stack needs Postgres, Redis, an API and a Next.js build. The
development machine has no Docker, and CI should not depend on a database to show that the tests work.

## Decision

The default target is `stub/`, a small Node server on `node:http` with no framework and no database. It
serves:

- server-rendered HTML pages with stable `data-testid` hooks (catalog, product detail, cart);
- a Medusa v2-shaped REST API (`/store/products`, `/store/carts`, `x-publishable-api-key`);
- a Saleor-shaped GraphQL API (`POST /graphql`, `products(first, channel, search)` with `edges/node`);
- optional fault injection through `STUB_LATENCY_MS`, `STUB_FLAKE_RATE` and `STUB_SEED`.

The seed data is deterministic (8 products), so assertions can be exact, for example "first title is
Classic Tee" and "$25.00".

## Consequences

- The stub typically starts in under a second. Slow disks, such as an external volume, can take longer,
  so the start-up wait is configurable (`STUB_HEALTH_TIMEOUT_S`, default 60 s). It runs the same way on a
  laptop and in CI.
- Fault injection gives the flaky-test detector and the performance tests something real to measure.
- The stub is not a real storefront. A passing run does not prove anything about Saleor or Medusa
  behaviour. This is why the real target is opt-in (ADR-0004).
- Every suite reads `BASE_URL`, `API_URL` and `GRAPHQL_URL`, so pointing a suite at another target needs
  no code change.
