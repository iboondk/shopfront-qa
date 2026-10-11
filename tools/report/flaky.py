"""Flaky-test detection across run-ids."""

from __future__ import annotations

from collections import defaultdict

from .junit import TestResult


def _groups(results: list[TestResult]) -> dict[tuple[str, str, str], list[TestResult]]:
    grouped: dict[tuple[str, str, str], list[TestResult]] = defaultdict(list)
    for result in results:
        grouped[(result.framework, result.suite, result.name)].append(result)
    return grouped


def detect_flaky(results: list[TestResult]) -> list[dict]:
    """Flaky if, across runs, it both passed and failed, or it passed after a retry.

    runs is the number of results in the group. flake_rate = fails / (passes + fails),
    rounded to 3 places. Sorted by flake_rate descending, then name.
    """
    flaky: list[dict] = []
    for (framework, suite, name), items in _groups(results).items():
        passes = sum(1 for r in items if r.status == "passed")
        fails = sum(1 for r in items if r.status == "failed")
        passed_after_retry = any(r.retries > 0 and r.status == "passed" for r in items)
        if not ((passes and fails) or passed_after_retry):
            continue
        decided = passes + fails
        flaky.append(
            {
                "framework": framework,
                "suite": suite,
                "name": name,
                "runs": len(items),
                "passes": passes,
                "fails": fails,
                "flake_rate": round(fails / decided, 3) if decided else 0.0,
            }
        )
    flaky.sort(key=lambda row: (-row["flake_rate"], row["name"], row["framework"], row["suite"]))
    return flaky


def stability_score(results: list[TestResult]) -> float:
    """Share of (framework, suite, name) groups that are not flaky. 1.0 when empty."""
    groups = _groups(results)
    if not groups:
        return 1.0
    flaky_keys = {(row["framework"], row["suite"], row["name"]) for row in detect_flaky(results)}
    return (len(groups) - len(flaky_keys)) / len(groups)
