"""Tests for married joint filing functionality."""

import pytest
from decimal import Decimal

from taxglide.io.loader import load_configs_with_filing_status
from taxglide.engine.federal import tax_federal_with_filing_status
from taxglide.engine.stgallen import simple_tax_sg_with_filing_status
from taxglide.engine.multipliers import apply_multipliers, MultPick
from taxglide.engine.models import chf
from taxglide.cli import _calc_once_separate


class TestMarriedJointFiling:
    """Test married joint filing calculations."""
    
    def test_married_joint_official_verification(self, config_root):
        """Test official verification case: 94,000 CHF should produce exact official results."""
        income = 94000
        income_d = chf(income)
        
        # Expected official results for married joint filing (excluding FEUER)
        expected_sg_total = Decimal('11197.45')  # Kantons- und Gemeindesteuern
        expected_fed_total = Decimal('1525.00')   # Direkte Bundessteuer
        
        # Load married joint configurations
        sg_cfg, fed_cfg, mult_cfg = load_configs_with_filing_status(config_root, 2025, "married_joint")
        
        # Calculate SG simple tax (uses income splitting)
        sg_simple = simple_tax_sg_with_filing_status(income_d, sg_cfg, "married_joint")
        
        # Apply multipliers (excluding FEUER as per specification)
        default_picks = [i.code for i in mult_cfg.items if i.default_selected and i.code != 'FEUER']
        sg_after_mult = apply_multipliers(sg_simple, mult_cfg, MultPick(default_picks))
        
        # Calculate Federal tax (uses married tax table)
        fed_tax = tax_federal_with_filing_status(income_d, fed_cfg, "married_joint")
        
        # Verify results match official calculations within tight tolerance
        sg_diff = abs(float(sg_after_mult) - float(expected_sg_total))
        fed_diff = abs(float(fed_tax) - float(expected_fed_total))
        
        assert sg_diff < 0.1, f"SG tax mismatch: expected {expected_sg_total}, got {sg_after_mult}, diff {sg_diff:.2f}"
        assert fed_diff < 0.1, f"Federal tax mismatch: expected {expected_fed_total}, got {fed_tax}, diff {fed_diff:.2f}"
        
        # Also verify the total
        total = sg_after_mult + fed_tax
        expected_total = expected_sg_total + expected_fed_total
        total_diff = abs(float(total) - float(expected_total))
        assert total_diff < 0.1, f"Total tax mismatch: expected {expected_total}, got {total}, diff {total_diff:.2f}"
    
    def test_married_vs_single_filing_differences(self, config_root):
        """Test that married joint filing provides tax savings vs single filing."""
        income = 94000
        income_d = chf(income)
        
        # Calculate for single filing
        sg_cfg_single, fed_cfg_single, mult_cfg = load_configs_with_filing_status(config_root, 2025, "single")
        default_picks = [i.code for i in mult_cfg.items if i.default_selected and i.code != 'FEUER']
        
        sg_simple_single = simple_tax_sg_with_filing_status(income_d, sg_cfg_single, "single")
        sg_after_mult_single = apply_multipliers(sg_simple_single, mult_cfg, MultPick(default_picks))
        fed_single = tax_federal_with_filing_status(income_d, fed_cfg_single, "single")
        total_single = sg_after_mult_single + fed_single
        
        # Calculate for married joint filing
        sg_cfg_married, fed_cfg_married, _ = load_configs_with_filing_status(config_root, 2025, "married_joint")
        
        sg_simple_married = simple_tax_sg_with_filing_status(income_d, sg_cfg_married, "married_joint")
        sg_after_mult_married = apply_multipliers(sg_simple_married, mult_cfg, MultPick(default_picks))
        fed_married = tax_federal_with_filing_status(income_d, fed_cfg_married, "married_joint")
        total_married = sg_after_mult_married + fed_married
        
        # Married filing should result in lower taxes
        assert sg_after_mult_married < sg_after_mult_single, "Married SG tax should be lower than single"
        assert fed_married < fed_single, "Married federal tax should be lower than single"
        assert total_married < total_single, "Total married tax should be lower than single"
        
        # Calculate savings
        total_savings = total_single - total_married
        savings_percentage = float(total_savings / total_single * 100)
        
        # At this income level, savings should be substantial (>20%)
        assert savings_percentage > 20, f"Expected significant savings, got {savings_percentage:.1f}%"
        
        # Verify specific savings amounts are reasonable
        assert total_savings > chf(4000), f"Total savings should exceed 4,000 CHF, got {total_savings}"
    
    def test_sg_income_splitting_logic(self, config_root):
        """Test that SG income splitting works correctly for married couples."""
        income = 100000
        income_d = chf(income)
        
        sg_cfg, _, _ = load_configs_with_filing_status(config_root, 2025, "single")
        
        # Calculate tax at half income
        half_income = income_d / 2
        tax_at_half = simple_tax_sg_with_filing_status(half_income, sg_cfg, "single")
        
        # Calculate effective rate at half income
        if half_income > 0:
            effective_rate = tax_at_half / half_income
        else:
            effective_rate = chf(0)
        
        # Manual married calculation: full income * effective rate at half income
        expected_married_tax = income_d * effective_rate
        
        # Use the married filing function
        actual_married_tax = simple_tax_sg_with_filing_status(income_d, sg_cfg, "married_joint")
        
        # Should match within rounding differences
        diff = abs(float(expected_married_tax) - float(actual_married_tax))
        assert diff < 1.0, f"Income splitting calculation mismatch: expected {expected_married_tax}, got {actual_married_tax}"
    
    def test_federal_table_switching(self, config_root):
        """Test that correct federal tax tables are loaded for each filing status."""
        # This test verifies that different federal configurations are loaded
        _, fed_cfg_single, _ = load_configs_with_filing_status(config_root, 2025, "single")
        _, fed_cfg_married, _ = load_configs_with_filing_status(config_root, 2025, "married_joint")
        
        # The configurations should be different (married should use federal_married.yaml)
        # We can test this by comparing tax at a specific income level
        test_income = chf(94000)
        
        single_fed_tax = tax_federal_with_filing_status(test_income, fed_cfg_single, "single")
        married_fed_tax = tax_federal_with_filing_status(test_income, fed_cfg_married, "married_joint")
        
        # They should produce different results
        assert single_fed_tax != married_fed_tax, "Single and married federal taxes should differ"
        
        # Married should be lower at this income level
        assert married_fed_tax < single_fed_tax, "Married federal tax should be lower than single"
    
    def test_cli_integration_married_filing(self, config_root):
        """Test CLI integration with married filing status."""
        # Test the CLI calculation function with married filing
        result = _calc_once_separate(2025, 94000, 94000, ["KANTON", "GEMEINDE"], "married_joint")
        
        # Verify structure includes filing status
        assert "filing_status" in result
        assert result["filing_status"] == "married_joint"
        
        # Verify expected values
        expected_sg = 11197.44  # Allow small rounding difference
        expected_fed = 1525.00
        
        assert abs(result["sg_after_mult"] - expected_sg) < 0.1
        assert abs(result["federal"] - expected_fed) < 0.1
        assert abs(result["total"] - (expected_sg + expected_fed)) < 0.1
    
    def test_edge_cases_married_filing(self, config_root):
        """Test edge cases for married filing."""
        sg_cfg, fed_cfg, mult_cfg = load_configs_with_filing_status(config_root, 2025, "married_joint")
        
        # Test zero income
        zero_sg = simple_tax_sg_with_filing_status(chf(0), sg_cfg, "married_joint")
        zero_fed = tax_federal_with_filing_status(chf(0), fed_cfg, "married_joint")
        assert zero_sg == chf(0), "Zero income should result in zero SG tax"
        assert zero_fed == chf(0), "Zero income should result in zero federal tax"
        
        # Test very low income (below thresholds)
        low_income = chf(5000)
        low_sg = simple_tax_sg_with_filing_status(low_income, sg_cfg, "married_joint")
        low_fed = tax_federal_with_filing_status(low_income, fed_cfg, "married_joint")
        assert low_sg == chf(0), "Income below SG threshold should result in zero SG tax"
        assert low_fed == chf(0), "Income below federal threshold should result in zero federal tax"


class TestMarriedFilingAccuracy:
    """Test accuracy of married filing against known values."""
    
    @pytest.mark.parametrize("income,expected_sg,expected_fed", [
        (94000, 11197.44, 1525.00),  # Official test case
        # Add more test cases here as they become available
    ])
    def test_married_filing_accuracy(self, config_root, income, expected_sg, expected_fed):
        """Test married filing accuracy against known official values."""
        income_d = chf(income)
        
        sg_cfg, fed_cfg, mult_cfg = load_configs_with_filing_status(config_root, 2025, "married_joint")
        
        # Calculate taxes
        sg_simple = simple_tax_sg_with_filing_status(income_d, sg_cfg, "married_joint")
        default_picks = [i.code for i in mult_cfg.items if i.default_selected and i.code != 'FEUER']
        sg_after_mult = apply_multipliers(sg_simple, mult_cfg, MultPick(default_picks))
        fed_tax = tax_federal_with_filing_status(income_d, fed_cfg, "married_joint")
        
        # Verify accuracy
        sg_diff = abs(float(sg_after_mult) - expected_sg)
        fed_diff = abs(float(fed_tax) - expected_fed)
        
        assert sg_diff < 0.1, f"SG tax inaccurate for income {income}: expected {expected_sg}, got {sg_after_mult}"
        assert fed_diff < 0.1, f"Federal tax inaccurate for income {income}: expected {expected_fed}, got {fed_tax}"
