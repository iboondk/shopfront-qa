import unittest
from pathlib import Path

from tools.report.junit import TestResult, load_raw, parse_junit

RAW = Path(__file__).resolve().parent / "fixtures" / "raw"


def _by_name(results):
    return {r.name: r for r in results}


class ParseJunitTests(unittest.TestCase):
    def test_playwright_failure_is_failed_and_others_passed(self):
        results = parse_junit(RAW / "playwright" / "r2" / "junit.xml", "playwright", "r2")
        self.assertEqual(len(results), 3)
        statuses = {r.scenario: r.status for r in results}
        self.assertEqual(statuses["catalog.lists-products"], "passed")
        self.assertEqual(statuses["product.shows-detail"], "passed")
        self.assertEqual(statuses["cart.add-item"], "failed")
        self.assertTrue(all(r.framework == "playwright" and r.run_id == "r2" for r in results))

    def test_scenario_extracted_from_name(self):
        results = parse_junit(RAW / "playwright" / "r1" / "junit.xml", "playwright", "r1")
        self.assertEqual(
            sorted(r.scenario for r in results),
            ["cart.add-item", "catalog.lists-products", "product.shows-detail"],
        )
        self.assertEqual(results[0].suite, "scenarios.spec.ts")

    def test_testsuites_root_and_suite_name_fallback(self):
        results = parse_junit(RAW / "cypress" / "r1" / "junit.xml", "cypress", "r1")
        self.assertEqual(len(results), 4)
        no_title = _by_name(results)["storefront home has a title"]
        # No classname on the testcase, so the parent testsuite name is used.
        self.assertEqual(no_title.suite, "e2e/scenarios.cy.js")
        self.assertIsNone(no_title.scenario)
        # Missing time attribute defaults to 0.0.
        self.assertEqual(no_title.duration_s, 0.0)
        self.assertEqual(no_title.status, "passed")

    def test_bare_testsuite_root_with_skipped(self):
        results = parse_junit(RAW / "selenium" / "r1" / "junit.xml", "selenium", "r1")
        self.assertEqual(len(results), 3)
        by_scenario = {r.scenario: r for r in results}
        self.assertEqual(by_scenario["product.shows-detail"].status, "skipped")
        self.assertEqual(by_scenario["catalog.lists-products"].status, "passed")
        self.assertEqual(by_scenario["cart.add-item"].duration_s, 3.0)
        self.assertEqual(by_scenario["cart.add-item"].suite, "tests.test_scenarios.TestStorefront")


class LoadRawTests(unittest.TestCase):
    def test_loads_all_junit_runs_and_skips_k6(self):
        results = load_raw(RAW)
        # playwright 3+3, cypress 4, selenium 3
        self.assertEqual(len(results), 13)
        self.assertNotIn("k6", {r.framework for r in results})
        self.assertEqual(
            {r.framework for r in results}, {"playwright", "cypress", "selenium"}
        )

    def test_missing_directory_returns_empty(self):
        self.assertEqual(load_raw(RAW / "does-not-exist"), [])


class TestResultTests(unittest.TestCase):
    def test_retries_default_zero_and_frozen(self):
        result = TestResult("playwright", "r1", "s", "n", None, "passed", 1.0)
        self.assertEqual(result.retries, 0)
        with self.assertRaises(Exception):
            result.status = "failed"


if __name__ == "__main__":
    unittest.main()
