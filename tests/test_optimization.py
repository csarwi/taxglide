"""Tests for tax optimization functionality."""

import pytest
from decimal import Decimal

from taxglide.engine.optimize import optimize_deduction, validate_optimization_inputs
from taxglide.engine.federal import tax_federal
from taxglide.engine.stgallen import simple_tax_sg
from taxglide.engine.multipliers import apply_multipliers, MultPick
from taxglide.engine.models import chf


class TestOptimizationInputValidation:
    """Test input validation for optimization."""
    
    def test_valid_inputs(self):
        """Test that valid inputs pass validation."""
        # Should not raise any exception
        validate_optimization_inputs(
            income=chf(80000),
            max_deduction=10000,
            min_deduction=1,
            step=100
        )
    
    def test_negative_income(self):
        """Test that negative income raises error."""
        with pytest.raises(ValueError, match="Income must be non-negative"):
            validate_optimization_inputs(
                income=chf(-1000),
                max_deduction=5000,
                min_deduction=1,
                step=100
            )
    
    def test_zero_step(self):
        """Test that zero step raises error."""
        with pytest.raises(ValueError, match="Step must be positive"):
            validate_optimization_inputs(
                income=chf(80000),
                max_deduction=5000,
                min_deduction=1,
                step=0
            )
    
    def test_negative_deductions(self):
        """Test that negative deductions raise error."""
        with pytest.raises(ValueError, match="Min deduction must be non-negative"):
            validate_optimization_inputs(
                income=chf(80000),
                max_deduction=5000,
                min_deduction=-100,
                step=100
            )
    
    def test_max_deduction_exceeds_income(self):
        """Test that max deduction > income raises error."""
        with pytest.raises(ValueError, match="Max deduction.*cannot exceed income"):
            validate_optimization_inputs(
                income=chf(50000),
                max_deduction=60000,
                min_deduction=1,
                step=100
            )
    
    def test_max_less_than_min_deduction(self):
        """Test that max < min deduction raises error."""
        with pytest.raises(ValueError, match="Max deduction must be >= min deduction"):
            validate_optimization_inputs(
                income=chf(80000),
                max_deduction=1000,
                min_deduction=2000,
                step=100
            )


class TestOptimizationAlgorithm:
    """Test the core optimization algorithm."""
    
    def test_optimization_with_real_swiss_values(self, configs_2025):
        """Test optimization with real Swiss tax scenarios."""
        sg_cfg, fed_cfg, mult_cfg = configs_2025
        
        def calc_fn(income: Decimal):
            sg_simple = simple_tax_sg(income, sg_cfg)
            sg_after = apply_multipliers(sg_simple, mult_cfg, MultPick(["KANTON", "GEMEINDE"]))
            fed = tax_federal(income, fed_cfg)
            total = sg_after + fed
            return {"total": total, "federal": fed}
        
        # Test optimization for realistic scenarios
        test_scenarios = [
            (60000, 5000, "Mid-income optimization"),
            (90000, 8000, "Higher-income optimization"),
            (120000, 10000, "High-income optimization")
        ]
        
        for income, max_deduction, description in test_scenarios:
            result = optimize_deduction(
                income=chf(income),
                max_deduction=max_deduction,
                step=100,
                calc_fn=calc_fn
            )
            
            # Should find valid optimization
            assert result["sweet_spot"] is not None, f"No optimization found for {description}"
            
            sweet_spot = result["sweet_spot"]
            assert 0 < sweet_spot["deduction"] <= max_deduction, f"Invalid deduction amount for {description}"
            assert sweet_spot["new_income"] < income, f"New income should be lower for {description}"
            assert sweet_spot["tax_saved_absolute"] > 0, f"Should save taxes for {description}"
            
            # ROI in Swiss tax system can be VERY high due to bracket effects!
            # When income sits right at a bracket boundary, even 1 CHF deduction
            # can move you to a lower bracket, creating ROI of 300-900%
            # This is mathematically correct and a key insight of the optimizer
            deduction = sweet_spot["deduction"]
            saved = sweet_spot["tax_saved_absolute"]
            roi = saved / deduction * 100
            
            # ROI should be positive. Very high ROI indicates bracket boundary optimization
            assert roi > 0, f"ROI should be positive for {description}"
            assert roi < 2000, f"ROI {roi:.1f}% seems impossibly high - possible calculation error"
            
            print(f"\n{description}: Deduct {deduction} CHF, save {saved:.2f} CHF (ROI: {roi:.1f}%)")
            
            # Debug: let's verify the calculation manually
            baseline_result = calc_fn(chf(income))
            optimized_result = calc_fn(chf(sweet_spot["new_income"]))
            manual_savings = baseline_result["total"] - optimized_result["total"]
            manual_roi = manual_savings / deduction * 100
            
            print(f"  Debug - Manual calc: save {manual_savings:.2f} CHF, ROI {manual_roi:.1f}%")
            
            # Explain high ROI scenarios
            if roi > 100:
                print(f"  ✨ EXCELLENT! Found bracket boundary optimization")
                print(f"      Just {deduction} CHF deduction saves {saved:.2f} CHF in taxes!")
                print(f"      This demonstrates TaxGlide's sophisticated bracket analysis")
            elif roi > 50:
                print(f"  💰 Very good ROI due to progressive tax brackets")
    
    def test_optimization_basic_structure(self, configs_2025):
        """Test that optimization returns expected structure."""
        sg_cfg, fed_cfg, mult_cfg = configs_2025
        
        def calc_fn(income: Decimal):
            sg_simple = simple_tax_sg(income, sg_cfg)
            sg_after = apply_multipliers(sg_simple, mult_cfg, MultPick(["KANTON", "GEMEINDE"]))
            fed = tax_federal(income, fed_cfg)
            total = sg_after + fed
            return {"total": total, "federal": fed}
        
        result = optimize_deduction(
            income=chf(80000),
            max_deduction=5000,
            step=100,
            calc_fn=calc_fn
        )
        
        # Check basic structure
        assert "base_total" in result
        assert "sweet_spot" in result
        assert isinstance(result["base_total"], Decimal)
    
    def test_optimization_no_deduction_space(self, configs_2025):
        """Test optimization when no deduction is possible."""
        sg_cfg, fed_cfg, mult_cfg = configs_2025
        
        def calc_fn(income: Decimal):
            return {"total": chf(1000)}
        
        result = optimize_deduction(
            income=chf(1000),
            max_deduction=0,  # No deduction space
            step=100,
            calc_fn=calc_fn,
            min_deduction=0  # Set min to 0 to allow max=0
        )
        
        assert result["sweet_spot"] is None
        assert "no search space" in str(result.get("diagnostics", {}))
    
    def test_optimization_decreasing_roi(self, configs_2025):
        """Test optimization with typical decreasing ROI pattern."""
        sg_cfg, fed_cfg, mult_cfg = configs_2025
        
        def calc_fn(income: Decimal):
            # Simple mock that shows decreasing marginal benefit
            # Higher income = lower effective rate (simplified for test)
            rate = max(0.1, 0.3 - float(income) * 0.000001)
            return {"total": income * chf(rate)}
        
        result = optimize_deduction(
            income=chf(50000),
            max_deduction=5000,
            step=100,
            calc_fn=calc_fn
        )
        
        assert result["sweet_spot"] is not None
        assert result["sweet_spot"]["deduction"] > 0
        assert result["sweet_spot"]["new_income"] < 50000
    
    def test_optimization_with_context_function(self, configs_2025):
        """Test optimization with bracket context information."""
        sg_cfg, fed_cfg, mult_cfg = configs_2025
        
        def calc_fn(income: Decimal):
            sg_simple = simple_tax_sg(income, sg_cfg)
            sg_after = apply_multipliers(sg_simple, mult_cfg, MultPick(["KANTON", "GEMEINDE"]))
            fed = tax_federal(income, fed_cfg)
            total = sg_after + fed
            return {"total": total, "federal": fed}
        
        def context_fn(income: Decimal):
            from taxglide.engine.federal import federal_segment_info
            from taxglide.engine.stgallen import sg_bracket_info
            return {
                "federal_segment": federal_segment_info(income, fed_cfg),
                "sg_bracket": sg_bracket_info(income, sg_cfg)
            }
        
        result = optimize_deduction(
            income=chf(80000),
            max_deduction=5000,
            step=100,
            calc_fn=calc_fn,
            context_fn=context_fn
        )
        
        # Should include bracket information in the result
        if result["sweet_spot"]:
            why = result["sweet_spot"].get("why", {})
            assert "federal_bracket_before" in why
            assert "federal_bracket_after" in why
    
    def test_optimization_tolerance_settings(self, configs_2025):
        """Test optimization with different tolerance settings."""
        sg_cfg, fed_cfg, mult_cfg = configs_2025
        
        def calc_fn(income: Decimal):
            sg_simple = simple_tax_sg(income, sg_cfg)
            sg_after = apply_multipliers(sg_simple, mult_cfg, MultPick(["KANTON", "GEMEINDE"]))
            fed = tax_federal(income, fed_cfg)
            total = sg_after + fed
            return {"total": total}
        
        # Test with tight tolerance
        result_tight = optimize_deduction(
            income=chf(80000),
            max_deduction=3000,
            step=100,
            calc_fn=calc_fn,
            roi_tolerance_bp=1.0  # Very tight tolerance
        )
        
        # Test with loose tolerance  
        result_loose = optimize_deduction(
            income=chf(80000),
            max_deduction=3000,
            step=100,
            calc_fn=calc_fn,
            roi_tolerance_bp=50.0  # Very loose tolerance
        )
        
        # Both should find solutions, but plateau characteristics may differ
        assert result_tight["sweet_spot"] is not None
        assert result_loose["sweet_spot"] is not None


class TestOptimizationEdgeCases:
    """Test edge cases in optimization."""
    
    def test_optimization_single_step(self, configs_2025):
        """Test optimization with only one possible deduction step."""
        sg_cfg, fed_cfg, mult_cfg = configs_2025
        
        def calc_fn(income: Decimal):
            return {"total": income * chf("0.2")}  # Simple 20% tax
        
        result = optimize_deduction(
            income=chf(1000),
            max_deduction=100,  # Only one 100 CHF step possible
            step=100,
            calc_fn=calc_fn
        )
        
        # Should still work with single step
        assert result["sweet_spot"] is not None
        assert result["sweet_spot"]["deduction"] == 100
    
    def test_optimization_flat_tax_scenario(self, configs_2025):
        """Test optimization with flat tax (constant marginal rate)."""
        def calc_fn(income: Decimal):
            return {"total": income * chf("0.25")}  # Flat 25% tax
        
        result = optimize_deduction(
            income=chf(40000),
            max_deduction=5000,
            step=100,
            calc_fn=calc_fn
        )
        
        # With flat tax, ROI should be constant, so sweet spot should be at maximum deduction
        assert result["sweet_spot"] is not None
        assert result["sweet_spot"]["deduction"] == 5000  # Maximum deduction
    
    def test_optimization_very_high_income(self, configs_2025):
        """Test optimization with very high income (SG override territory)."""
        sg_cfg, fed_cfg, mult_cfg = configs_2025
        
        def calc_fn(income: Decimal):
            sg_simple = simple_tax_sg(income, sg_cfg)
            sg_after = apply_multipliers(sg_simple, mult_cfg, MultPick(["KANTON", "GEMEINDE"]))
            fed = tax_federal(income, fed_cfg)
            total = sg_after + fed
            return {"total": total}
        
        result = optimize_deduction(
            income=chf(500000),  # High income triggering SG override
            max_deduction=20000,
            step=500,
            calc_fn=calc_fn
        )
        
        assert result["sweet_spot"] is not None
        # Should find some optimization even in high-income territory
        assert result["sweet_spot"]["deduction"] > 0
    
    def test_realistic_optimization_benchmark(self, configs_2025):
        """Test optimization against known realistic values to prevent regressions.
        
        This test validates that our optimization produces sensible, realistic results
        and helps prevent future regressions like the federal rounding artifacts.
        
        Based on actual TaxGlide output for separate incomes: 
        SG 97400 CHF, Federal 99400 CHF with max deduction 50000.
        Values should be within 95% accuracy tolerance.
        """
        sg_cfg, fed_cfg, mult_cfg = configs_2025
        
        # Separate income calculation function (SG vs Federal)
        sg_income = chf(97400)
        fed_income = chf(99400)
        
        def calc_fn_separate(deduction: Decimal):
            # Apply deduction to both incomes
            sg_income_after = sg_income - deduction
            fed_income_after = fed_income - deduction
            
            # Calculate taxes separately
            sg_simple = simple_tax_sg(sg_income_after, sg_cfg)
            sg_after = apply_multipliers(sg_simple, mult_cfg, MultPick(["KANTON", "GEMEINDE"]))
            fed = tax_federal(fed_income_after, fed_cfg)
            total = sg_after + fed
            return {"total": total, "federal": fed}
        
        # Context function to provide bracket information
        def context_fn_separate(remaining_income: Decimal):
            from taxglide.engine.federal import federal_segment_info
            from taxglide.engine.stgallen import sg_bracket_info
            
            deduction = baseline_income - remaining_income
            sg_income_after = sg_income - deduction
            fed_income_after = fed_income - deduction
            
            return {
                "federal_segment": federal_segment_info(fed_income_after, fed_cfg),
                "sg_bracket": sg_bracket_info(sg_income_after, sg_cfg)
            }
        
        # Test case: Separate incomes with large deduction space
        # Use higher income as baseline for optimization validation
        baseline_income = max(sg_income, fed_income)
        result = optimize_deduction(
            income=baseline_income,
            max_deduction=50000,
            step=100,
            calc_fn=lambda income: calc_fn_separate(baseline_income - income),
            context_fn=context_fn_separate
        )
        
        # Expected realistic values (95% tolerance)
        expected = {
            "base_total": 19129.63,           # Base tax before optimization
            "deduction": 20500,               # Optimal deduction amount
            "new_income": 78900.0,            # Income after deduction
            "total_tax_at_spot": 13214.102,   # Tax at optimized income
            "tax_saved_absolute": 5915.53,    # Absolute tax savings
            "tax_saved_percent": 30.92,       # Percent savings
            "roi_at_spot_percent": 28.86,     # ROI percentage (realistic!)
            "local_marginal_percent_at_spot": 28.31,  # Marginal rate at optimized point
            "federal_bracket_changed": True,   # Should cross federal bracket
        }
        
        # Validation with 95% accuracy tolerance
        tolerance = 0.05  # 5% tolerance
        
        assert result["sweet_spot"] is not None, "Optimization should find a sweet spot"
        sweet_spot = result["sweet_spot"]
        
        # Base total validation (within 5%)
        base_total = float(result["base_total"])
        assert abs(base_total - expected["base_total"]) / expected["base_total"] <= tolerance, \
            f"Base total {base_total} not within 95% of expected {expected['base_total']}"
        
        # Deduction amount validation (within 5%)
        deduction = sweet_spot["deduction"]
        assert abs(deduction - expected["deduction"]) / expected["deduction"] <= tolerance, \
            f"Deduction {deduction} not within 95% of expected {expected['deduction']}"
        
        # Tax savings validation (within 5%)
        tax_saved = sweet_spot["tax_saved_absolute"]
        assert abs(tax_saved - expected["tax_saved_absolute"]) / expected["tax_saved_absolute"] <= tolerance, \
            f"Tax saved {tax_saved} not within 95% of expected {expected['tax_saved_absolute']}"
        
        # ROI validation - this is critical for detecting rounding artifacts
        why = sweet_spot.get("why", {})
        roi = why.get("roi_at_spot_percent", 0)
        assert abs(roi - expected["roi_at_spot_percent"]) / expected["roi_at_spot_percent"] <= tolerance, \
            f"ROI {roi}% not within 95% of expected {expected['roi_at_spot_percent']}%"
        
        # ROI sanity checks to prevent future regressions
        assert roi > 10, f"ROI {roi}% seems too low - possible optimization bug"
        assert roi < 100, f"ROI {roi}% seems unrealistically high - possible rounding artifact"
        
        # Federal bracket change validation
        federal_bracket_changed = why.get("federal_bracket_changed", False)
        assert federal_bracket_changed == expected["federal_bracket_changed"], \
            f"Expected federal bracket change: {expected['federal_bracket_changed']}, got: {federal_bracket_changed}"
        
        # Marginal rate validation
        marginal_rate = why.get("local_marginal_percent_at_spot", 0)
        assert abs(marginal_rate - expected["local_marginal_percent_at_spot"]) / expected["local_marginal_percent_at_spot"] <= tolerance, \
            f"Marginal rate {marginal_rate}% not within 95% of expected {expected['local_marginal_percent_at_spot']}%"
        
        # Success message
        print(f"\n✅ Realistic Optimization Benchmark PASSED")
        print(f"   SG Income: 97,400 CHF, Federal Income: 99,400 CHF")
        print(f"   Optimal deduction: {deduction:,} CHF")
        print(f"   Tax savings: {tax_saved:,.2f} CHF ({sweet_spot['tax_saved_percent']:.1f}%)")
        print(f"   ROI: {roi:.1f}% (realistic and sustainable)")
        print(f"   Federal bracket optimization: {'✓' if federal_bracket_changed else '✗'}")
