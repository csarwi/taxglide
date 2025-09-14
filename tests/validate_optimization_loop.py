#!/usr/bin/env python3
"""
Comprehensive optimization loop validation script for TaxGlide.

This script tests optimization functionality across many income levels in a loop,
similar to the income range validation, to ensure optimization works consistently
across the entire income spectrum.
"""

import sys
import argparse
from pathlib import Path
from decimal import Decimal

# Add project root to path so we can import modules
project_root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(project_root))

from taxglide.engine.optimize import optimize_deduction
from taxglide.engine.federal import tax_federal
from taxglide.engine.stgallen import simple_tax_sg
from taxglide.engine.multipliers import apply_multipliers, MultPick
from taxglide.engine.models import chf
from taxglide.io.loader import load_configs


def run_optimization_loop_validation(start_income=20000, end_income=150000, step_income=2000, 
                                    max_deduction_ratio=0.15, year=2025, filing_status="single"):
    """Run comprehensive optimization validation across income range."""
    
    # Load configs
    CONFIG_ROOT = project_root / "configs"
    sg_cfg, fed_cfg, mult_cfg = load_configs(CONFIG_ROOT, year)
    
    print(f"🔄 TaxGlide Comprehensive Optimization Loop Validation")
    print("=" * 70)
    print(f"Income range: {start_income:,} to {end_income:,} CHF (step: {step_income:,})")
    print(f"Max deduction: {max_deduction_ratio:.1%} of income")
    print(f"Tax year: {year}")
    print(f"Filing status: {filing_status}")
    
    incomes = list(range(start_income, end_income + 1, step_income))
    total_tests = len(incomes)
    print(f"Total optimization tests: {total_tests}")
    print()
    
    # Run optimization loop
    results = []
    failures = []
    no_optimization_count = 0
    
    print("🧮 Running optimization calculations...")
    for i, income in enumerate(incomes):
        if i % 15 == 0 or i == total_tests - 1:
            progress = (i + 1) / total_tests * 100
            print(f"  Progress: {i+1:3d}/{total_tests} ({progress:5.1f}%) - Income: {income:,} CHF")
        
        max_deduction = int(income * max_deduction_ratio)
        
        try:
            # Create calculation function
            def calc_fn(current_income: Decimal):
                sg_simple = simple_tax_sg(current_income, sg_cfg)
                sg_after = apply_multipliers(sg_simple, mult_cfg, MultPick(["KANTON", "GEMEINDE"]))
                fed = tax_federal(current_income, fed_cfg)
                total = sg_after + fed
                return {"total": total, "federal": fed}
            
            # Run optimization
            result = optimize_deduction(
                income=chf(income),
                max_deduction=max_deduction,
                step=200,  # Reasonable step for loop performance
                calc_fn=calc_fn,
                roi_tolerance_bp=25.0  # Moderate tolerance for comprehensive testing
            )
            
            if result["sweet_spot"] is None:
                no_optimization_count += 1
                continue
            
            # Extract results
            sweet_spot = result["sweet_spot"]
            deduction = sweet_spot["deduction"]
            tax_saved = sweet_spot["tax_saved_absolute"]
            new_income = sweet_spot["new_income"]
            roi = (tax_saved / deduction * 100) if deduction > 0 else 0
            
            # Store result
            opt_result = {
                "income": income,
                "max_deduction": max_deduction,
                "optimal_deduction": deduction,
                "tax_saved": tax_saved,
                "new_income": new_income,
                "roi": roi,
                "deduction_ratio": deduction / income,
                "savings_ratio": tax_saved / income
            }
            results.append(opt_result)
            
            # Basic validation checks
            if deduction <= 0 or deduction > max_deduction:
                failures.append(f"Income {income:,}: Invalid deduction {deduction}")
            elif new_income >= income:
                failures.append(f"Income {income:,}: New income {new_income} not less than original")
            elif tax_saved <= 0:
                failures.append(f"Income {income:,}: Non-positive savings {tax_saved:.2f}")
            elif roi <= 0:
                failures.append(f"Income {income:,}: Non-positive ROI {roi:.1f}%")
            elif roi > 500:  # Extremely high ROI check
                failures.append(f"Income {income:,}: Unrealistic ROI {roi:.1f}%")
            
            # Deduction reasonableness checks
            utilization_ratio = deduction / max_deduction
            income_ratio = deduction / income
            
            # Check for unreasonably small deductions
            if deduction < 200 and income >= 30000:  # Less than 200 CHF for incomes above 30K
                failures.append(f"Income {income:,}: Very small deduction {deduction} CHF (likely suboptimal)")
            elif utilization_ratio < 0.02 and income >= 50000:  # Less than 2% of max deduction for higher incomes
                failures.append(f"Income {income:,}: Tiny deduction utilization {utilization_ratio:.1%} ({deduction}/{max_deduction})")
            elif income_ratio < 0.005 and income >= 60000:  # Less than 0.5% of income for higher incomes
                failures.append(f"Income {income:,}: Negligible deduction {income_ratio:.2%} of income ({deduction}/{income})")
            
            # Check for unreasonably large deductions (unlikely but possible)
            elif utilization_ratio > 0.95 and roi < 10:  # Using >95% of max but low ROI
                failures.append(f"Income {income:,}: High deduction use ({utilization_ratio:.1%}) but low ROI ({roi:.1f}%)")
            
        except Exception as e:
            failures.append(f"Income {income:,}: Optimization failed - {str(e)[:80]}")
    
    print(f"✅ Completed {len(results)} successful optimizations")
    print()
    
    # Analysis
    print("📊 COMPREHENSIVE OPTIMIZATION ANALYSIS")
    print("=" * 70)
    
    if failures:
        print(f"❌ Found {len(failures)} optimization issues:")
        for failure in failures[:10]:  # Show first 10
            print(f"  - {failure}")
        if len(failures) > 10:
            print(f"  ... and {len(failures) - 10} more")
        return False
    
    success_rate = len(results) / total_tests * 100
    testable_incomes = total_tests - no_optimization_count
    optimization_rate = len(results) / testable_incomes * 100 if testable_incomes > 0 else 0
    
    print(f"Success Metrics:")
    print(f"  Overall success rate: {success_rate:.1f}% ({len(results)}/{total_tests} incomes)")
    print(f"  Optimization rate: {optimization_rate:.1f}% (of testable incomes)")
    print(f"  No optimization found: {no_optimization_count} incomes")
    print()
    
    if results:
        # Statistical analysis
        rois = [r["roi"] for r in results]
        deductions = [r["optimal_deduction"] for r in results]
        savings = [r["tax_saved"] for r in results]
        deduction_ratios = [r["deduction_ratio"] for r in results]
        savings_ratios = [r["savings_ratio"] for r in results]
        
        print("📈 OPTIMIZATION STATISTICS")
        print("-" * 50)
        
        print(f"ROI Analysis:")
        print(f"  Average ROI: {sum(rois) / len(rois):6.1f}%")
        print(f"  Median ROI:  {sorted(rois)[len(rois)//2]:6.1f}%")
        print(f"  ROI range:   {min(rois):6.1f}% - {max(rois):6.1f}%")
        print()
        
        print(f"Deduction Analysis:")
        print(f"  Average deduction: {sum(deductions) / len(deductions):8,.0f} CHF")
        print(f"  Deduction range:   {min(deductions):8,} - {max(deductions):8,} CHF")
        print(f"  Avg % of income:   {sum(deduction_ratios) / len(deduction_ratios):8.1%}")
        
        # Calculate utilization ratios (how much of max deduction is used)
        utilization_ratios = [r["optimal_deduction"] / r["max_deduction"] for r in results]
        avg_utilization = sum(utilization_ratios) / len(utilization_ratios)
        print(f"  Avg utilization:   {avg_utilization:8.1%} (of max deduction available)")
        
        # Deduction size distribution
        very_small_deductions = sum(1 for r in results if r["optimal_deduction"] < 500)
        small_deductions = sum(1 for r in results if 500 <= r["optimal_deduction"] < 2000)
        medium_deductions = sum(1 for r in results if 2000 <= r["optimal_deduction"] < 10000)
        large_deductions = sum(1 for r in results if r["optimal_deduction"] >= 10000)
        
        print(f"\n  Deduction Distribution:")
        print(f"    Very small (<500):   {very_small_deductions:3d} ({very_small_deductions/len(results)*100:.1f}%)")
        print(f"    Small (500-2K):      {small_deductions:3d} ({small_deductions/len(results)*100:.1f}%)")
        print(f"    Medium (2K-10K):     {medium_deductions:3d} ({medium_deductions/len(results)*100:.1f}%)")
        print(f"    Large (≥10K):        {large_deductions:3d} ({large_deductions/len(results)*100:.1f}%)")
        print()
        
        print(f"Savings Analysis:")
        print(f"  Average savings:   {sum(savings) / len(savings):8,.0f} CHF")
        print(f"  Savings range:     {min(savings):8,.0f} - {max(savings):8,.0f} CHF")
        print(f"  Avg % of income:   {sum(savings_ratios) / len(savings_ratios):8.2%}")
        print()
        
        # Income segment analysis
        segments = [
            ("Low income (≤40K)", [r for r in results if r["income"] <= 40000]),
            ("Mid income (40K-80K)", [r for r in results if 40000 < r["income"] <= 80000]),
            ("High income (80K-120K)", [r for r in results if 80000 < r["income"] <= 120000]),
            ("Very high (>120K)", [r for r in results if r["income"] > 120000])
        ]
        
        print("🔍 INCOME SEGMENT ANALYSIS")
        print("-" * 50)
        print(f"{'Segment':20} | {'Count':5} | {'Avg ROI':8} | {'Avg Deduct':11} | {'Avg Savings':11}")
        print("-" * 70)
        
        for segment_name, segment_results in segments:
            if segment_results:
                count = len(segment_results)
                avg_roi = sum(r["roi"] for r in segment_results) / count
                avg_deduction = sum(r["optimal_deduction"] for r in segment_results) / count
                avg_savings = sum(r["tax_saved"] for r in segment_results) / count
                
                print(f"{segment_name:20} | {count:5d} | {avg_roi:6.1f}% | {avg_deduction:8,.0f} | {avg_savings:8,.0f}")
        
        print()
        
        # Sample results table
        print("📋 SAMPLE OPTIMIZATION RESULTS")
        print("-" * 80)
        print(f"{'Income':>8} | {'Max Deduct':>10} | {'Optimal':>8} | {'Savings':>8} | {'ROI':>6} | {'New Income':>10}")
        print("-" * 80)
        
        # Show every Nth result for representative sample
        sample_step = max(1, len(results) // 15)  # Show ~15 samples
        for i in range(0, len(results), sample_step):
            r = results[i]
            print(f"{r['income']:8,} | {r['max_deduction']:10,} | {r['optimal_deduction']:8,} | "
                  f"{r['tax_saved']:8,.0f} | {r['roi']:5.1f}% | {r['new_income']:10,.0f}")
        
        print()
        
        # Sequential comparison analysis (income N vs income N-1)
        print("📈 SEQUENTIAL INCOME COMPARISON")
        print("-" * 40)
        
        large_roi_jumps = []
        roi_regressions = []
        
        # Sort results by income for sequential analysis
        sorted_results = sorted(results, key=lambda x: x["income"])
        
        for i in range(1, len(sorted_results)):
            prev_result = sorted_results[i-1]
            curr_result = sorted_results[i]
            
            prev_roi = prev_result["roi"]
            curr_roi = curr_result["roi"]
            roi_change = curr_roi - prev_roi
            
            # Check for large ROI jumps (could indicate bracket effects)
            if abs(roi_change) > 15:  # More than 15% ROI change
                large_roi_jumps.append({
                    "from_income": prev_result["income"],
                    "to_income": curr_result["income"],
                    "from_roi": prev_roi,
                    "to_roi": curr_roi,
                    "change": roi_change
                })
            
            # Check for ROI regressions (higher income, lower ROI - could be normal)
            if curr_roi < prev_roi - 5:  # More than 5% ROI decrease
                roi_regressions.append({
                    "from_income": prev_result["income"],
                    "to_income": curr_result["income"],
                    "from_roi": prev_roi,
                    "to_roi": curr_roi,
                    "regression": prev_roi - curr_roi
                })
        
        print(f"Large ROI jumps (>15%): {len(large_roi_jumps)} cases")
        if large_roi_jumps:
            for jump in large_roi_jumps[:3]:  # Show first 3
                direction = "↗" if jump["change"] > 0 else "↘"
                print(f"  {jump['from_income']:,} → {jump['to_income']:,} CHF: "
                      f"{jump['from_roi']:.1f}% → {jump['to_roi']:.1f}% ({direction}{abs(jump['change']):.1f}%)")
            if len(large_roi_jumps) > 3:
                print(f"  ... and {len(large_roi_jumps) - 3} more")
        
        print(f"\nROI regressions (>5%): {len(roi_regressions)} cases")
        if roi_regressions:
            for regression in roi_regressions[:3]:  # Show first 3
                print(f"  {regression['from_income']:,} → {regression['to_income']:,} CHF: "
                      f"{regression['from_roi']:.1f}% → {regression['to_roi']:.1f}% (↘{regression['regression']:.1f}%)")
            if len(roi_regressions) > 3:
                print(f"  ... and {len(roi_regressions) - 3} more")
        
        # Analysis
        if len(large_roi_jumps) > len(sorted_results) * 0.15:  # More than 15% have large jumps
            print("\n⚠️ Many large ROI jumps - could indicate bracket boundary effects or optimization instability")
        else:
            print("\n✅ ROI progression between consecutive incomes looks stable")
        
        if len(roi_regressions) > len(sorted_results) * 0.30:  # More than 30% have regressions
            print("⚠️ Many ROI regressions - optimization may not be finding consistent opportunities")
        else:
            print("✅ ROI regressions within normal bounds (bracket effects can cause this)")
        
        print()
        
        # Deduction reasonableness validation
        print("💰 DEDUCTION REASONABLENESS VALIDATION")
        print("-" * 50)
        
        # Check for patterns that might indicate suboptimal deductions
        utilization_ratios = [r["optimal_deduction"] / r["max_deduction"] for r in results]
        income_ratios = [r["optimal_deduction"] / r["income"] for r in results]
        
        # Count concerning patterns
        very_low_utilization = sum(1 for r in utilization_ratios if r < 0.05)  # Less than 5% of max
        very_low_income_ratio = sum(1 for r in income_ratios if r < 0.01)      # Less than 1% of income
        tiny_absolute_amounts = sum(1 for r in results if r["optimal_deduction"] < 300 and r["income"] >= 50000)
        
        print(f"Potentially suboptimal deduction patterns:")
        print(f"  Very low utilization (<5% of max):     {very_low_utilization:3d} cases ({very_low_utilization/len(results)*100:.1f}%)")
        print(f"  Very low income ratio (<1% of income): {very_low_income_ratio:3d} cases ({very_low_income_ratio/len(results)*100:.1f}%)")
        print(f"  Tiny amounts for high income:          {tiny_absolute_amounts:3d} cases ({tiny_absolute_amounts/len(results)*100:.1f}%)")
        
        # Analyze deduction scaling with income
        low_income_deductions = [r["optimal_deduction"] for r in results if r["income"] <= 40000]
        high_income_deductions = [r["optimal_deduction"] for r in results if r["income"] >= 100000]
        
        if low_income_deductions and high_income_deductions:
            low_avg_deduction = sum(low_income_deductions) / len(low_income_deductions)
            high_avg_deduction = sum(high_income_deductions) / len(high_income_deductions)
            scaling_ratio = high_avg_deduction / low_avg_deduction if low_avg_deduction > 0 else 0
            
            print(f"\nDeduction scaling analysis:")
            print(f"  Low income avg deduction:  {low_avg_deduction:6,.0f} CHF")
            print(f"  High income avg deduction: {high_avg_deduction:6,.0f} CHF")
            print(f"  Scaling ratio:             {scaling_ratio:6.1f}x")
            
            if scaling_ratio < 1.5:
                print("  ⚠️ Deductions scale poorly with income - may indicate optimization issues")
            elif scaling_ratio > 8:
                print("  ⚠️ Deductions scale very aggressively - may indicate bracket artifacts")
            else:
                print("  ✅ Deduction scaling looks reasonable")
        
        # Overall deduction reasonableness assessment
        concerning_cases = very_low_utilization + very_low_income_ratio + tiny_absolute_amounts
        concerning_rate = concerning_cases / (len(results) * 3) * 100  # 3 types of checks
        
        if concerning_rate > 15:  # More than 15% of checks show concerning patterns
            print(f"\n⚠️ Many potentially suboptimal deductions ({concerning_rate:.1f}% concerning patterns)")
            print("   Optimization may be too conservative or missing opportunities")
        elif concerning_rate > 5:
            print(f"\nℹ️ Some potentially suboptimal deductions ({concerning_rate:.1f}% concerning patterns)")
            print("   Generally reasonable, but some improvements possible")
        else:
            print(f"\n✅ Deduction amounts appear reasonable ({concerning_rate:.1f}% concerning patterns)")
            print("   Good balance between utilization and optimization")
        
        print()
        
        # Original reasonableness checks
        print("🔍 GENERAL REASONABLENESS VALIDATION")
        print("-" * 40)
        
        # ROI distribution check
        high_roi_count = sum(1 for roi in rois if roi > 50)
        very_high_roi_count = sum(1 for roi in rois if roi > 100)
        
        print(f"ROI Distribution:")
        print(f"  ROI > 50%:  {high_roi_count:3d} cases ({high_roi_count/len(rois)*100:.1f}%)")
        print(f"  ROI > 100%: {very_high_roi_count:3d} cases ({very_high_roi_count/len(rois)*100:.1f}%)")
        
        if very_high_roi_count > len(results) * 0.10:  # More than 10% very high ROI
            print("  ⚠️ Many very high ROI cases - possible bracket boundary optimizations")
        else:
            print("  ✅ ROI distribution looks reasonable")
        
        # Deduction size distribution
        small_deduction_count = sum(1 for r in results if r["deduction_ratio"] < 0.02)  # Less than 2% of income
        large_deduction_count = sum(1 for r in results if r["deduction_ratio"] > 0.12)  # More than 12% of income
        
        print(f"\nDeduction Distribution:")
        print(f"  Very small (<2%): {small_deduction_count:3d} cases ({small_deduction_count/len(results)*100:.1f}%)")
        print(f"  Large (>12%):     {large_deduction_count:3d} cases ({large_deduction_count/len(results)*100:.1f}%)")
        
        if small_deduction_count > len(results) * 0.20:  # More than 20% very small
            print("  ⚠️ Many very small deductions - optimization may be conservative")
        else:
            print("  ✅ Deduction size distribution looks reasonable")
    
    print("\n🎯 FINAL ASSESSMENT")
    print("-" * 30)
    
    # Success criteria
    min_success_rate = 75.0  # At least 75% should have successful optimization
    min_optimization_count = total_tests * 0.50  # At least 50% of all incomes
    
    passed_checks = []
    failed_checks = []
    
    # Check 1: No failures
    if len(failures) == 0:
        passed_checks.append("No optimization failures")
    else:
        failed_checks.append(f"{len(failures)} optimization failures")
    
    # Check 2: Success rate
    if success_rate >= min_success_rate:
        passed_checks.append(f"Success rate {success_rate:.1f}% ≥ {min_success_rate:.1f}%")
    else:
        failed_checks.append(f"Success rate {success_rate:.1f}% < {min_success_rate:.1f}%")
    
    # Check 3: Total optimizations
    if len(results) >= min_optimization_count:
        passed_checks.append(f"Found {len(results)} optimizations ≥ {min_optimization_count:.0f}")
    else:
        failed_checks.append(f"Only {len(results)} optimizations < {min_optimization_count:.0f}")
    
    # Check 4: Reasonable average ROI
    if results:
        avg_roi = sum(rois) / len(rois)
        if 10 <= avg_roi <= 100:  # Between 10% and 100% average ROI
            passed_checks.append(f"Reasonable average ROI {avg_roi:.1f}%")
        else:
            failed_checks.append(f"Unusual average ROI {avg_roi:.1f}%")
    
    print("✅ Passed checks:")
    for check in passed_checks:
        print(f"  - {check}")
    
    if failed_checks:
        print("\n❌ Failed checks:")
        for check in failed_checks:
            print(f"  - {check}")
    
    all_passed = len(failed_checks) == 0
    assessment = "EXCELLENT" if all_passed and success_rate >= 90 else \
                "GOOD" if all_passed else \
                "NEEDS REVIEW" if len(failed_checks) <= 2 else \
                "POOR"
    
    print(f"\n💡 Overall Assessment: {assessment}")
    
    if all_passed:
        print("   Optimization system works consistently across the income range!")
        if results:
            avg_roi = sum(rois) / len(rois)
            avg_savings = sum(savings) / len(savings)
            print(f"   Average {avg_roi:.1f}% ROI, {avg_savings:,.0f} CHF savings per optimization.")
    else:
        print("   Some optimization issues detected - review details above.")
    
    return all_passed


def main():
    parser = argparse.ArgumentParser(description="Comprehensive optimization loop validation for TaxGlide")
    parser.add_argument("--start", type=int, default=20000, 
                       help="Starting income in CHF (default: 20,000)")
    parser.add_argument("--end", type=int, default=150000,
                       help="Ending income in CHF (default: 150,000)")
    parser.add_argument("--step", type=int, default=2000,
                       help="Income step size in CHF (default: 2,000)")
    parser.add_argument("--max-deduction-ratio", type=float, default=0.15,
                       help="Max deduction as ratio of income (default: 0.15)")
    parser.add_argument("--year", type=int, default=2025, help="Tax year (default: 2025)")
    parser.add_argument("--filing-status", choices=["single", "married_joint"], 
                       default="single", help="Filing status (default: single)")
    
    args = parser.parse_args()
    
    # Validation
    if args.start >= args.end:
        print("❌ Error: Start income must be less than end income")
        sys.exit(1)
    
    if args.step <= 0:
        print("❌ Error: Step size must be positive")
        sys.exit(1)
    
    if not (0.01 <= args.max_deduction_ratio <= 0.50):
        print("❌ Error: Max deduction ratio must be between 1% and 50%")
        sys.exit(1)
    
    total_tests = (args.end - args.start) // args.step + 1
    if total_tests > 200:
        print(f"❌ Error: Too many tests ({total_tests}). Use larger step size.")
        sys.exit(1)
    
    try:
        success = run_optimization_loop_validation(
            start_income=args.start,
            end_income=args.end,
            step_income=args.step,
            max_deduction_ratio=args.max_deduction_ratio,
            year=args.year,
            filing_status=args.filing_status
        )
        
        sys.exit(0 if success else 1)
        
    except KeyboardInterrupt:
        print("\n🛑 Validation interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Validation failed with error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
