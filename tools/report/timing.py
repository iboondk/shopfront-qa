"""Per-scenario timing comparison and per-framework totals."""

from __future__ import annotations

import statistics

from .junit import TestResult


def compare_timings(results: list[TestResult]) -> list[dict]:
    """One row per scenario, using only passed results that carry a scenario ID.

    Each row looks like {"scenario": ..., "playwright": {"runs", "median_s", "min_s", "max_s"}, ...}.
    A framework appears in a row only if it has passed results for that scenario.
    """
    grouped: dict[str, dict[str, list[float]]] = {}
    for result in results:
        if result.scenario is None or result.status != "passed":
            continue
        grouped.setdefault(result.scenario, {}).setdefault(result.framework, []).append(
            result.duration_s
        )

    rows: list[dict] = []
    for scenario in sorted(grouped):
        row: dict = {"scenario": scenario}
        for framework in sorted(grouped[scenario]):
            durations = grouped[scenario][framework]
            row[framework] = {
                "runs": len(durations),
                "median_s": statistics.median(durations),
                "min_s": min(durations),
                "max_s": max(durations),
            }
        rows.append(row)
    return rows


def framework_totals(results: list[TestResult]) -> dict[str, dict]:
    """Counts and summed duration per framework, across all runs."""
    totals: dict[str, dict] = {}
    for result in results:
        entry = totals.setdefault(
            result.framework,
            {"tests": 0, "passed": 0, "failed": 0, "skipped": 0, "total_s": 0.0},
        )
        entry["tests"] += 1
        if result.status in ("passed", "failed", "skipped"):
            entry[result.status] += 1
        entry["total_s"] += result.duration_s
    return dict(sorted(totals.items()))
