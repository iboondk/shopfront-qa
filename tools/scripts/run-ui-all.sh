#!/usr/bin/env bash
# Runs the three UI suites (Playwright, Cypress, Selenium) against one shared stub storefront.
# Each suite runs even if an earlier one failed; the final exit status reflects all of them.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$REPO_ROOT"

# Optional machine-specific settings (cache locations and the like) live in an untracked file.
# Copy tools/scripts/local.env.example to tools/scripts/local.env to use them.
if [[ -f "$REPO_ROOT/tools/scripts/local.env" ]]; then
  # shellcheck disable=SC1091
  source "$REPO_ROOT/tools/scripts/local.env"
fi

# Set a cache variable only when the caller has not already set it and its parent directory exists.
# On machines without the external cache volume, the tools fall back to their default locations.
set_cache_var() {
  local name="$1" dir="$2"
  if [[ -z "${!name:-}" && -d "$(dirname "$dir")" ]]; then
    export "$name=$dir"
  fi
  return 0
}
set_cache_var npm_config_cache /Volumes/Hazel/caches/npm
set_cache_var PIP_CACHE_DIR /Volumes/Hazel/caches/pip
set_cache_var PLAYWRIGHT_BROWSERS_PATH /Volumes/Hazel/caches/ms-playwright
set_cache_var CYPRESS_CACHE_FOLDER /Volumes/Hazel/caches/cypress
set_cache_var SE_CACHE_PATH /Volumes/Hazel/caches/selenium

export RUN_ID="${RUN_ID:-local-$(date +%s)}"
PORT=3100
export BASE_URL="http://127.0.0.1:${PORT}"

STUB_PID=""
cleanup() {
  if [[ -n "$STUB_PID" ]] && kill -0 "$STUB_PID" 2>/dev/null; then
    kill "$STUB_PID" 2>/dev/null || true
    wait "$STUB_PID" 2>/dev/null || true
  fi
}
trap cleanup EXIT INT TERM

echo "[run-ui-all] RUN_ID=${RUN_ID} BASE_URL=${BASE_URL}"
mkdir -p reports
PORT="$PORT" node stub/server.mjs >"reports/stub-${RUN_ID}.log" 2>&1 &
STUB_PID=$!

healthy=0
for _ in $(seq 1 50); do
  if curl -fsS "${BASE_URL}/health" >/dev/null 2>&1; then
    healthy=1
    break
  fi
  if ! kill -0 "$STUB_PID" 2>/dev/null; then
    break
  fi
  sleep 0.2
done
if [[ "$healthy" -ne 1 ]]; then
  echo "[run-ui-all] stub did not become healthy at ${BASE_URL}/health" >&2
  exit 1
fi
echo "[run-ui-all] stub healthy"

status=0
npm run test:pw || status=1
npm run test:cy || status=1
npm run test:se || status=1

if [[ -d tools/report ]]; then
  python3 -m tools.report --raw reports/raw --out site || status=1
fi

echo "[run-ui-all] exit status ${status}"
exit "$status"
