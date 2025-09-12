#!/usr/bin/env python3
"""
Convenient test runner script for TaxGlide tests.

Usage:
    python run_tests.py                    # Run all tests
    python run_tests.py --coverage         # Run with coverage
    python run_tests.py --verbose          # Run with verbose output
    python run_tests.py calculation        # Run only calculation tests
"""

import sys
import subprocess
from pathlib import Path

def run_tests():
    """Run pytest with appropriate options."""
    
    # Base pytest command
    cmd = ["python", "-m", "pytest", "tests/"]
    
    # Check arguments
    args = sys.argv[1:] if len(sys.argv) > 1 else []
    
    # Handle help
    if "--help" in args or "-h" in args:
        print(__doc__)
        print("\nAdditional examples:")
        print("  python run_tests.py --coverage --verbose    # Coverage with verbose output")
        print("  python run_tests.py calculation             # Only calculation tests")
        print("  python run_tests.py opt --verbose           # Only optimization tests (verbose)")
        return 0
    
    if "--coverage" in args:
        cmd.extend(["--cov=taxglide", "--cov-report=term-missing"])
        args.remove("--coverage")
    
    if "--verbose" in args:
        cmd.append("-v")
        args.remove("--verbose")
    
    # If specific test category is specified
    if args:
        test_category = args[0]
        if test_category in ["calculation", "calc"]:
            cmd[-1] = "tests/test_calculation.py"
        elif test_category in ["optimization", "opt"]:
            cmd[-1] = "tests/test_optimization.py"
        elif test_category in ["config", "validation"]:
            cmd[-1] = "tests/test_config_validation.py"
        else:
            print(f"Unknown test category: {test_category}")
            print("Available categories: calculation, optimization, config")
            return 1
    
    # Run the command
    print(f"Running: {' '.join(cmd)}")
    return subprocess.run(cmd).returncode

if __name__ == "__main__":
    sys.exit(run_tests())
