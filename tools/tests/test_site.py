import io
import json
import shutil
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

from tools.report.__main__ import main
from tools.report.junit import TestResult, load_raw
from tools.report.k6 import load_k6
from tools.report.site import render_site

TESTS_DIR = Path(__file__).resolve().parent
RAW = TESTS_DIR / "fixtures" / "raw"


class RenderSiteTests(unittest.TestCase):
    def setUp(self):
        # Scratch space inside the project, so nothing is written outside it.
        self.scratch = Path(tempfile.mkdtemp(prefix="out-", dir=TESTS_DIR))
        self.addCleanup(shutil.rmtree, self.scratch, True)

    def test_renders_three_files_from_fixtures(self):
        out = self.scratch / "site"
        written = render_site(load_raw(RAW), load_k6(RAW), out)
        self.assertEqual(len(written), 3)
        self.assertEqual({p.name for p in written}, {"index.html", "flaky.html", "data.json"})
        for path in written:
            self.assertTrue(path.exists())

        index = (out / "index.html").read_text(encoding="utf-8")
        self.assertIn('class="fastest"', index)
        self.assertIn("cart.add-item", index)
        self.assertNotIn("No results found", index)
        self.assertIn("flaky.html", index)

        flaky = (out / "flaky.html").read_text(encoding="utf-8")
        self.assertIn("cart.add-item", flaky)
        self.assertIn("Stability score", flaky)

    def test_data_json_is_serialisable_and_complete(self):
        out = self.scratch / "site"
        render_site(load_raw(RAW), load_k6(RAW), out)
        data = json.loads((out / "data.json").read_text(encoding="utf-8"))
        self.assertEqual(len(data["results"]), 13)
        self.assertEqual(len(data["flaky"]), 1)
        self.assertAlmostEqual(data["stability_score"], 0.9)
        self.assertEqual(data["k6"][0]["run_id"], "r1")
        self.assertIn("framework_totals", data)
        self.assertIn("timings", data)

    def test_escapes_script_in_test_name(self):
        out = self.scratch / "site"
        evil = TestResult(
            "playwright", "r1", "suite", "cart.add-item <script>alert(1)</script>",
            "cart.add-item", "failed", 0.5,
        )
        render_site([evil], [], out)
        for name in ("index.html", "flaky.html"):
            text = (out / name).read_text(encoding="utf-8")
            self.assertNotIn("<script", text)
        data = (out / "data.json").read_text(encoding="utf-8")
        self.assertIn("<script>alert(1)</script>", json.loads(data)["results"][0]["name"])
        index = (out / "index.html").read_text(encoding="utf-8")
        self.assertNotIn("<script>", index)

    def test_no_external_urls_in_output(self):
        out = self.scratch / "site"
        render_site(load_raw(RAW), load_k6(RAW), out)
        for name in ("index.html", "flaky.html"):
            text = (out / name).read_text(encoding="utf-8")
            self.assertNotIn("http://", text)
            self.assertNotIn("https://", text)

    def test_empty_input_renders_no_results(self):
        out = self.scratch / "empty"
        written = render_site([], [], out)
        self.assertEqual(len(written), 3)
        index = (out / "index.html").read_text(encoding="utf-8")
        flaky = (out / "flaky.html").read_text(encoding="utf-8")
        self.assertIn("No results found", index)
        self.assertIn("No results found", flaky)
        self.assertIn("No k6 summaries found", index)
        self.assertEqual(json.loads((out / "data.json").read_text(encoding="utf-8"))["results"], [])


class CliTests(unittest.TestCase):
    def setUp(self):
        self.scratch = Path(tempfile.mkdtemp(prefix="cli-", dir=TESTS_DIR))
        self.addCleanup(shutil.rmtree, self.scratch, True)

    def test_missing_raw_dir_still_exits_zero(self):
        out = self.scratch / "site"
        buffer = io.StringIO()
        with redirect_stdout(buffer):
            code = main(["--raw", str(self.scratch / "does-not-exist"), "--out", str(out)])
        self.assertEqual(code, 0)
        self.assertIn("wrote 3 files to", buffer.getvalue())
        self.assertTrue((out / "index.html").exists())

    def test_fixture_run_prints_three_files(self):
        out = self.scratch / "site"
        buffer = io.StringIO()
        with redirect_stdout(buffer):
            code = main(["--raw", str(RAW), "--out", str(out)])
        self.assertEqual(code, 0)
        self.assertIn(f"wrote 3 files to {out}", buffer.getvalue())


if __name__ == "__main__":
    unittest.main()
