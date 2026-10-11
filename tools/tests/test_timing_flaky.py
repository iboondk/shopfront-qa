import unittest
from pathlib import Path

from tools.report.flaky import detect_flaky, stability_score
from tools.report.junit import TestResult, load_raw
from tools.report.timing import compare_timings, framework_totals

RAW = Path(__file__).resolve().parent / "fixtures" / "raw"


def _result(framework="playwright", run_id="r1", suite="s", name="cart.add-item x",
            scenario="cart.add-item", status="passed", duration_s=1.0, retries=0):
    return TestResult(framework, run_id, suite, name, scenario, status, duration_s, retries)


class CompareTimingsTests(unittest.TestCase):
    def setUp(self):
        self.rows = {row["scenario"]: row for row in compare_timings(load_raw(RAW))}

    def test_one_row_per_passed_scenario(self):
        self.assertEqual(
            sorted(self.rows),
            ["cart.add-item", "catalog.lists-products", "product.shows-detail"],
        )

    def test_medians_and_run_counts(self):
        catalog = self.rows["catalog.lists-products"]
        self.assertEqual(catalog["playwright"]["runs"], 2)
        self.assertAlmostEqual(catalog["playwright"]["median_s"], 1.25)
        self.assertAlmostEqual(catalog["playwright"]["min_s"], 1.2)
        self.assertAlmostEqual(catalog["playwright"]["max_s"], 1.3)
        self.assertAlmostEqual(catalog["cypress"]["median_s"], 0.9)
        self.assertAlmostEqual(catalog["selenium"]["median_s"], 2.0)

    def test_failed_and_skipped_excluded(self):
        # playwright cart.add-item failed in r2, so only the r1 pass (1.0 s) counts.
        cart = self.rows["cart.add-item"]
        self.assertEqual(cart["playwright"]["runs"], 1)
        self.assertAlmostEqual(cart["playwright"]["median_s"], 1.0)
        # selenium product.shows-detail was skipped, so selenium has no entry there.
        self.assertNotIn("selenium", self.rows["product.shows-detail"])

    def test_frameworks_present_per_row(self):
        self.assertEqual(
            set(self.rows["product.shows-detail"]) - {"scenario"},
            {"playwright", "cypress"},
        )

    def test_framework_totals(self):
        totals = framework_totals(load_raw(RAW))
        self.assertEqual(set(totals), {"playwright", "cypress", "selenium"})
        self.assertEqual(totals["playwright"]["tests"], 6)
        self.assertEqual(totals["playwright"]["passed"], 5)
        self.assertEqual(totals["playwright"]["failed"], 1)
        self.assertEqual(totals["playwright"]["skipped"], 0)
        self.assertAlmostEqual(totals["playwright"]["total_s"], 9.2)
        self.assertEqual(totals["cypress"]["passed"], 4)
        self.assertEqual(totals["selenium"]["skipped"], 1)
        self.assertEqual(totals["selenium"]["passed"], 2)

    def test_empty_input(self):
        self.assertEqual(compare_timings([]), [])
        self.assertEqual(framework_totals([]), {})


class DetectFlakyTests(unittest.TestCase):
    def test_fixture_finds_only_playwright_cart(self):
        flaky = detect_flaky(load_raw(RAW))
        self.assertEqual(len(flaky), 1)
        row = flaky[0]
        self.assertEqual(row["framework"], "playwright")
        self.assertEqual(row["name"], "cart.add-item adds Classic Tee to the cart")
        self.assertEqual(row["passes"], 1)
        self.assertEqual(row["fails"], 1)
        self.assertEqual(row["runs"], 2)
        self.assertEqual(row["flake_rate"], 0.5)

    def test_stability_score_fixture(self):
        # 10 (framework, suite, name) groups, 1 flaky.
        self.assertAlmostEqual(stability_score(load_raw(RAW)), 0.9)

    def test_retry_then_pass_is_flaky(self):
        results = [_result(run_id="r1", status="passed", retries=1)]
        flaky = detect_flaky(results)
        self.assertEqual(len(flaky), 1)
        self.assertEqual(flaky[0]["flake_rate"], 0.0)

    def test_consistent_results_are_not_flaky(self):
        results = [_result(run_id="r1"), _result(run_id="r2")]
        self.assertEqual(detect_flaky(results), [])
        self.assertEqual(stability_score(results), 1.0)

    def test_sorted_by_flake_rate_then_name(self):
        results = [
            _result(name="b", run_id="r1", status="passed"),
            _result(name="b", run_id="r2", status="failed"),
            _result(name="a", run_id="r1", status="passed"),
            _result(name="a", run_id="r2", status="passed"),
            _result(name="a", run_id="r3", status="failed"),
            _result(name="c", run_id="r1", status="passed"),
            _result(name="c", run_id="r2", status="failed"),
            _result(name="c", run_id="r3", status="failed"),
            _result(name="c", run_id="r4", status="passed"),
        ]
        flaky = detect_flaky(results)
        # b and c both have rate 0.5 (name breaks the tie), a has 1/3.
        self.assertEqual([r["name"] for r in flaky], ["b", "c", "a"])
        self.assertEqual([r["flake_rate"] for r in flaky], [0.5, 0.5, 0.333])

    def test_empty_stability_is_one(self):
        self.assertEqual(stability_score([]), 1.0)


if __name__ == "__main__":
    unittest.main()
