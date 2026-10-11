"""Parse JUnit XML files into TestResult records."""

from __future__ import annotations

import re
import sys
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path

SCENARIO_RE = re.compile(r"(catalog|product|cart)\.[a-z0-9-]+")
RETRY_TAGS = ("rerunFailure", "rerunError", "flakyFailure", "flakyError")
K6_DIR = "k6"


@dataclass(frozen=True)
class TestResult:
    framework: str
    run_id: str
    suite: str
    name: str
    scenario: str | None
    status: str  # 'passed' | 'failed' | 'skipped'
    duration_s: float
    retries: int = 0


def _float_attr(element: ET.Element, key: str) -> float:
    try:
        return float(element.get(key, 0.0))
    except (TypeError, ValueError):
        return 0.0


def _retries(case: ET.Element) -> int:
    count = 0
    try:
        count = int(float(case.get("retries", 0)))
    except (TypeError, ValueError):
        count = 0
    # Surefire-style retry markers, if a reporter emits them.
    count += sum(1 for tag in RETRY_TAGS for _ in case.findall(tag))
    return count


def _status(case: ET.Element) -> str:
    if case.find("failure") is not None or case.find("error") is not None:
        return "failed"
    if case.find("skipped") is not None:
        return "skipped"
    return "passed"


def _scenario(name: str) -> str | None:
    match = SCENARIO_RE.search(name)
    return match.group(0) if match else None


def _suites(root: ET.Element) -> list[ET.Element]:
    """Return every <testsuite> under the root, or the root itself if there are none."""
    suites = list(root.iter("testsuite"))
    return suites if suites else [root]


def parse_junit(path: Path, framework: str, run_id: str) -> list[TestResult]:
    """Parse one JUnit XML file. Accepts a <testsuites> or a bare <testsuite> root."""
    root = ET.parse(path).getroot()
    results: list[TestResult] = []
    for suite_el in _suites(root):
        parent_name = suite_el.get("name", "")
        for case in suite_el.findall("testcase"):
            name = case.get("name", "")
            suite = case.get("classname") or parent_name
            results.append(
                TestResult(
                    framework=framework,
                    run_id=run_id,
                    suite=suite,
                    name=name,
                    scenario=_scenario(name),
                    status=_status(case),
                    duration_s=_float_attr(case, "time"),
                    retries=_retries(case),
                )
            )
    return results


def load_raw(raw_dir: Path) -> list[TestResult]:
    """Load every JUnit file under raw_dir/<framework>/<run-id>/*.xml (k6 excluded).

    A missing raw_dir yields an empty list. A malformed XML file is skipped with a
    warning on stderr so one bad shard does not hide the rest of the report.
    """
    if not raw_dir.is_dir():
        return []
    results: list[TestResult] = []
    for framework_dir in sorted(p for p in raw_dir.iterdir() if p.is_dir()):
        if framework_dir.name == K6_DIR:
            continue
        for run_dir in sorted(p for p in framework_dir.iterdir() if p.is_dir()):
            for xml_path in sorted(run_dir.glob("*.xml")):
                try:
                    results.extend(parse_junit(xml_path, framework_dir.name, run_dir.name))
                except ET.ParseError as exc:
                    print(f"warning: skipping {xml_path}: {exc}", file=sys.stderr)
    return results
