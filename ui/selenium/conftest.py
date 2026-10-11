"""Shared fixtures for the Selenium storefront scenarios.

- base_url: BASE_URL env var, or the local stub on 127.0.0.1:3100.
- stub_server: session fixture; when BASE_URL is unset it starts `node stub/server.mjs`
  (PORT=3100) and stops it at teardown.
- driver: headless Chrome, one per test.
"""

import os
import subprocess
import time
from pathlib import Path

import pytest
import requests
from selenium import webdriver
from selenium.webdriver.chrome.options import Options

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_BASE_URL = "http://127.0.0.1:3100"
HEALTH_TIMEOUT_S = 10.0


@pytest.fixture(scope="session")
def base_url():
    return os.environ.get("BASE_URL") or DEFAULT_BASE_URL


@pytest.fixture(scope="session", autouse=True)
def stub_server(base_url):
    if os.environ.get("BASE_URL"):
        yield None
        return

    env = dict(os.environ, PORT="3100")
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
                if requests.get(base_url + "/health", timeout=1).ok:
                    break
            except requests.RequestException:
                pass
            if proc.poll() is not None:
                raise RuntimeError("stub server exited before becoming healthy")
            if time.monotonic() > deadline:
                raise RuntimeError(f"stub server not healthy at {base_url}/health after {HEALTH_TIMEOUT_S}s")
            time.sleep(0.2)
        yield proc
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()


@pytest.fixture
def driver():
    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--window-size=1280,800")
    drv = webdriver.Chrome(options=options)
    drv.implicitly_wait(0)
    try:
        yield drv
    finally:
        drv.quit()
