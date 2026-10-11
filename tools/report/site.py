"""Render the static HTML report site. Self-contained: inline CSS, no scripts, no external assets."""

from __future__ import annotations

import html
import json
from dataclasses import asdict
from pathlib import Path

from .flaky import detect_flaky, stability_score
from .junit import TestResult
from .timing import compare_timings, framework_totals

MISSING = "&mdash;"
NO_RESULTS = "No results found"

K6_COLUMNS = [
    ("http_req_duration_p95_ms", "p95 latency (ms)"),
    ("http_req_duration_avg_ms", "avg latency (ms)"),
    ("http_reqs", "requests"),
    ("http_req_failed_rate", "failed rate"),
    ("checks_passes", "checks passed"),
    ("checks_fails", "checks failed"),
]

CSS = """
:root {
  --bg: #ffffff; --fg: #1b1f24; --muted: #5b6470; --border: #d8dde3;
  --head: #f3f5f7; --accent: #1a4fb3; --fastest-bg: #d9f5e3; --fastest-fg: #0b5d2a;
}
@media (prefers-color-scheme: dark) {
  :root {
    --bg: #0f1216; --fg: #e6e9ee; --muted: #9aa4b2; --border: #2c333c;
    --head: #171c22; --accent: #7aa7ff; --fastest-bg: #12391f; --fastest-fg: #9ef0b8;
  }
}
* { box-sizing: border-box; }
body {
  margin: 0; background: var(--bg); color: var(--fg);
  font-family: system-ui, -apple-system, "Segoe UI", sans-serif; line-height: 1.5;
}
header, main { max-width: 1040px; margin: 0 auto; padding: 1.25rem 1rem; }
header { border-bottom: 1px solid var(--border); }
h1 { font-size: 1.6rem; margin: 0 0 0.25rem; }
h2 { font-size: 1.15rem; margin: 2rem 0 0.5rem; }
nav a { color: var(--accent); margin-right: 1rem; }
a { color: var(--accent); }
.muted, small { color: var(--muted); }
.table-wrap { overflow-x: auto; }
table { border-collapse: collapse; width: 100%; font-size: 0.92rem; }
th, td { text-align: left; padding: 0.45rem 0.6rem; border-bottom: 1px solid var(--border); vertical-align: top; }
th { background: var(--head); font-weight: 600; }
td.num, th.num { text-align: right; font-variant-numeric: tabular-nums; }
td.fastest { background: var(--fastest-bg); color: var(--fastest-fg); font-weight: 600; }
code { font-family: ui-monospace, SFMono-Regular, Menlo, monospace; word-break: break-all; }
.score { font-size: 1.4rem; font-weight: 600; }
.empty { color: var(--muted); font-style: italic; }
"""


def _e(value) -> str:
    """Escape any value for HTML text or attribute use."""
    return html.escape("" if value is None else str(value), quote=True)


def _num(value, digits: int = 3) -> str:
    if value is None:
        return MISSING
    if isinstance(value, bool):
        return _e(value)
    if isinstance(value, float):
        return f"{value:.{digits}f}"
    return _e(value)


def _page(title: str, body: str) -> str:
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{_e(title)}</title>
<style>{CSS}</style>
</head>
<body>
<header>
<h1>{_e(title)}</h1>
<nav><a href="index.html">Overview</a><a href="flaky.html">Flaky tests</a><a href="data.json">data.json</a></nav>
</header>
<main>
{body}
</main>
</body>
</html>
"""


def _table(headers: list[str], rows: list[list[str]], numeric_from: int = 1) -> str:
    head = "".join(
        f'<th class="num">{_e(h)}</th>' if i >= numeric_from else f"<th>{_e(h)}</th>"
        for i, h in enumerate(headers)
    )
    body = "".join(
        "<tr>" + "".join(cell for cell in row) + "</tr>" for row in rows
    )
    return f'<div class="table-wrap"><table><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table></div>'


def _cell(content: str, numeric: bool = True, css: str = "") -> str:
    if css:
        # The fastest-cell marker is the bare class "fastest", as the spec requires.
        return f'<td class="{css}">{content}</td>'
    attr = ' class="num"' if numeric else ""
    return f"<td{attr}>{content}</td>"


def _totals_section(totals: dict[str, dict]) -> str:
    if not totals:
        return f'<p class="empty">{NO_RESULTS}</p>'
    headers = ["Framework", "Tests", "Passed", "Failed", "Skipped", "Total time (s)"]
    rows = []
    for framework, t in totals.items():
        rows.append(
            [
                _cell(f"<code>{_e(framework)}</code>", numeric=False),
                _cell(_num(t["tests"])),
                _cell(_num(t["passed"])),
                _cell(_num(t["failed"])),
                _cell(_num(t["skipped"])),
                _cell(_num(t["total_s"])),
            ]
        )
    return _table(headers, rows)


def _timing_section(timings: list[dict]) -> str:
    if not timings:
        return f'<p class="empty">{NO_RESULTS}</p>'
    frameworks = sorted({fw for row in timings for fw in row if fw != "scenario"})
    headers = ["Scenario"] + frameworks
    rows = []
    for row in timings:
        present = {fw: row[fw] for fw in frameworks if fw in row}
        fastest = min(present, key=lambda fw: present[fw]["median_s"]) if present else None
        cells = [_cell(f"<code>{_e(row['scenario'])}</code>", numeric=False)]
        for fw in frameworks:
            if fw not in present:
                cells.append(_cell(MISSING))
                continue
            stats = present[fw]
            css = "fastest" if fw == fastest else ""
            content = (
                f"{_num(stats['median_s'])} s "
                f"<small>(n={_num(stats['runs'])}, range {_num(stats['min_s'])}&ndash;{_num(stats['max_s'])})</small>"
            )
            cells.append(_cell(content, css=css))
        rows.append(cells)
    note = '<p class="muted">Median duration of passed runs per scenario. The fastest median is highlighted.</p>'
    return note + _table(headers, rows)


def _k6_section(k6_runs: list[tuple[str, dict]]) -> str:
    if not k6_runs:
        return f'<p class="empty">No k6 summaries found</p>'
    headers = ["Run"] + [label for _, label in K6_COLUMNS]
    rows = []
    for run_id, metrics in k6_runs:
        cells = [_cell(f"<code>{_e(run_id)}</code>", numeric=False)]
        for key, _ in K6_COLUMNS:
            cells.append(_cell(_num(metrics.get(key))))
        rows.append(cells)
    return _table(headers, rows)


def _flaky_table(flaky: list[dict]) -> str:
    headers = ["Framework", "Suite", "Test", "Runs", "Passes", "Fails", "Flake rate"]
    rows = []
    for row in flaky:
        rows.append(
            [
                _cell(f"<code>{_e(row['framework'])}</code>", numeric=False),
                _cell(_e(row["suite"]), numeric=False),
                _cell(f"<code>{_e(row['name'])}</code>", numeric=False),
                _cell(_num(row["runs"])),
                _cell(_num(row["passes"])),
                _cell(_num(row["fails"])),
                _cell(_num(row["flake_rate"])),
            ]
        )
    return _table(headers, rows, numeric_from=3)


def _index_body(results, flaky, timings, totals, k6_runs) -> str:
    flaky_count = len(flaky)
    summary = (
        f'<p class="muted">{_num(len(results))} results parsed. '
        f'See <a href="flaky.html">flaky tests</a> ({_num(flaky_count)} flagged) '
        f'and <a href="data.json">data.json</a>.</p>'
    )
    return "\n".join(
        [
            summary,
            "<h2>Framework totals</h2>",
            _totals_section(totals),
            "<h2>Scenario timing comparison</h2>",
            _timing_section(timings),
            "<h2>k6 performance summaries</h2>",
            _k6_section(k6_runs),
        ]
    )


def _flaky_body(results, flaky, score) -> str:
    if not results:
        return f'<p class="empty">{NO_RESULTS}</p>'
    score_line = (
        f'<p>Stability score: <span class="score">{_num(score)}</span> '
        f'<small>(share of tests that are not flaky)</small></p>'
    )
    if not flaky:
        return score_line + '<p class="empty">No flaky tests detected.</p>'
    return score_line + _flaky_table(flaky)


def render_site(
    results: list[TestResult],
    k6_runs: list[tuple[str, dict]],
    out_dir: Path,
) -> list[Path]:
    """Write index.html, flaky.html and data.json into out_dir. Returns the paths written."""
    out_dir.mkdir(parents=True, exist_ok=True)

    totals = framework_totals(results)
    timings = compare_timings(results)
    flaky = detect_flaky(results)
    score = stability_score(results)

    index_path = out_dir / "index.html"
    flaky_path = out_dir / "flaky.html"
    data_path = out_dir / "data.json"

    index_path.write_text(
        _page("Shopfront-QA report", _index_body(results, flaky, timings, totals, k6_runs)),
        encoding="utf-8",
    )
    flaky_path.write_text(
        _page("Flaky tests", _flaky_body(results, flaky, score)),
        encoding="utf-8",
    )

    data = {
        "results": [asdict(r) for r in results],
        "framework_totals": totals,
        "timings": timings,
        "flaky": flaky,
        "stability_score": score,
        "k6": [{"run_id": run_id, **metrics} for run_id, metrics in k6_runs],
    }
    data_path.write_text(json.dumps(data, indent=2), encoding="utf-8")

    return [index_path, flaky_path, data_path]
