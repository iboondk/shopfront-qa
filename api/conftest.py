"""Shared fixtures for the API suite.

REST tests follow the Medusa v2 store API shape; GraphQL tests follow the Saleor shape.

- target: TARGET env var, default 'stub'. REST test modules skip when target == 'saleor'.
- stub_server: session fixture. When API_URL is unset it starts `node stub/server.mjs` on
  PORT 3101, polls /health for up to STUB_HEALTH_TIMEOUT_S seconds (default 60), and
  terminates the process at teardown.
  It is not autouse, so a run that sets API_URL (for example TARGET=saleor) never starts it.
- api_url: API_URL env var, or the stub on http://127.0.0.1:3101.
- graphql_url: GRAPHQL_URL env var, or api_url + '/graphql'.
- publishable_key: PUBLISHABLE_KEY env var, or the placeholder 'pk_test_stub'.
- store: requests.Session with x-publishable-api-key set. Every request has timeout=10.
- gql: POSTs {query, variables}, asserts HTTP 200, returns the parsed JSON body.
- gql_raw: POSTs any body without a status assertion, for negative GraphQL tests.
"""

import os
import subprocess
import time
from pathlib import Path

import pytest
import requests

REPO_ROOT = Path(__file__).resolve().parents[1]
STUB_PORT = 3101
STUB_URL = f"http://127.0.0.1:{STUB_PORT}"
HEALTH_TIMEOUT_S = float(os.environ.get("STUB_HEALTH_TIMEOUT_S", "60"))
REQUEST_TIMEOUT_S = 10


class _TimeoutSession(requests.Session):
    """requests.Session that applies REQUEST_TIMEOUT_S to every call unless overridden."""

    def request(self, method, url, **kwargs):
        kwargs.setdefault("timeout", REQUEST_TIMEOUT_S)
        return super().request(method, url, **kwargs)


@pytest.fixture(scope="session")
def target():
    return os.environ.get("TARGET", "stub")


@pytest.fixture(scope="session")
def stub_server():
    if os.environ.get("API_URL"):
        yield None
        return

    env = dict(os.environ, PORT=str(STUB_PORT), STUB_LATENCY_MS="0", STUB_FLAKE_RATE="0")
    proc = subprocess.Popen(
        ["node", "stub/server.mjs"],
        cwd=str(REPO_ROOT),
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    try:
        deadline = time.monotonic() + HEALTH_TIMEOUT_S
        while True:
            try:
                if requests.get(STUB_URL + "/health", timeout=1).ok:
                    break
            except requests.RequestException:
                pass
            if proc.poll() is not None:
                raise RuntimeError("stub server exited before becoming healthy")
            if time.monotonic() > deadline:
                raise RuntimeError(f"stub server not healthy at {STUB_URL}/health after {HEALTH_TIMEOUT_S}s")
            time.sleep(0.2)
        yield proc
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()


@pytest.fixture(scope="session")
def api_url(stub_server):
    return (os.environ.get("API_URL") or STUB_URL).rstrip("/")


@pytest.fixture(scope="session")
def graphql_url(api_url):
    return os.environ.get("GRAPHQL_URL") or api_url + "/graphql"


@pytest.fixture(scope="session")
def publishable_key():
    return os.environ.get("PUBLISHABLE_KEY") or "pk_test_stub"


@pytest.fixture
def store(publishable_key):
    session = _TimeoutSession()
    session.headers.update({"x-publishable-api-key": publishable_key})
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def gql(store, graphql_url):
    def _gql(query, variables=None):
        body = {"query": query}
        if variables is not None:
            body["variables"] = variables
        resp = store.post(graphql_url, json=body)
        assert resp.status_code == 200, f"GraphQL HTTP {resp.status_code}: {resp.text[:300]}"
        return resp.json()

    return _gql


@pytest.fixture
def gql_raw(store, graphql_url):
    def _post(body):
        if isinstance(body, str):
            return store.post(graphql_url, data=body, headers={"content-type": "application/json"})
        return store.post(graphql_url, json=body)

    return _post
