# ADR-0004: Saleor in Docker Compose as an optional real target, not the default

- Status: Accepted
- Date: 2026-10-11

## Context

The GraphQL tests should be checked against a real GraphQL commerce API, not only against the stub. Saleor
publishes an official image, but a Saleor stack needs Postgres and Redis. Medusa v2 has no official prebuilt
image, so it cannot be run the same way.

## Decision

`infra/saleor/docker-compose.yml` defines `db` (postgres 15), `cache` (redis 7), `migrate` (runs
`migrate` and `populatedb`) and `api` (`ghcr.io/saleor/saleor:3.20`). `api` waits for `migrate` to finish
successfully, so one `docker compose up` brings it up on a migrated database. The API tests run against it
with `TARGET=saleor` and `GRAPHQL_URL`. The REST tests skip when `TARGET=saleor`.

Medusa is listed as future work and is not claimed to work.

## Consequences

- Real-target mode is available to anyone with Docker, with no change to the test code.
- The compose file is not run by default and is not part of the CI matrix. It was checked only for YAML
  structure locally, because Docker is not installed on the development machine. Any statement about it
  working needs a real run first.
- Placeholder secrets only. `.env.example` holds `change-me-local-only`, and real values belong in the
  gitignored `infra/saleor/.env`.
