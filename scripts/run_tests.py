"""Run the existing suite and expose failures as readable GitHub check annotations."""

import os
import sys
import unittest
from pathlib import Path


def annotate_failure(test, traceback):
    message = f"{test.id()}\n{traceback}"
    # GitHub workflow command data must escape percent signs before line breaks.
    message = message.replace("%", "%25").replace("\r", "%0D").replace("\n", "%0A")
    print(f"::error title=Test failure::{message}", flush=True)


def run_suite(suite, annotate=False):
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    if annotate:
        for test, traceback in result.failures + result.errors:
            annotate_failure(test, traceback)
    if result.testsRun == 0:
        print("No tests ran.", file=sys.stderr)
        return 1
    return 0 if result.wasSuccessful() else 1


def main():
    root = Path(__file__).resolve().parents[1]
    suite = unittest.defaultTestLoader.discover(str(root / "tests"), top_level_dir=str(root))
    return run_suite(suite, annotate=os.environ.get("GITHUB_ACTIONS") == "true")


if __name__ == "__main__":
    raise SystemExit(main())
