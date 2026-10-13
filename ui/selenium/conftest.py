"""Shared fixtures for the Selenium storefront scenarios.

- base_url: BASE_URL env var, or the local stub on 127.0.0.1:3100.
- stub_server: session fixture; when BASE_URL is unset it starts `node stub/server.mjs`
  (PORT=3100) and stops it at teardown.
- chrome_service: session fixture; resolves the chromedriver path once per session.
- driver: headless Chrome, one per test.

chromedriver lookup order:
1. CHROMEDRIVER env var (explicit path).
2. An executable named `chromedriver` under SE_CACHE_PATH (no network lookup).
3. Selenium Manager, once per session.
"""

import os
import subprocess
import time
from pathlib import Path

import pytest
import requests
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.selenium_manager import SeleniumManager

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_BASE_URL = "http://127.0.0.1:3100"
HEALTH_TIMEOUT_S = float(os.environ.get("STUB_HEALTH_TIMEOUT_S", "60"))


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
            # Polling a local HTTP server, not a browser wait, so a plain sleep is the right tool.
            time.sleep(0.2)
        yield proc
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()


def _cached_chromedriver():
    """Return an executable chromedriver found under SE_CACHE_PATH, newest path name first."""
    cache = os.environ.get("SE_CACHE_PATH")
    if not cache or not Path(cache).is_dir():
        return None
    candidates = sorted(
        (p for p in Path(cache).rglob("chromedriver") if p.is_file() and os.access(p, os.X_OK)),
        reverse=True,
    )
    return str(candidates[0]) if candidates else None


@pytest.fixture(scope="session")
def chrome_service():
    """Resolve chromedriver once per session and share the Service with every driver."""
    path = os.environ.get("CHROMEDRIVER") or _cached_chromedriver()
    if not path:
        # Falls back to Selenium Manager; this is the only place that may touch the network.
        path = SeleniumManager().binary_paths(["--browser", "chrome"])["driver_path"]
    return Service(executable_path=path)


def _headless_options():
    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--window-size=1280,800")
    return options


@pytest.fixture
def driver(chrome_service):
    drv = webdriver.Chrome(service=chrome_service, options=_headless_options())
    drv.implicitly_wait(0)
    try:
        yield drv
    finally:
        drv.quit()
