#!/usr/bin/env python3
"""
Comprehensive optimization validation for TaxGlide.

Tests optimization across the full income spectrum (20K-200K CHF) with 100 CHF steps
to ensure consistent, meaningful optimization results with proper utilization.
"""

import sys
import argparse
from pathlib import Path
from decimal import Decimal
from typing import List, Dict, Any

# Add project root to path so we can import modules
project_root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(project_root))

from taxglide.engine.optimize import optimize_deduction_adaptive
from taxglide.engine.federal import tax_federal
from taxglide.engine.stgallen import simple_tax_sg
from taxglide.engine.multipliers import apply_multipliers, MultPick
from taxglide.engine.models import chf
from taxglide.io.loader import load_configs
from taxglide.cli import _get_adaptive_tolerance_bp


def run_comprehensive_optimization_validation(
    start_income: int = 20000,
    end_income: int = 200000,
    step_income: int = 100,
    max_deduction_ratio: float = 0.15,
    year: int = 2025,
    filing_status: str = "single",
    min_utilization_threshold: float = 0.25,  # 25% minimum utilization
    min_roi_threshold: float = 10.0,          # 10% minimum ROI
    max_roi_threshold: float = 100.0,         # 100% maximum realistic ROI
) -> bool:
    """Run comprehensive optimization validation across full income range."""
    
    # Load configs
    CONFIG_ROOT = project_root / "configs"
    sg_cfg, fed_cfg, mult_cfg = load_configs(CONFIG_ROOT, year)
    
    print(f"🔄 TaxGlide Comprehensive Optimization Validation")
    print("=" * 80)
    print(f"Income range: {start_income:,} to {end_income:,} CHF (step: {step_income:,})")
    print(f"Max deduction: {max_deduction_ratio:.1%} of income")
    print(f"Tax year: {year}")
    print(f"Filing status: {filing_status}")
    print(f"Quality thresholds:")
    print(f"  - Minimum utilization: {min_utilization_threshold:.0%}")
    print(f"  - ROI range: {min_roi_threshold:.0f}% - {max_roi_threshold:.0f}%")
    
    incomes = list(range(start_income, end_income + 1, step_income))
    total_tests = len(incomes)
    print(f"Total tests: {total_tests:,}")
    print()
    
    # Run optimization tests
    results = []
    failures = []
    no_optimization_count = 0
    
    print("🧮 Running comprehensive optimization tests...")
    
    for i, income in enumerate(incomes):
        if i % 500 == 0 or i == total_tests - 1:
            progress = (i + 1) / total_tests * 100
            print(f"  Progress: {i+1:6d}/{total_tests} ({progress:5.1f}%) - Income: {income:,} CHF")
        
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
    
    print(f"✅ Completed {len(results):,} successful optimizations")
    print()
    
    # Analysis
    print("📊 COMPREHENSIVE OPTIMIZATION ANALYSIS")
    print("=" * 80)
    
    if failures:
        print(f"❌ Found {len(failures):,} optimization issues:")
        
        # Group failures by type for better analysis
        utilization_failures = [f for f in failures if "Low utilization" in f]
        roi_failures = [f for f in failures if ("Low ROI" in f or "Unrealistic ROI" in f)]
        other_failures = [f for f in failures if f not in utilization_failures + roi_failures]
        
        if utilization_failures:
            print(f"  📉 Utilization issues: {len(utilization_failures):,}")
            for failure in utilization_failures[:5]:  # Show first 5
                print(f"    - {failure}")
            if len(utilization_failures) > 5:
                print(f"    ... and {len(utilization_failures) - 5:,} more")
        
        if roi_failures:
            print(f"  💹 ROI issues: {len(roi_failures):,}")
            for failure in roi_failures[:5]:  # Show first 5
                print(f"    - {failure}")
            if len(roi_failures) > 5:
                print(f"    ... and {len(roi_failures) - 5:,} more")
        
        if other_failures:
            print(f"  🔧 Other issues: {len(other_failures):,}")
            for failure in other_failures[:5]:  # Show first 5
                print(f"    - {failure}")
            if len(other_failures) > 5:
                print(f"    ... and {len(other_failures) - 5:,} more")
        
        print()
    
    # Success metrics
    success_rate = len(results) / total_tests * 100
    testable_incomes = total_tests - no_optimization_count
    optimization_rate = len(results) / testable_incomes * 100 if testable_incomes > 0 else 0
    
    print(f"Success Metrics:")
    print(f"  Overall success rate: {success_rate:.1f}% ({len(results):,}/{total_tests:,} incomes)")
    print(f"  Optimization rate: {optimization_rate:.1f}% (of testable incomes)")
    print(f"  No optimization found: {no_optimization_count:,} incomes")
    print()
    
    # Quality analysis
    if results:
        utilizations = [r["utilization"] for r in results]
        rois = [r["roi"] for r in results]
        deductions = [r["optimal_deduction"] for r in results]
        savings = [r["tax_saved"] for r in results]
        
        print("📈 QUALITY STATISTICS")
        print("-" * 60)
        
        # Utilization analysis
        low_utilization = sum(1 for u in utilizations if u < min_utilization_threshold)
        avg_utilization = sum(utilizations) / len(utilizations)
        
        print(f"Utilization Analysis:")
        print(f"  Average utilization: {avg_utilization:8.1%}")
        print(f"  Median utilization:  {sorted(utilizations)[len(utilizations)//2]:8.1%}")
        print(f"  Range: {min(utilizations):6.1%} - {max(utilizations):6.1%}")
        print(f"  Below {min_utilization_threshold:.0%} threshold: {low_utilization:5,} ({low_utilization/len(results)*100:.1f}%)")
        
        # ROI analysis
        low_roi = sum(1 for r in rois if r < min_roi_threshold)
        high_roi = sum(1 for r in rois if r > max_roi_threshold)
        avg_roi = sum(rois) / len(rois)
        
        print(f"\nROI Analysis:")
        print(f"  Average ROI: {avg_roi:10.1f}%")
        print(f"  Median ROI:  {sorted(rois)[len(rois)//2]:10.1f}%")
        print(f"  Range: {min(rois):8.1f}% - {max(rois):8.1f}%")
        print(f"  Below {min_roi_threshold:.0f}% threshold: {low_roi:7,} ({low_roi/len(results)*100:.1f}%)")
        print(f"  Above {max_roi_threshold:.0f}% threshold: {high_roi:7,} ({high_roi/len(results)*100:.1f}%)")
        
        # Deduction size analysis
        avg_deduction = sum(deductions) / len(deductions)
        avg_savings = sum(savings) / len(savings)
        
        print(f"\nDeduction Analysis:")
        print(f"  Average deduction: {avg_deduction:10,.0f} CHF")
        print(f"  Average savings:   {avg_savings:10,.0f} CHF")
        print(f"  Range deductions:  {min(deductions):8,} - {max(deductions):8,} CHF")
        
        # Adaptive retry usage
        adaptive_used = sum(1 for r in results if r["adaptive_used"])
        print(f"\nAdaptive Retry Usage:")
        print(f"  Used adaptive retry: {adaptive_used:8,} cases ({adaptive_used/len(results)*100:.1f}%)")
        
        # Income segment analysis
        segments = [
            ("Low (20K-50K)", [r for r in results if 20000 <= r["income"] < 50000]),
            ("Mid (50K-100K)", [r for r in results if 50000 <= r["income"] < 100000]),
            ("High (100K-150K)", [r for r in results if 100000 <= r["income"] < 150000]),
            ("Very High (150K+)", [r for r in results if r["income"] >= 150000])
        ]
        
        print(f"\n🔍 INCOME SEGMENT ANALYSIS")
        print("-" * 80)
        print(f"{'Segment':15} | {'Count':6} | {'Avg Util':8} | {'Avg ROI':8} | {'Avg Deduct':11} | {'Qual Issues':11}")
        print("-" * 80)
        
        for segment_name, segment_results in segments:
            if segment_results:
                count = len(segment_results)
                avg_util = sum(r["utilization"] for r in segment_results) / count
                avg_roi = sum(r["roi"] for r in segment_results) / count
                avg_deduct = sum(r["optimal_deduction"] for r in segment_results) / count
                
                # Count quality issues in this segment
                segment_incomes = [r["income"] for r in segment_results]
                qual_issues = sum(1 for f in failures if any(f"Income {inc:,}:" in f for inc in segment_incomes))
                
                print(f"{segment_name:15} | {count:6,} | {avg_util:7.1%} | {avg_roi:6.1f}% | {avg_deduct:8,.0f} | {qual_issues:8,} ({qual_issues/count*100:.1f}%)")
        
        print()
    
    # Final assessment
    print("🎯 FINAL QUALITY ASSESSMENT")
    print("-" * 50)
    
    # Quality criteria
    min_success_rate = 95.0          # At least 95% should have successful optimization
    max_quality_failure_rate = 5.0   # No more than 5% quality failures
    min_avg_utilization = min_utilization_threshold  # Average should meet threshold
    
    passed_checks = []
    failed_checks = []
    
    # Check 1: Success rate
    if success_rate >= min_success_rate:
        passed_checks.append(f"Success rate {success_rate:.1f}% ≥ {min_success_rate:.1f}%")
    else:
        failed_checks.append(f"Success rate {success_rate:.1f}% < {min_success_rate:.1f}%")
    
    # Check 2: Quality failure rate
    if results:
        quality_failure_rate = len(failures) / len(results) * 100
        if quality_failure_rate <= max_quality_failure_rate:
            passed_checks.append(f"Quality failure rate {quality_failure_rate:.1f}% ≤ {max_quality_failure_rate:.1f}%")
        else:
            failed_checks.append(f"Quality failure rate {quality_failure_rate:.1f}% > {max_quality_failure_rate:.1f}%")
    
    # Check 3: Average utilization
    if results:
        avg_util = sum(r["utilization"] for r in results) / len(results)
        if avg_util >= min_avg_utilization:
            passed_checks.append(f"Average utilization {avg_util:.1%} ≥ {min_avg_utilization:.0%}")
        else:
            failed_checks.append(f"Average utilization {avg_util:.1%} < {min_avg_utilization:.0%}")
    
    # Check 4: ROI reasonableness
    if results:
        avg_roi = sum(r["roi"] for r in results) / len(results)
        if min_roi_threshold <= avg_roi <= max_roi_threshold:
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
    assessment = "EXCELLENT" if all_passed and success_rate >= 99 else \
                "GOOD" if all_passed else \
                "NEEDS IMPROVEMENT" if len(failed_checks) <= 2 else \
                "POOR"
    
    print(f"\n💡 Overall Assessment: {assessment}")
    
    if all_passed:
        print("   Optimization system provides consistent, high-quality results across all income ranges!")
        if results:
            avg_util = sum(r["utilization"] for r in results) / len(results)
            avg_roi = sum(r["roi"] for r in results) / len(results)
            avg_savings = sum(r["tax_saved"] for r in results) / len(results)
            print(f"   Average: {avg_util:.1%} utilization, {avg_roi:.1f}% ROI, {avg_savings:,.0f} CHF savings")
    else:
        print("   Optimization quality issues detected - review details above.")
    
    return all_passed


def main():
    parser = argparse.ArgumentParser(description="Comprehensive optimization validation for TaxGlide")
    parser.add_argument("--start", type=int, default=20000,
                       help="Starting income in CHF (default: 20,000)")
    parser.add_argument("--end", type=int, default=200000,
                       help="Ending income in CHF (default: 200,000)")
    parser.add_argument("--step", type=int, default=100,
                       help="Income step size in CHF (default: 100)")
    parser.add_argument("--max-deduction-ratio", type=float, default=0.15,
                       help="Max deduction as ratio of income (default: 0.15)")
    parser.add_argument("--min-utilization", type=float, default=0.25,
                       help="Minimum utilization threshold (default: 0.25)")
    parser.add_argument("--min-roi", type=float, default=10.0,
                       help="Minimum ROI threshold (default: 10.0)")
    parser.add_argument("--max-roi", type=float, default=100.0,
                       help="Maximum realistic ROI threshold (default: 100.0)")
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
    
    if not (0.05 <= args.min_utilization <= 0.95):
        print("❌ Error: Min utilization must be between 5% and 95%")
        sys.exit(1)
    
    total_tests = (args.end - args.start) // args.step + 1
    if total_tests > 50000:
        print(f"❌ Error: Too many tests ({total_tests:,}). Use larger step size.")
        sys.exit(1)
    
    print(f"⚠️ About to run {total_tests:,} optimization tests. This may take several minutes.")
    try:
        input("Press Enter to continue or Ctrl+C to cancel...")
    except KeyboardInterrupt:
        print("\n🛑 Cancelled by user")
        sys.exit(1)
    
    try:
        success = run_comprehensive_optimization_validation(
            start_income=args.start,
            end_income=args.end,
            step_income=args.step,
            max_deduction_ratio=args.max_deduction_ratio,
            year=args.year,
            filing_status=args.filing_status,
            min_utilization_threshold=args.min_utilization,
            min_roi_threshold=args.min_roi,
            max_roi_threshold=args.max_roi,
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
