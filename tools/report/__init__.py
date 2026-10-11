"""Report generator for the Shopfront-QA suites (Python 3.10, stdlib only).

Reads raw results from ``reports/raw/<framework>/<run-id>/*.xml`` (JUnit) and
``reports/raw/k6/<run-id>/summary.json`` (k6 --summary-export), then writes a
static HTML site. Run with ``python3 -m tools.report --raw reports/raw --out site``.
"""
