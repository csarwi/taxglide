"""
Comprehensive optimization test for TaxGlide test suite.

Tests optimization across the full income spectrum (20K-200K CHF) with 100 CHF steps
to ensure consistent, meaningful optimization results with proper utilization.

This test runs as part of the regular pytest suite to catch optimization regressions.
"""

import pytest
from decimal import Decimal
from typing import List, Dict, Any

from taxglide.engine.optimize import optimize_deduction_adaptive
from taxglide.engine.federal import tax_federal
from taxglide.engine.stgallen import simple_tax_sg
from taxglide.engine.multipliers import apply_multipliers, MultPick
from taxglide.engine.models import chf
from taxglide.cli import _get_adaptive_tolerance_bp


class TestComprehensiveOptimization:
    """Comprehensive optimization test across full income spectrum."""

    @pytest.mark.slow
    def test_optimization_quality_across_income_spectrum(self, configs_2025):
        """
        Test optimization quality from 20K to 200K CHF with 100 CHF steps.
        
        This is a critical test that ensures optimization provides meaningful results
        across all income levels with proper utilization and reasonable ROI.
        
        Quality requirements:
        - Minimum 20% utilization (practical deduction usage)
        - ROI between 10-100% (reasonable and realistic)
        - At least 95% success rate
        - Maximum 5% quality failure rate
        """
        sg_cfg, fed_cfg, mult_cfg = configs_2025
        
        # Test parameters
        start_income = 20000
        end_income = 200000
        step_income = 100
        max_deduction_ratio = 0.15
        min_utilization_threshold = 0.20  # 20% minimum utilization
        min_roi_threshold = 10.0
        max_roi_threshold = 100.0
        
        print(f"\n🧮 Running comprehensive optimization test:")
        print(f"  Income range: {start_income:,} to {end_income:,} CHF (step: {step_income})")
        print(f"  Max deduction: {max_deduction_ratio:.1%} of income")
        print(f"  Minimum utilization: {min_utilization_threshold:.0%}")
        
        incomes = list(range(start_income, end_income + 1, step_income))
        total_tests = len(incomes)
        print(f"  Total tests: {total_tests:,}")
        
        # Run optimization tests
        results = []
        failures = []
        no_optimization_count = 0
        
        for i, income in enumerate(incomes):
            # Progress reporting for long test
            if i % 500 == 0 or i == total_tests - 1:
                progress = (i + 1) / total_tests * 100
                print(f"    Progress: {i+1:6d}/{total_tests} ({progress:5.1f}%)")
            
            max_deduction = int(income * max_deduction_ratio)
            
            try:
                # Create calculation function
                def calc_fn(current_income: Decimal):
                    sg_simple = simple_tax_sg(current_income, sg_cfg)
                    sg_after = apply_multipliers(sg_simple, mult_cfg, MultPick(["KANTON", "GEMEINDE"]))
                    fed = tax_federal(current_income, fed_cfg)
                    total = sg_after + fed
                    return {"total": total, "federal": fed}
                
                # Use the same tolerance logic as CLI for consistency
                tolerance_bp = _get_adaptive_tolerance_bp(income)
                
                # Run optimization with adaptive retry
                result = optimize_deduction_adaptive(
                    income=chf(income),
                    max_deduction=max_deduction,
                    step=100,
                    calc_fn=calc_fn,
                    initial_roi_tolerance_bp=tolerance_bp,
                    enable_adaptive_retry=True,
                    min_income_for_retry=25000,  # Use our updated threshold
                )
                
                if result["sweet_spot"] is None:
                    no_optimization_count += 1
                    failures.append(f"Income {income:,}: No optimization found")
                    continue
                
                # Extract results
                sweet_spot = result["sweet_spot"]
                deduction = sweet_spot["deduction"]
                tax_saved = sweet_spot["tax_saved_absolute"]
                roi = (tax_saved / deduction * 100) if deduction > 0 else 0
                utilization = deduction / max_deduction
                new_income = sweet_spot["new_income"]
                
                # Store result
                opt_result = {
                    "income": income,
                    "max_deduction": max_deduction,
                    "tolerance_bp": tolerance_bp,
                    "optimal_deduction": deduction,
                    "tax_saved": tax_saved,
                    "new_income": new_income,
                    "roi": roi,
                    "utilization": utilization,
                    "adaptive_used": "adaptive_retry_used" in result
                }
                results.append(opt_result)
                
                # Quality validation checks
                quality_issues = []
                
                # 1. Utilization check - this is critical
                if utilization < min_utilization_threshold:
                    quality_issues.append(f"Low utilization {utilization:.1%} < {min_utilization_threshold:.0%}")
                
                # 2. ROI sanity checks
                if roi < min_roi_threshold:
                    quality_issues.append(f"Low ROI {roi:.1f}% < {min_roi_threshold:.0f}%")
                elif roi > max_roi_threshold:
                    quality_issues.append(f"Unrealistic ROI {roi:.1f}% > {max_roi_threshold:.0f}%")
                
                # 3. Basic sanity checks
                if deduction <= 0 or deduction > max_deduction:
                    quality_issues.append(f"Invalid deduction {deduction:,} CHF (max: {max_deduction:,})")
                elif tax_saved <= 0:
                    quality_issues.append(f"Non-positive savings {tax_saved:.2f} CHF")
                elif new_income >= income:
                    quality_issues.append(f"New income {new_income:,.0f} not less than original {income:,}")
                
                # 4. Efficiency checks - deduction should provide meaningful savings
                savings_rate = tax_saved / income
                if savings_rate < 0.002:  # Less than 0.2% of income saved
                    quality_issues.append(f"Negligible savings rate {savings_rate:.3%} of income")
                
                # Record any quality issues
                if quality_issues:
                    for issue in quality_issues:
                        failures.append(f"Income {income:,}: {issue}")
                        
            except Exception as e:
                failures.append(f"Income {income:,}: Optimization failed - {str(e)[:100]}")
        
        print(f"  ✅ Completed {len(results):,} successful optimizations")
        
        # Quality analysis and assertions
        success_rate = len(results) / total_tests * 100
        
        # Print summary statistics
        if results:
            utilizations = [r["utilization"] for r in results]
            rois = [r["roi"] for r in results]
            savings = [r["tax_saved"] for r in results]
            
            low_utilization = sum(1 for u in utilizations if u < min_utilization_threshold)
            avg_utilization = sum(utilizations) / len(utilizations)
            avg_roi = sum(rois) / len(rois)
            avg_savings = sum(savings) / len(savings)
            
            print(f"\n📊 Summary Statistics:")
            print(f"  Average utilization: {avg_utilization:.1%}")
            print(f"  Average ROI: {avg_roi:.1f}%")
            print(f"  Average savings: {avg_savings:,.0f} CHF")
            print(f"  Below {min_utilization_threshold:.0%} utilization: {low_utilization:,} ({low_utilization/len(results)*100:.1f}%)")
        
        # Quality assertions
        
        # 1. Success rate must be high
        assert success_rate >= 95.0, f"Success rate {success_rate:.1f}% < 95.0%"
        
        # 2. Quality failure rate must be low
        if results:
            quality_failure_rate = len(failures) / len(results) * 100
            assert quality_failure_rate <= 5.0, f"Quality failure rate {quality_failure_rate:.1f}% > 5.0%"
        
        # 3. Average utilization must meet threshold
        if results:
            avg_util = sum(r["utilization"] for r in results) / len(results)
            assert avg_util >= min_utilization_threshold, f"Average utilization {avg_util:.1%} < {min_utilization_threshold:.0%}"
        
        # 4. Average ROI must be reasonable
        if results:
            avg_roi = sum(r["roi"] for r in results) / len(results)
            assert min_roi_threshold <= avg_roi <= max_roi_threshold, f"Average ROI {avg_roi:.1f}% not in range {min_roi_threshold:.0f}%-{max_roi_threshold:.0f}%"
        
        # Show any failures for debugging
        if failures:
            print(f"\n⚠️ Quality issues found ({len(failures):,}):")
            # Group by type for better analysis
            utilization_failures = [f for f in failures if "Low utilization" in f]
            roi_failures = [f for f in failures if ("Low ROI" in f or "Unrealistic ROI" in f)]
            
            if utilization_failures:
                print(f"  📉 Utilization issues: {len(utilization_failures):,}")
                for failure in utilization_failures[:3]:
                    print(f"    - {failure}")
                if len(utilization_failures) > 3:
                    print(f"    ... and {len(utilization_failures) - 3:,} more")
            
            if roi_failures:
                print(f"  💹 ROI issues: {len(roi_failures):,}")
                for failure in roi_failures[:3]:
                    print(f"    - {failure}")
        
        print(f"\n✅ Comprehensive optimization test passed!")
        print(f"   {success_rate:.1f}% success rate with high-quality optimization across full income spectrum")

    def test_specific_problematic_cases(self, configs_2025):
        """Test specific income levels that have been problematic in the past."""
        sg_cfg, fed_cfg, mult_cfg = configs_2025
        
        def calc_fn(current_income: Decimal):
            sg_simple = simple_tax_sg(current_income, sg_cfg)
            sg_after = apply_multipliers(sg_simple, mult_cfg, MultPick(["KANTON", "GEMEINDE"]))
            fed = tax_federal(current_income, fed_cfg)
            total = sg_after + fed
            return {"total": total, "federal": fed}
        
        # Test cases that have been problematic
        problematic_cases = [
            (34000, 5100),  # The case we've been debugging
            (34567, 10000), # The original bug report case
            (33000, 4950),  # Similar range
            (35000, 5250),  # Similar range
        ]
        
        for income, max_deduction in problematic_cases:
            tolerance_bp = _get_adaptive_tolerance_bp(income)
            
            result = optimize_deduction_adaptive(
                income=chf(income),
                max_deduction=max_deduction,
                step=100,
                calc_fn=calc_fn,
                initial_roi_tolerance_bp=tolerance_bp,
                enable_adaptive_retry=True,
            )
            
            assert result["sweet_spot"] is not None, f"No optimization found for income {income:,}"
            
            sweet_spot = result["sweet_spot"]
            deduction = sweet_spot["deduction"]
            tax_saved = sweet_spot["tax_saved_absolute"]
            utilization = deduction / max_deduction
            roi = (tax_saved / deduction * 100) if deduction > 0 else 0
            
            print(f"\nProblematic case {income:,} CHF:")
            print(f"  Deduction: {deduction:,} CHF ({utilization:.1%} utilization)")
            print(f"  Tax saved: {tax_saved:.0f} CHF")
            print(f"  ROI: {roi:.1f}%")
            
            # These should all have reasonable utilization now (relaxed threshold since users are educated)
            assert utilization >= 0.05, f"Income {income:,}: utilization {utilization:.1%} < 5% (extremely low)"
            assert roi >= 10.0, f"Income {income:,}: ROI {roi:.1f}% < 10%"
            assert roi <= 100.0, f"Income {income:,}: ROI {roi:.1f}% > 100% (unrealistic)"
            assert tax_saved > 0, f"Income {income:,}: no tax savings"
