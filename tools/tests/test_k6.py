import unittest
from pathlib import Path

from tools.report.k6 import load_k6, parse_k6_summary

FIXTURES = Path(__file__).resolve().parent / "fixtures"
RAW = FIXTURES / "raw"


class ParseK6SummaryTests(unittest.TestCase):
    def test_parses_summary_export_values(self):
        metrics = parse_k6_summary(RAW / "k6" / "r1" / "summary.json")
        self.assertEqual(metrics["http_req_duration_p95_ms"], 95.2)
        self.assertEqual(metrics["http_req_duration_avg_ms"], 42.5)
        self.assertEqual(metrics["http_reqs"], 1200)
        self.assertEqual(metrics["http_req_failed_rate"], 0.0025)
        self.assertEqual(metrics["checks_passes"], 2997)
        self.assertEqual(metrics["checks_fails"], 3)
        self.assertEqual(
            set(metrics),
            {
                "http_req_duration_p95_ms",
                "http_req_duration_avg_ms",
                "http_reqs",
                "http_req_failed_rate",
                "checks_passes",
                "checks_fails",
            },
        )

    def test_parses_nested_handle_summary_shape(self):
        metrics = parse_k6_summary(FIXTURES / "k6_nested" / "summary.json")
        self.assertEqual(metrics["http_req_duration_p95_ms"], 95.2)
        self.assertEqual(metrics["http_req_duration_avg_ms"], 42.5)
        self.assertEqual(metrics["http_reqs"], 1200)
        self.assertEqual(metrics["http_req_failed_rate"], 0.0025)
        self.assertEqual(metrics["checks_passes"], 2997)
        self.assertEqual(metrics["checks_fails"], 3)

    def test_missing_metrics_become_none(self):
        metrics = parse_k6_summary(FIXTURES / "k6_sparse" / "summary.json")
        self.assertEqual(metrics["http_reqs"], 10)
        for key in (
            "http_req_duration_p95_ms",
            "http_req_duration_avg_ms",
            "http_req_failed_rate",
            "checks_passes",
            "checks_fails",
        ):
            self.assertIsNone(metrics[key], key)


class LoadK6Tests(unittest.TestCase):
    def test_loads_run_ids_from_k6_directory(self):
        runs = load_k6(RAW)
        self.assertEqual([run_id for run_id, _ in runs], ["r1"])
        self.assertEqual(runs[0][1]["http_reqs"], 1200)

    def test_missing_k6_directory_returns_empty(self):
        self.assertEqual(load_k6(FIXTURES / "does-not-exist"), [])


if __name__ == "__main__":
    unittest.main()
