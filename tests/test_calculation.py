"""Tests for core tax calculation functions."""

import pytest
from decimal import Decimal

from taxglide.engine.federal import tax_federal, federal_marginal_hundreds
from taxglide.engine.stgallen import simple_tax_sg
from taxglide.engine.multipliers import apply_multipliers, MultPick
from taxglide.engine.models import chf
from taxglide.cli import _calc_once


class TestFederalTaxCalculation:
    """Test Swiss federal tax calculations."""
    
    def test_federal_tax_zero_income(self, configs_2025):
        """Test federal tax calculation for zero income."""
        _, fed_cfg, _ = configs_2025
        result = tax_federal(chf(0), fed_cfg)
        assert result == chf(0), "Federal tax should be 0 for zero income"
    
    def test_federal_tax_below_threshold(self, configs_2025):
        """Test federal tax for income below taxable threshold."""
        _, fed_cfg, _ = configs_2025
        # According to federal.yaml, no tax below 15,200 CHF
        result = tax_federal(chf(10000), fed_cfg)
        assert result == chf(0), "No federal tax below 15,200 CHF threshold"
    
    def test_federal_tax_at_bracket_boundaries(self, configs_2025):
        """Test federal tax at exact bracket boundaries."""
        _, fed_cfg, _ = configs_2025
        
        # Test at 15,200 CHF (first taxable income)
        result = tax_federal(chf(15200), fed_cfg)
        assert result == chf(0), "Federal tax should be 0 at 15,200 CHF"
        
        # Test at 76,100 CHF (bracket boundary)
        result = tax_federal(chf(76100), fed_cfg)
        expected = chf("1149.55")  # From federal.yaml
        assert abs(result - expected) < chf("0.01"), f"Expected {expected}, got {result}"


class TestStGallenTaxCalculation:
    """Test St. Gallen cantonal tax calculations."""
    
    def test_sg_tax_zero_income(self, configs_2025):
        """Test SG tax calculation for zero income."""
        sg_cfg, _, _ = configs_2025
        result = simple_tax_sg(chf(0), sg_cfg)
        assert result == chf(0), "SG tax should be 0 for zero income"
    
    def test_sg_tax_below_threshold(self, configs_2025):
        """Test SG tax for income below taxable threshold."""
        sg_cfg, _, _ = configs_2025
        # According to stgallen.yaml, no tax below 11,600 CHF
        result = simple_tax_sg(chf(10000), sg_cfg)
        assert result == chf(0), "No SG tax below 11,600 CHF threshold"
    
    def test_sg_tax_high_income_override(self, configs_2025):
        """Test SG tax high-income override (flat 8.5% above 264,200 CHF)."""
        sg_cfg, _, _ = configs_2025
        high_income = chf(300000)
        result = simple_tax_sg(high_income, sg_cfg)
        expected = high_income * chf("0.085")  # 8.5% flat rate
        # Allow small rounding differences
        assert abs(result - expected) < chf("1.0"), f"High income override failed: expected ~{expected}, got {result}"


class TestMultiplierSystem:
    """Test the SG multiplier system."""
    
    def test_default_multipliers(self, configs_2025):
        """Test default multiplier application."""
        _, _, mult_cfg = configs_2025
        
        base_tax = chf(1000)
        default_codes = [item.code for item in mult_cfg.items if item.default_selected]
        picks = MultPick(default_codes)
        
        result = apply_multipliers(base_tax, mult_cfg, picks)
        
        # Default multipliers: KANTON (1.05) + GEMEINDE (1.38) = 2.43 total factor
        expected = base_tax * chf("2.43")
        assert result == expected, f"Expected {expected}, got {result}"
    
    def test_no_multipliers(self, configs_2025):
        """Test with no multipliers selected."""
        _, _, mult_cfg = configs_2025
        
        base_tax = chf(1000)
        picks = MultPick([])
        
        result = apply_multipliers(base_tax, mult_cfg, picks)
        assert result == chf(0), "Should be 0 with no multipliers"
    
    def test_fire_service_multiplier(self, configs_2025):
        """Test fire service multiplier."""
        _, _, mult_cfg = configs_2025
        
        base_tax = chf(1000)
        picks = MultPick(["FEUER"])
        
        result = apply_multipliers(base_tax, mult_cfg, picks)
        expected = base_tax * chf("0.14")  # FEUER rate is 0.14
        assert result == expected, f"Expected {expected}, got {result}"


class TestIntegratedCalculation:
    """Test the integrated calculation function used by CLI."""
    
    def test_taxglide_accuracy_against_official_values(self, sample_tax_cases, default_multiplier_codes):
        """Validate TaxGlide's exceptional accuracy against official Swiss tax calculations."""
        print("\nTaxGlide Accuracy Validation:")
        print("Income   | Federal Diff | SG Diff  | Total Diff | Description")
        print("-" * 65)
        
        max_error = 0.0
        total_cases = len(sample_tax_cases)
        
        for test_case in sample_tax_cases:
            result = _calc_once(2025, test_case.income, default_multiplier_codes)
            
            fed_error = abs(result["federal"] - float(test_case.federal_tax))
            sg_error = abs(result["sg_after_mult"] - float(test_case.sg_after_mult)) 
            total_error = abs(result["total"] - float(test_case.total_tax))
            
            max_error = max(max_error, fed_error, sg_error, total_error)
            
            print(f"{test_case.income:8d} | {fed_error:11.2f} | {sg_error:8.2f} | {total_error:10.2f} | {test_case.description}")
            
            # All errors should be minimal (within 1 CHF)
            assert fed_error <= 1.0, f"Federal tax error too large: {fed_error:.2f} CHF"
            assert sg_error <= 1.0, f"SG tax error too large: {sg_error:.2f} CHF" 
            assert total_error <= 1.0, f"Total tax error too large: {total_error:.2f} CHF"
        
        print(f"\nAccuracy Summary: {total_cases} test cases, max error {max_error:.2f} CHF")
        print("✅ TaxGlide achieves exceptional accuracy (≤ 1 CHF) vs official Swiss tax calculations")
        
        # Overall accuracy should be outstanding
        assert max_error <= 1.0, f"TaxGlide accuracy degraded - max error {max_error:.2f} CHF exceeds 1 CHF threshold"
    
    def test_calc_once_basic(self, configs_2025, default_multiplier_codes):
        """Test basic integrated calculation."""
        result = _calc_once(2025, 50000, default_multiplier_codes)
        
        # Basic structure checks
        assert "income" in result
        assert "federal" in result
        assert "sg_simple" in result
        assert "sg_after_mult" in result
        assert "total" in result
        assert "avg_rate" in result
        assert "marginal_total" in result
        
        assert result["income"] == 50000
        assert result["federal"] >= 0
        assert result["sg_simple"] >= 0
        assert result["sg_after_mult"] >= 0
        assert result["total"] >= 0
        assert 0 <= result["avg_rate"] <= 1.0  # Should be between 0 and 100%
    
    def test_calc_once_with_real_swiss_values(self, sample_tax_cases, default_multiplier_codes):
        """Test calculation with real Swiss tax values - should be very accurate."""
        for test_case in sample_tax_cases:
            result = _calc_once(2025, test_case.income, default_multiplier_codes)
            
            # Test against real Swiss tax calculations with small tolerance
            tolerance = 1.0  # 1 CHF tolerance for rounding differences
            
            # Federal tax should match very closely
            fed_diff = abs(result["federal"] - float(test_case.federal_tax))
            assert fed_diff <= tolerance, (
                f"Federal tax mismatch for income {test_case.income}: "
                f"expected {test_case.federal_tax}, got {result['federal']}, diff {fed_diff:.2f}"
            )
            
            # SG simple tax should match closely 
            sg_simple_diff = abs(result["sg_simple"] - float(test_case.sg_simple))
            assert sg_simple_diff <= tolerance, (
                f"SG simple tax mismatch for income {test_case.income}: "
                f"expected {test_case.sg_simple}, got {result['sg_simple']}, diff {sg_simple_diff:.2f}"
            )
            
            # SG after multipliers should match closely
            sg_mult_diff = abs(result["sg_after_mult"] - float(test_case.sg_after_mult))
            assert sg_mult_diff <= tolerance, (
                f"SG multiplied tax mismatch for income {test_case.income}: "
                f"expected {test_case.sg_after_mult}, got {result['sg_after_mult']}, diff {sg_mult_diff:.2f}"
            )
            
            # Total tax should match closely
            total_diff = abs(result["total"] - float(test_case.total_tax))
            assert total_diff <= tolerance, (
                f"Total tax mismatch for income {test_case.income}: "
                f"expected {test_case.total_tax}, got {result['total']}, diff {total_diff:.2f}"
            )
            
            # Verify structure
            assert result["income"] == test_case.income
            assert 0 <= result["avg_rate"] <= 1.0, "Average rate should be between 0 and 100%"
            assert result["picks"] == default_multiplier_codes


class TestTaxBracketTransitions:
    """Test tax calculations at bracket transition points."""
    
    def test_federal_bracket_transitions(self, configs_2025):
        """Test federal tax at various bracket transition points."""
        _, fed_cfg, _ = configs_2025
        
        # Test key transition points from federal.yaml - use 100 CHF steps since that's how federal tax works
        transitions = [
            (15100, 15300),  # Around first taxable bracket
            (33100, 33300),  # Around second bracket  
            (76000, 76200),  # Around higher bracket
            (81900, 82100),  # Around another bracket
        ]
        
        for income_low, income_high in transitions:
            tax_low = tax_federal(chf(income_low), fed_cfg)
            tax_high = tax_federal(chf(income_high), fed_cfg)
            
            # Tax should increase or stay the same, never decrease
            assert tax_high >= tax_low, f"Tax should not decrease: {income_low}->tax:{tax_low}, {income_high}->tax:{tax_high}"
            
            # For federal tax with 100 CHF steps, the increase per 200 CHF should be reasonable
            # Max marginal rate in config is about 13.2%, so for 200 CHF that's about 26.4 CHF max
            income_diff = income_high - income_low
            tax_diff = tax_high - tax_low
            max_reasonable_increase = chf(income_diff * 0.15)  # 15% is reasonable upper bound for marginal rate
            
            assert tax_diff <= max_reasonable_increase, f"Tax increase seems too large: {tax_diff} for income change {income_diff}"
