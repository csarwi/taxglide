#!/usr/bin/env python3
"""
Convenient test runner for TaxGlide:
- Runs pytest (category shortcuts supported)

Examples:
  python run_tests.py
  python run_tests.py --coverage -q
  python run_tests.py calc -k roi
"""

import sys
import subprocess

def _run(cmd: list[str]) -> int:
    print(f"Running: {' '.join(cmd)}")
    return subprocess.run(cmd).returncode

def run_tests() -> int:
    args = sys.argv[1:]

    # simple flags we still support (no effect on build/reinstall behavior)
    do_coverage = False
    do_verbose = False
    if "--coverage" in args:
        do_coverage = True
        args.remove("--coverage")
    if "--verbose" in args:
        do_verbose = True
        args.remove("--verbose")

    # category mapping (optional first arg)
    pytest_target = "tests/"
    rest = args[:]  # pass-through for extra pytest args
    if rest:
        cat = rest[0]
        mapping = {
            "calculation": "tests/test_calculation.py",
            "calc":        "tests/test_calculation.py",
            "optimization":"tests/test_optimization.py",
            "opt":         "tests/test_optimization.py",
            "config":      "tests/test_config_validation.py",
            "validation":  "tests/test_config_validation.py",
            "married":     "tests/test_married_filing.py",
            "filing":      "tests/test_married_filing.py",
            "range":       "tests/test_income_range_validation.py",
            "income":      "tests/test_income_range_validation.py",
        }
        if cat in mapping:
            pytest_target = mapping[cat]
            rest = rest[1:]  # keep remaining args for pytest

    # build pytest command with same interpreter
    cmd = [sys.executable, "-m", "pytest", pytest_target]
    if do_coverage:
        cmd += ["--cov=taxglide", "--cov-report=term-missing"]
    if do_verbose:
        cmd.append("-v")
    cmd += rest

    # Run tests
    code = _run(cmd)
    if code != 0:
        print("❌ tests failed")
        return code
    print("✅ tests passed")
    return 0

if __name__ == "__main__":
    sys.exit(run_tests())
