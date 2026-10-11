"""Parse k6 --summary-export JSON files."""

from __future__ import annotations

import json
from pathlib import Path


def _metric(summary: dict, name: str) -> dict:
    """Return the values of one metric in either export shape.

    --summary-export writes the flat form: {"metrics": {"name": {"p(95)": 1.0}}}.
    k6's handleSummary data nests the values: {"metrics": {"name": {"values": {"p(95)": 1.0}}}}.
    Both shapes are accepted, so a nested file cannot turn every metric into None.
    """
    metrics = summary.get("metrics") or {}
    metric = metrics.get(name)
    if not isinstance(metric, dict):
        return {}
    nested = metric.get("values")
    return nested if isinstance(nested, dict) else metric


def _number(value):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    return value


def parse_k6_summary(path: Path) -> dict:
    """Return the headline k6 metrics. Any metric absent from the file is None."""
    summary = json.loads(path.read_text(encoding="utf-8"))
    duration = _metric(summary, "http_req_duration")
    reqs = _metric(summary, "http_reqs")
    failed = _metric(summary, "http_req_failed")
    checks = _metric(summary, "checks")

    failed_rate = failed.get("value")
    if failed_rate is None:
        failed_rate = failed.get("rate")

    return {
        "http_req_duration_p95_ms": _number(duration.get("p(95)")),
        "http_req_duration_avg_ms": _number(duration.get("avg")),
        "http_reqs": _number(reqs.get("count")),
        "http_req_failed_rate": _number(failed_rate),
        "checks_passes": _number(checks.get("passes")),
        "checks_fails": _number(checks.get("fails")),
    }


def load_k6(raw_dir: Path) -> list[tuple[str, dict]]:
    """Return (run_id, metrics) for every raw_dir/k6/<run-id>/summary.json."""
    k6_dir = raw_dir / "k6"
    if not k6_dir.is_dir():
        return []
    runs: list[tuple[str, dict]] = []
    for run_dir in sorted(p for p in k6_dir.iterdir() if p.is_dir()):
        summary = run_dir / "summary.json"
        if summary.is_file():
            runs.append((run_dir.name, parse_k6_summary(summary)))
    return runs
