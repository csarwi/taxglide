"""Tests for CLI income parameter handling.

Tests the new separate income parameter functionality while ensuring backward compatibility
with the legacy single income parameter.
"""

import pytest
from typer.testing import CliRunner

from taxglide.cli import app, _resolve_incomes, _calc_once, _calc_once_separate


class TestResolveIncomes:
    """Test the _resolve_incomes helper function."""
    
    def test_single_income(self):
        """Test single income parameter."""
        sg_income, fed_income = _resolve_incomes(60000, None, None)
        assert sg_income == 60000
        assert fed_income == 60000
    
    def test_separate_incomes(self):
        """Test separate income parameters."""
        sg_income, fed_income = _resolve_incomes(None, 58000, 60000)
        assert sg_income == 58000
        assert fed_income == 60000
    
    def test_no_income_provided(self):
        """Test error when no income is provided."""
        with pytest.raises(ValueError, match="Must provide either --income, or both --income-sg and --income-fed"):
            _resolve_incomes(None, None, None)
    
    def test_incomplete_separate_incomes(self):
        """Test error when only one of separate incomes is provided."""
        with pytest.raises(ValueError, match="When using separate incomes, both --income-sg and --income-fed must be provided"):
            _resolve_incomes(None, 58000, None)
        
        with pytest.raises(ValueError, match="When using separate incomes, both --income-sg and --income-fed must be provided"):
            _resolve_incomes(None, None, 60000)
    
    def test_conflicting_parameters(self):
        """Test error when both single and separate incomes are provided."""
        with pytest.raises(ValueError, match="Cannot specify both --income and --income-sg/--income-fed"):
            _resolve_incomes(60000, 58000, None)
        
        with pytest.raises(ValueError, match="Cannot specify both --income and --income-sg/--income-fed"):
            _resolve_incomes(60000, None, 60000)
        
        with pytest.raises(ValueError, match="Cannot specify both --income and --income-sg/--income-fed"):
            _resolve_incomes(60000, 58000, 60000)


class TestCalcOnceSeparate:
    """Test the new _calc_once_separate function."""
    
    def test_equal_incomes(self, configs_2025, default_multiplier_codes):
        """Test calculation with equal SG and federal incomes."""
        result = _calc_once_separate(2025, 60000, 60000, default_multiplier_codes)
        
        # Should match legacy calculation
        legacy_result = _calc_once(2025, 60000, default_multiplier_codes)
        
        assert result["income_sg"] == 60000
        assert result["income_fed"] == 60000
        assert result["federal"] == legacy_result["federal"]
        assert result["sg_simple"] == legacy_result["sg_simple"] 
        assert result["sg_after_mult"] == legacy_result["sg_after_mult"]
        assert result["total"] == legacy_result["total"]
        assert result["avg_rate"] == legacy_result["avg_rate"]
    
    def test_different_incomes(self, configs_2025, default_multiplier_codes):
        """Test calculation with different SG and federal incomes."""
        result = _calc_once_separate(2025, 58000, 60000, default_multiplier_codes)
        
        # Compare with separate legacy calculations
        sg_result = _calc_once(2025, 58000, default_multiplier_codes)
        fed_result = _calc_once(2025, 60000, default_multiplier_codes)
        
        assert result["income_sg"] == 58000
        assert result["income_fed"] == 60000
        assert result["sg_simple"] == sg_result["sg_simple"]
        assert result["sg_after_mult"] == sg_result["sg_after_mult"] 
        assert result["federal"] == fed_result["federal"]
        
        # Total should be SG (from 58k) + Federal (from 60k)
        expected_total = result["sg_after_mult"] + result["federal"]
        assert abs(result["total"] - expected_total) < 0.01
    
    def test_realistic_difference_scenario(self, configs_2025, default_multiplier_codes):
        """Test a realistic scenario where SG and federal incomes differ due to deductions."""
        # Example: 90k base income, but person can deduct 5k more from federal than SG
        sg_income = 90000
        fed_income = 85000
        
        result = _calc_once_separate(2025, sg_income, fed_income, default_multiplier_codes)
        
        # Verify structure
        assert result["income_sg"] == sg_income
        assert result["income_fed"] == fed_income
        assert result["federal"] > 0
        assert result["sg_simple"] > 0
        assert result["sg_after_mult"] > 0
        assert result["total"] == result["federal"] + result["sg_after_mult"]
        assert 0 < result["avg_rate"] < 1.0


class TestCliCalcCommand:
    """Test the calc CLI command with new income parameters."""
    
    def setup_method(self):
        """Set up CLI runner for each test."""
        self.runner = CliRunner()
    
    def test_calc_with_legacy_income(self):
        """Test calc command with legacy single income parameter."""
        result = self.runner.invoke(app, [
            "calc", "--year", "2025", "--income", "60000"
        ])
        assert result.exit_code == 0
        assert "income_sg" in result.stdout
        assert "income_fed" in result.stdout
        assert "'income': 60000" in result.stdout
    
    def test_calc_with_separate_incomes(self):
        """Test calc command with separate income parameters."""
        result = self.runner.invoke(app, [
            "calc", "--year", "2025", "--income-sg", "58000", "--income-fed", "60000"
        ])
        assert result.exit_code == 0
        assert "'income_sg': 58000" in result.stdout
        assert "'income_fed': 60000" in result.stdout
        assert "'income': None" in result.stdout  # Legacy field should be None
    
    def test_calc_error_no_income(self):
        """Test calc command error when no income is provided."""
        result = self.runner.invoke(app, [
            "calc", "--year", "2025"
        ])
        assert result.exit_code == 2  # CLI exits with code 2 for validation errors
        assert "error" in result.stdout
        assert "Must provide either --income" in result.stdout
    
    def test_calc_error_incomplete_separate_incomes(self):
        """Test calc command error with incomplete separate incomes."""
        result = self.runner.invoke(app, [
            "calc", "--year", "2025", "--income-sg", "58000"
        ])
        assert result.exit_code == 2
        assert "error" in result.stdout
        assert "When using separate incomes" in result.stdout
    
    def test_calc_error_conflicting_parameters(self):
        """Test calc command error with conflicting parameters."""
        result = self.runner.invoke(app, [
            "calc", "--year", "2025", "--income", "60000", "--income-sg", "58000"
        ])
        assert result.exit_code == 2
        assert "error" in result.stdout
        assert "Cannot specify both --income and --income-sg" in result.stdout


class TestCliOptimizeCommand:
    """Test the optimize CLI command with new income parameters."""
    
    def setup_method(self):
        """Set up CLI runner for each test."""
        self.runner = CliRunner()
    
    def test_optimize_with_legacy_income(self):
        """Test optimize command with legacy single income parameter."""
        result = self.runner.invoke(app, [
            "optimize", "--year", "2025", "--income", "80000", "--max-deduction", "5000"
        ])
        assert result.exit_code == 0
        assert "sweet_spot" in result.stdout
    
    def test_optimize_with_separate_incomes(self):
        """Test optimize command with separate income parameters."""
        result = self.runner.invoke(app, [
            "optimize", "--year", "2025", 
            "--income-sg", "78000", "--income-fed", "80000",
            "--max-deduction", "5000"
        ])
        assert result.exit_code == 0
        assert "sweet_spot" in result.stdout
    
    def test_optimize_error_no_income(self):
        """Test optimize command error when no income is provided.""" 
        result = self.runner.invoke(app, [
            "optimize", "--year", "2025", "--max-deduction", "5000"
        ])
        assert result.exit_code == 2
        assert "error" in result.stdout
        assert "Must provide either --income" in result.stdout


class TestCliScanCommand:
    """Test the scan CLI command with new income parameters."""
    
    def setup_method(self):
        """Set up CLI runner for each test.""" 
        self.runner = CliRunner()
    
    def test_scan_with_legacy_income(self):
        """Test scan command with legacy single income parameter."""
        result = self.runner.invoke(app, [
            "scan", "--year", "2025", "--income", "70000", 
            "--max-deduction", "2000", "--d-step", "500"
        ])
        assert result.exit_code == 0
        # Should produce output with saved info
        assert "saved" in result.stdout.lower() or "rows" in result.stdout.lower()
    
    def test_scan_with_separate_incomes(self):
        """Test scan command with separate income parameters."""
        result = self.runner.invoke(app, [
            "scan", "--year", "2025", 
            "--income-sg", "68000", "--income-fed", "70000",
            "--max-deduction", "2000", "--d-step", "500"  
        ])
        assert result.exit_code == 0
        assert "saved" in result.stdout.lower() or "rows" in result.stdout.lower()


class TestCliCompareBracketsCommand:
    """Test the compare-brackets CLI command with new income parameters."""
    
    def setup_method(self):
        """Set up CLI runner for each test."""
        self.runner = CliRunner()
    
    def test_compare_brackets_with_legacy_income(self):
        """Test compare-brackets command with legacy single income parameter."""
        result = self.runner.invoke(app, [
            "compare-brackets", "--year", "2025", "--income", "75000", "--deduction", "3000"
        ])
        assert result.exit_code == 0
        assert "original_sg_income" in result.stdout and "federal_bracket" in result.stdout
    
    def test_compare_brackets_with_separate_incomes(self):
        """Test compare-brackets command with separate income parameters."""
        result = self.runner.invoke(app, [
            "compare-brackets", "--year", "2025",
            "--income-sg", "73000", "--income-fed", "75000", 
            "--deduction", "3000"
        ])
        assert result.exit_code == 0
        assert "original_sg_income" in result.stdout and "federal_bracket" in result.stdout


class TestBackwardCompatibility:
    """Test that existing workflows continue to work unchanged."""
    
    def test_legacy_workflows_unchanged(self, configs_2025, default_multiplier_codes):
        """Test that legacy single income workflows produce identical results."""
        income = 65000
        
        # Legacy calculation
        legacy_result = _calc_once(2025, income, default_multiplier_codes)
        
        # New calculation with single income resolved 
        sg_income, fed_income = _resolve_incomes(income, None, None)
        new_result = _calc_once_separate(2025, sg_income, fed_income, default_multiplier_codes)
        
        # Results should be identical
        assert new_result["income_sg"] == income
        assert new_result["income_fed"] == income
        assert new_result["federal"] == legacy_result["federal"]
        assert new_result["sg_simple"] == legacy_result["sg_simple"]
        assert new_result["sg_after_mult"] == legacy_result["sg_after_mult"]
        assert new_result["total"] == legacy_result["total"]
        assert new_result["avg_rate"] == legacy_result["avg_rate"]
        assert new_result["marginal_total"] == legacy_result["marginal_total"]
    
    def test_multiple_income_levels(self, configs_2025, default_multiplier_codes):
        """Test backward compatibility across multiple income levels."""
        test_incomes = [25000, 50000, 75000, 100000, 150000]
        
        for income in test_incomes:
            # Legacy calculation
            legacy_result = _calc_once(2025, income, default_multiplier_codes)
            
            # New calculation 
            sg_income, fed_income = _resolve_incomes(income, None, None)
            new_result = _calc_once_separate(2025, sg_income, fed_income, default_multiplier_codes)
            
            # Key fields should match exactly
            assert new_result["federal"] == legacy_result["federal"], f"Federal mismatch at income {income}"
            assert new_result["sg_simple"] == legacy_result["sg_simple"], f"SG simple mismatch at income {income}" 
            assert new_result["sg_after_mult"] == legacy_result["sg_after_mult"], f"SG mult mismatch at income {income}"
            assert new_result["total"] == legacy_result["total"], f"Total mismatch at income {income}"
            assert abs(new_result["avg_rate"] - legacy_result["avg_rate"]) < 1e-6, f"Avg rate mismatch at income {income}"


class TestSeparateIncomeRealWorldScenarios:
    """Test separate income functionality with real Swiss tax data."""
    
    def test_separate_income_accuracy_against_official_values(self, separate_income_test_cases, default_multiplier_codes):
        """Validate TaxGlide's accuracy with separate SG and Federal incomes against official Swiss calculations."""
        print("\nSeparate Income Accuracy Validation:")
        print("SG Inc  | Fed Inc | Federal Diff | SG Diff  | Total Diff | Description")
        print("-" * 85)
        
        max_error = 0.0
        total_cases = len(separate_income_test_cases)
        
        for test_case in separate_income_test_cases:
            result = _calc_once_separate(2025, test_case.sg_income, test_case.fed_income, default_multiplier_codes)
            
            fed_error = abs(result["federal"] - float(test_case.federal_tax))
            sg_error = abs(result["sg_after_mult"] - float(test_case.sg_after_mult)) 
            total_error = abs(result["total"] - float(test_case.total_tax))
            
            max_error = max(max_error, fed_error, sg_error, total_error)
            
            print(f"{test_case.sg_income:7d} | {test_case.fed_income:7d} | {fed_error:11.2f} | {sg_error:8.2f} | {total_error:10.2f} | {test_case.description[:30]}")
            
            # All errors should be minimal (within 1 CHF)
            assert fed_error <= 1.0, f"Federal tax error too large: {fed_error:.2f} CHF"
            assert sg_error <= 1.0, f"SG tax error too large: {sg_error:.2f} CHF" 
            assert total_error <= 1.0, f"Total tax error too large: {total_error:.2f} CHF"
        
        print(f"\nAccuracy Summary: {total_cases} separate income test cases, max error {max_error:.2f} CHF")
        print("✅ TaxGlide achieves exceptional accuracy (≤ 1 CHF) with separate SG/Federal incomes")
        
        # Overall accuracy should be outstanding
        assert max_error <= 1.0, f"TaxGlide separate income accuracy degraded - max error {max_error:.2f} CHF exceeds 1 CHF threshold"
    
    def test_separate_vs_single_income_calculation_differences(self, separate_income_test_cases, default_multiplier_codes):
        """Demonstrate the tax savings when using separate incomes vs single income approach."""
        print("\nSeparate vs Single Income Tax Impact:")
        print("SG Inc  | Fed Inc | Single Total | Separate Total | Tax Savings | Savings %")
        print("-" * 75)
        
        for test_case in separate_income_test_cases:
            # Calculate with separate incomes (new functionality)
            separate_result = _calc_once_separate(2025, test_case.sg_income, test_case.fed_income, default_multiplier_codes)
            
            # Calculate as if using single higher income (legacy approach)
            higher_income = max(test_case.sg_income, test_case.fed_income)
            single_result = _calc_once(2025, higher_income, default_multiplier_codes)
            
            tax_savings = single_result["total"] - separate_result["total"]
            savings_percent = (tax_savings / single_result["total"]) * 100
            
            print(f"{test_case.sg_income:7d} | {test_case.fed_income:7d} | {single_result['total']:11.2f} | {separate_result['total']:13.2f} | {tax_savings:10.2f} | {savings_percent:8.2f}%")
            
            # There should be meaningful tax savings when federal income is lower than SG income
            if test_case.fed_income < test_case.sg_income:
                assert tax_savings > 0, f"Expected tax savings when federal income ({test_case.fed_income}) < SG income ({test_case.sg_income})"
                assert savings_percent > 0.5, f"Expected meaningful savings percentage, got {savings_percent:.2f}%"
        
        print("\n✅ Separate income functionality provides significant tax optimization opportunities")
