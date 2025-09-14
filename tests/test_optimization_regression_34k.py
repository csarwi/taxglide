"""Regression test for optimization issue with ~34K income.

This test captures the specific scenario where optimization recommends
unreasonably low deductions (200-700 CHF) for ~34K income with 10K max deduction.
This should catch similar issues in the future.
"""

import pytest
from decimal import Decimal

from taxglide.engine.optimize import optimize_deduction_adaptive
from taxglide.engine.federal import tax_federal
from taxglide.engine.stgallen import simple_tax_sg
from taxglide.engine.multipliers import apply_multipliers, MultPick
from taxglide.engine.models import chf


class TestOptimization34kRegression:
    """Regression test for 34k income optimization bug."""

    def test_34567_income_optimization_regression(self, configs_2025):
        """Test that optimization finds reasonable deduction for 34,567 CHF income.
        
        This specific income/max_deduction combination was showing unreasonably
        low optimal deductions (200-700 CHF) when much larger deductions would
        provide better absolute savings.
        """
        sg_cfg, fed_cfg, mult_cfg = configs_2025
        
        def calc_fn(income: Decimal):
            sg_simple = simple_tax_sg(income, sg_cfg)
            sg_after = apply_multipliers(sg_simple, mult_cfg, MultPick(["KANTON", "GEMEINDE"]))
            fed = tax_federal(income, fed_cfg)
            total = sg_after + fed
            return {"total": total, "federal": fed}
        
        # This is the exact scenario from the bug report
        income = chf(34567)
        max_deduction = 10000
        
        # Use the same adaptive tolerance logic as CLI
        from taxglide.cli import _get_adaptive_tolerance_bp
        tolerance_bp = _get_adaptive_tolerance_bp(int(income))
        
        result = optimize_deduction_adaptive(
            income=income,
            max_deduction=max_deduction,
            step=100,
            calc_fn=calc_fn,
            initial_roi_tolerance_bp=tolerance_bp,  # Use CLI's adaptive tolerance
            enable_adaptive_retry=True,  # Ensure we use the adaptive logic
        )
        
        assert result["sweet_spot"] is not None, "Should find an optimization"
        
        sweet_spot = result["sweet_spot"]
        deduction = sweet_spot["deduction"]
        tax_saved = sweet_spot["tax_saved_absolute"]
        roi_percent = (tax_saved / deduction * 100) if deduction > 0 else 0
        utilization = deduction / max_deduction
        
        print(f"\nRegression test results for {income} CHF income:")
        print(f"  Recommended deduction: {deduction:,} CHF")
        print(f"  Tax savings: {tax_saved:.2f} CHF")
        print(f"  ROI: {roi_percent:.1f}%")
        print(f"  Utilization: {utilization:.1%} of max deduction")
        
        # The bug was showing ~700 CHF deduction with 20.3% ROI
        # But with 10K max deduction available, we should expect much better utilization
        
        # Regression prevention criteria:
        
        # 1. For this income level with 10K max deduction, we expect reasonable utilization (relaxed since users are educated)
        assert utilization >= 0.10, f"Utilization {utilization:.1%} seems too low - possible regression to conservative optimization"
        
        # 2. Tax savings should be reasonable given the income and deduction space (relaxed threshold)
        assert tax_saved >= 200, f"Tax savings {tax_saved:.2f} CHF seems too low for {income} income with {max_deduction} max deduction"
        
        # 3. ROI should be reasonable but not necessarily super high
        assert 10 <= roi_percent <= 100, f"ROI {roi_percent:.1f}% should be in reasonable range (10-100%)"
        
        # 4. Deduction should be meaningful for this income level (relaxed threshold)
        assert deduction >= 1000, f"Deduction {deduction} CHF seems too small for {income} income with {max_deduction} available"
        
        # 5. Utilization should not be trivial for mid-range income (relaxed threshold)
        income_ratio = deduction / float(income)
        assert income_ratio >= 0.03, f"Deduction {income_ratio:.2%} of income seems too small"
        
        # Check if adaptive retry was used (indicates the initial optimization was too conservative)
        if "adaptive_retry_used" in result:
            retry_info = result["adaptive_retry_used"]
            print(f"  Adaptive retry used: {retry_info['selection_reason']}")
            print(f"  Original tolerance: {retry_info['original_tolerance_bp']} bp")
            print(f"  Chosen tolerance: {retry_info['chosen_tolerance_bp']} bp")
            print(f"  ROI improvement: {retry_info['roi_improvement']:.2f}%")
            print(f"  Utilization improvement: {retry_info['utilization_improvement']:.2%}")
        
        # Verify this prevents the original bug scenario
        assert not (deduction <= 800 and utilization < 0.10), \
            "This looks like the original bug: very small deduction with low utilization"
    
    def test_similar_income_range_consistency(self, configs_2025):
        """Test that similar incomes around 34K show consistent optimization patterns."""
        sg_cfg, fed_cfg, mult_cfg = configs_2025
        
        def calc_fn(income: Decimal):
            sg_simple = simple_tax_sg(income, sg_cfg)
            sg_after = apply_multipliers(sg_simple, mult_cfg, MultPick(["KANTON", "GEMEINDE"]))
            fed = tax_federal(income, fed_cfg)
            total = sg_after + fed
            return {"total": total, "federal": fed}
        
        # Test range around the problematic income
        test_incomes = [32000, 33000, 34000, 34567, 35000, 36000]
        max_deduction = 10000
        
        results = []
        
        for income in test_incomes:
            result = optimize_deduction_adaptive(
                income=chf(income),
                max_deduction=max_deduction,
                step=100,
                calc_fn=calc_fn,
                enable_adaptive_retry=True,
            )
            
            if result["sweet_spot"]:
                sweet_spot = result["sweet_spot"]
                deduction = sweet_spot["deduction"]
                tax_saved = sweet_spot["tax_saved_absolute"]
                utilization = deduction / max_deduction
                
                results.append({
                    "income": income,
                    "deduction": deduction,
                    "tax_saved": tax_saved,
                    "utilization": utilization,
                    "roi": (tax_saved / deduction * 100) if deduction > 0 else 0
                })
        
        assert len(results) >= 5, "Should find optimization for most incomes in this range"
        
        # Check for consistency - deductions shouldn't vary wildly for similar incomes
        deductions = [r["deduction"] for r in results]
        utilizations = [r["utilization"] for r in results]
        
        # No deduction should be super tiny for this income range with 10K available
        min_expected_deduction = 1000  # At least 1K CHF for mid-income with 10K available
        tiny_deductions = [r for r in results if r["deduction"] < min_expected_deduction]
        
        if tiny_deductions:
            print(f"\nFound {len(tiny_deductions)} suspiciously small deductions:")
            for r in tiny_deductions:
                print(f"  Income {r['income']:,}: {r['deduction']} CHF deduction ({r['utilization']:.1%} utilization)")
        
        assert len(tiny_deductions) <= 1, "Too many tiny deductions suggest systematic optimization issues"
        
        # Average utilization should be reasonable for this income range
        avg_utilization = sum(utilizations) / len(utilizations)
        assert avg_utilization >= 0.20, f"Average utilization {avg_utilization:.1%} seems too low for {max_deduction} max deduction"
        
        print(f"\nConsistency check passed for {len(results)} incomes around 34K:")
        print(f"  Average deduction: {sum(deductions) / len(deductions):,.0f} CHF")
        print(f"  Average utilization: {avg_utilization:.1%}")
        print(f"  Deduction range: {min(deductions):,} - {max(deductions):,} CHF")


class TestOptimizationAdaptiveRetry:
    """Test the adaptive retry mechanism specifically."""
    
    def test_adaptive_retry_triggers_for_low_utilization(self, configs_2025):
        """Test that adaptive retry triggers when initial optimization shows low utilization."""
        sg_cfg, fed_cfg, mult_cfg = configs_2025
        
        def calc_fn(income: Decimal):
            sg_simple = simple_tax_sg(income, sg_cfg)
            sg_after = apply_multipliers(sg_simple, mult_cfg, MultPick(["KANTON", "GEMEINDE"]))
            fed = tax_federal(income, fed_cfg)
            total = sg_after + fed
            return {"total": total, "federal": fed}
        
        # Use the problematic income level
        income = chf(34567)
        max_deduction = 10000
        
        # Test with adaptive retry enabled
        result_adaptive = optimize_deduction_adaptive(
            income=income,
            max_deduction=max_deduction,
            step=100,
            calc_fn=calc_fn,
            enable_adaptive_retry=True,
            min_utilization_threshold=0.30,  # 30% threshold
        )
        
        # Test without adaptive retry (original algorithm)
        result_original = optimize_deduction_adaptive(
            income=income,
            max_deduction=max_deduction,
            step=100,
            calc_fn=calc_fn,
            enable_adaptive_retry=False,
        )
        
        assert result_adaptive["sweet_spot"] is not None
        assert result_original["sweet_spot"] is not None
        
        adaptive_deduction = result_adaptive["sweet_spot"]["deduction"]
        original_deduction = result_original["sweet_spot"]["deduction"]
        
        adaptive_utilization = adaptive_deduction / max_deduction
        original_utilization = original_deduction / max_deduction
        
        print(f"\nAdaptive retry test results:")
        print(f"  Original optimization: {original_deduction:,} CHF ({original_utilization:.1%} utilization)")
        print(f"  Adaptive optimization: {adaptive_deduction:,} CHF ({adaptive_utilization:.1%} utilization)")
        
        # The adaptive version should find better utilization when original is too conservative
        if original_utilization < 0.30:  # Low utilization should trigger retry
            assert "adaptive_retry_info" in result_adaptive, "Adaptive retry should have been triggered"
            
            # Adaptive should find better utilization
            assert adaptive_utilization >= original_utilization, \
                "Adaptive retry should find at least as good utilization"
            
            # If retry was used, it should show improvement
            if "adaptive_retry_used" in result_adaptive:
                assert adaptive_deduction > original_deduction, \
                    "When adaptive retry is used, it should find larger deduction"
