# Optimization Testing

This directory contains comprehensive optimization tests for TaxGlide.

## Quick Tests

Run the regular test suite (excludes slow comprehensive test):

```bash
pytest tests/
```

## Comprehensive Optimization Test

The comprehensive test validates optimization quality across the full income spectrum (20K-200K CHF, 1,801 test cases).

### Run Comprehensive Test

```bash
# Run the full comprehensive test (takes several minutes)
pytest -m slow tests/test_optimization_comprehensive.py::TestComprehensiveOptimization::test_optimization_quality_across_income_spectrum -v -s

# Or run all slow tests
pytest -m slow -v -s
```

### Standalone Validation Script

For detailed analysis and reporting, use the standalone script:

```bash
# Full comprehensive validation with detailed reporting
python tests/validate_optimization_comprehensive.py

# Quick test on smaller range
python tests/validate_optimization_comprehensive.py --start 30000 --end 50000 --step 1000
```

## Quality Requirements

The optimization tests enforce these quality thresholds:

- **Minimum 20% utilization** - Ensures practical deduction usage
- **ROI between 10-100%** - Reasonable and realistic returns  
- **95%+ success rate** - High reliability across income spectrum
- **≤5% quality failure rate** - Minimal edge cases

## Test Categories

### 1. Regular Tests (Fast)
- **test_specific_problematic_cases**: Tests specific income levels that have been problematic in the past
- Run with regular `pytest` command

### 2. Comprehensive Tests (Slow) 
- **test_optimization_quality_across_income_spectrum**: Full income spectrum validation (20K-200K CHF, 100 CHF steps)
- Marked with `@pytest.mark.slow`
- Run explicitly with `pytest -m slow`

## Integration with CI

The regular test suite runs on every commit. The comprehensive test should be run:

- Before major releases
- After optimization algorithm changes  
- When investigating optimization issues
- Weekly/monthly as regression prevention

## Interpreting Results

### Good Results
- Average utilization ≥ 20%
- Average ROI 15-25% (reasonable range)
- Quality failure rate < 5%
- Success rate > 95%

### Warning Signs
- Many low utilization failures
- Unrealistic ROI spikes (>100%)
- Poor success rate
- Significant regression from previous runs
