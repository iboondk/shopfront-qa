# Shopfront-QA: Architecture

Shopfront-QA is a test automation suite. It runs the same storefront scenarios through
Playwright, Cypress and Selenium side by side and compares timings. It also has API tests
(REST + GraphQL), visual regression, k6 and Locust performance tests, a GitHub Actions
matrix with sharding, flaky-test detection, and a static report site generator.

## 1. Key decision: a local "stub storefront" first, a real storefront as an option

Docker is not available on the dev machine, and a full Medusa or Saleor stack is heavy
(Postgres + Redis + API + a Next.js storefront build). So the suite targets a
**dependency-light stub storefront** (`stub/`) by default:

- a tiny Node HTTP server with deterministic seed data;
- server-rendered HTML pages with stable `data-testid` hooks (catalog, product detail, cart);
- a **Medusa v2-shaped REST API** (`/store/products`, `/store/carts`, `x-publishable-api-key` header);
- a **Saleor-shaped GraphQL API** (`POST /graphql`, `products(first, channel, search)` with an `edges/node` connection);
- optional fault injection (`STUB_LATENCY_MS`, `STUB_FLAKE_RATE`, `STUB_SEED`) so that the
  flaky-test detector and the perf tests have something real to measure.

Real-target mode is opt-in. `infra/saleor/docker-compose.yml` uses the official Saleor
images (`ghcr.io/saleor/saleor`, postgres, redis). The GraphQL API tests can run against it with
`TARGET=saleor`. Medusa v2 has no official prebuilt image, so it is documented as future work
and is not claimed. Every suite reads `BASE_URL` (UI) and `API_URL` / `GRAPHQL_URL`, so it
can point at any target without code changes.

## 2. Tech choices

| Concern | Choice | Why |
|---|---|---|
| Stub storefront | Node 20+ `node:http`, `graphql@16.9.0` | No framework, starts in under 100 ms, same server in CI and locally |
| UI: Playwright | `@playwright/test@1.48.2`, TypeScript | Built-in sharding (`--shard`), retries, JUnit reporter, screenshots |
| UI: Cypress | `cypress@13.15.2`, JS | Industry comparison point; JUnit through the built-in `junit` mocha reporter |
| UI: Selenium | Python `selenium==4.25.0` + `pytest==8.3.3` | Selenium Manager fetches chromedriver itself, so no Java and no Grid are needed |
| Visual regression | Playwright `toHaveScreenshot` | Baselines per platform (`{platform}` in path); CI owns the linux baselines |
| API tests | `pytest` + `requests==2.32.3` | REST + GraphQL in one runner, JUnit through `--junitxml` |
| Perf | k6 (`perf/k6/*.js`) + Locust `locust==2.31.8` | k6 for threshold-gated smoke, Locust for user-behaviour modelling |
| Reporting | Python 3.10 stdlib only (`tools/report/`) | Parses JUnit XML + k6 summary JSON, then writes a static HTML site to `site/` |
| CI | GitHub Actions | Matrix over frameworks, artifact upload, report job, Pages deploy |

Shared scenario contract: every UI framework implements the same three scenarios, and
the scenario ID appears in the **test name**. That lets the report line them up across frameworks:

| Scenario ID | Steps |
|---|---|
| `catalog.lists-products` | open `/`, see 8 `product-card` items, first title is "Classic Tee" |
| `product.shows-detail` | open `/`, click "Classic Tee", see `product-title` and price "$25.00" |
| `cart.add-item` | open `/products/classic-tee`, click `add-to-cart`, land on `/cart`, `cart-count` = "1" |

Raw results layout (the input contract of the report generator):
`reports/raw/<framework>/<run-id>/junit.xml`, where framework is one of `playwright`, `cypress`,
`selenium`, `api`, plus `reports/raw/k6/<run-id>/summary.json`. A "run-id" is one
attempt (CI: `${{ github.run_id }}-${{ github.run_attempt }}-shard<N>`). Flakiness is
detected by comparing the same test across run-ids, and by looking at Playwright's
retry-annotated results.

## 3. Directory layout

```
shopfront-qa/
  docs/architecture.md
  package.json                 # root npm workspace-less scripts; devDeps: playwright, cypress, graphql
  .env.example                 # BASE_URL, API_URL, GRAPHQL_URL, PUBLISHABLE_KEY, TARGET
  requirements.txt             # selenium, pytest, requests, locust
  stub/
    server.mjs                 # createServer({port, seed, flakeRate, latencyMs}) + CLI entry
    graphql.mjs                # schema + resolvers
    data/products.json         # 8 deterministic products
    server.test.mjs            # node --test
  ui/
    playwright/
      playwright.config.ts
      tests/scenarios.spec.ts
      tests/visual.spec.ts
      __screenshots__/         # baselines (per platform)
    cypress/
      cypress.config.js
      e2e/scenarios.cy.js
    selenium/
      conftest.py
      test_scenarios.py
  api/
    conftest.py
    test_rest_products.py
    test_rest_cart.py
    test_graphql.py
  perf/
    k6/smoke.js
    locust/locustfile.py
  tools/
    report/
      __init__.py
      junit.py                 # parse JUnit XML -> TestResult records
      flaky.py                 # detect flaky tests across runs
      timing.py                # per-framework/per-scenario timing comparison
      k6.py                    # parse k6 --summary-export JSON
      site.py                  # render static HTML site
      __main__.py              # python -m tools.report --raw reports/raw --out site
    tests/                     # unittest + fixture XML/JSON
    scripts/run-ui-all.sh      # starts stub, runs 3 UI frameworks, writes reports/raw
  infra/
    saleor/docker-compose.yml  # optional real target (not run locally: no docker)
  reports/  site/              # generated, gitignored
```

## 4. Environment and caches

The author's machine keeps heavy caches on an external volume. These paths are machine-specific, so they
live in an untracked file, `tools/scripts/local.env` (copied from `local.env.example`). The repository
never hard-codes them. `run-ui-all.sh` sources that file and sets each cache variable only when the
variable is unset and its directory exists.

The script does not export the cache variables unconditionally. Without the external volume,
exporting machine-specific paths would make npm, pip, Cypress and Selenium try to write there, so the
script skips the export. Where the configured directories exist, it exports `npm_config_cache`,
`PIP_CACHE_DIR`, `CYPRESS_CACHE_FOLDER`, `SE_CACHE_PATH` and `PLAYWRIGHT_BROWSERS_PATH`.

The Python venv lives at `./.venv` (gitignored). No real credentials: the publishable
key is the placeholder `pk_test_stub` in `.env.example`.

Tooling seen on the dev machine: node 24, npm 11, python 3.10, git. **Not available:** docker,
k6, java. So the Saleor compose and k6 run only in CI. Locally they get only syntax and
structure checks.

## 5. CI design

- `ui` job: matrix over `framework: [playwright, cypress, selenium]`. Sharding (Playwright `--shard`,
  spec-file splits for Cypress and Selenium) is designed for but not yet wired in; see ADR-0005.
- `api` job, `visual` job (Playwright linux baselines), `perf` job (k6 via `grafana/setup-k6-action`,
  Locust headless 30 s against the stub).
- `report` job: downloads all `reports/raw/**` artifacts, runs `python -m tools.report`,
  uploads `site/`, and deploys to GitHub Pages on `main`.
- Nightly schedule runs the UI matrix 3× with `STUB_FLAKE_RATE=0.05` to feed the flaky detector.

## 6. Components

- **Stub storefront**: HTML + REST + GraphQL + fault injection, unit-tested with `node --test`.
- **Report generator**: JUnit/k6 parsing, timing comparison, flaky detection, static site; unit-tested with fixtures. Independent of the stub.
- **Playwright UI + visual regression**: 3 scenarios + 2 screenshot tests, JUnit to `reports/raw/playwright`.
- **Cypress + Selenium UI**: the same 3 scenarios, JUnit to `reports/raw/{cypress,selenium}`, plus `run-ui-all.sh`.
- **API tests**: REST (products, cart, auth negative) + GraphQL, JUnit to `reports/raw/api`.
- **Perf**: k6 smoke with thresholds + Locust user model; Saleor compose file.

## 7. Reporting principles

- No benchmark or timing numbers are written into docs by hand. The report site shows only what it parsed.
- Visual baselines produced on macOS are marked as darwin baselines. CI generates linux ones.
- Anything that could not run locally (docker, k6, Saleor) is documented as "not run".
