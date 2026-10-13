# ADR-0003: A Python stdlib-only report generator that writes a static site

- Status: Accepted
- Date: 2026-10-11

## Context

Results come from several tools: JUnit XML from four frameworks, k6 summary JSON and Locust CSV. The team
needs one page that lines them up. The report should open from a file and be deployable to GitHub Pages
with no build step.

## Decision

`tools/report/` is written in Python 3.10 with the standard library only. Its entry point is
`python3 -m tools.report --raw reports/raw --out site`.

- `junit.py` parses JUnit into `TestResult` records.
- `k6.py` parses the k6 summary export.
- `timing.py` compares timings per framework and per scenario.
- `flaky.py` detects flaky tests across run-ids and computes a stability score.
- `site.py` writes self-contained HTML with inline CSS, no scripts and no external assets.

The renderer shows only what it parsed. If a framework has no results, the page says "No results found"
and does not fill in a number.

## Consequences

- No install step is needed for the report, and the code is covered by unittest with XML and JSON fixtures.
- The report generator does not depend on the other components, so it can be developed independently.
- Hand-written inline CSS is more work than a template engine. The page uses `prefers-color-scheme` to
  support dark mode.
- Timing comparisons are only as good as the input. The docs contain no benchmark numbers by hand.
