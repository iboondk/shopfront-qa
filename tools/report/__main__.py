"""CLI: python3 -m tools.report --raw reports/raw --out site"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .junit import load_raw
from .k6 import load_k6
from .site import render_site


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python3 -m tools.report",
        description="Build a static HTML report site from raw JUnit and k6 results.",
    )
    parser.add_argument("--raw", type=Path, default=Path("reports/raw"), help="raw results directory")
    parser.add_argument("--out", type=Path, default=Path("site"), help="output directory")
    args = parser.parse_args(argv)

    results = load_raw(args.raw)
    k6_runs = load_k6(args.raw)
    written = render_site(results, k6_runs, args.out)
    print(f"wrote {len(written)} files to {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
