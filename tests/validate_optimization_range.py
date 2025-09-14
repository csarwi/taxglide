#!/usr/bin/env python3
"""
Optimization range validation script for TaxGlide.

This script tests optimization functionality across different income levels 
to ensure deduction suggestions are reasonable and provide good ROI.
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


def test_optimization_scenarios(year=2025, filing_status="single", verbose=False):
    """Test optimization across various income scenarios."""
    
    # Load configs
    CONFIG_ROOT = project_root / "configs"
    sg_cfg, fed_cfg, mult_cfg = load_configs(CONFIG_ROOT, year)
    
    # Define test scenarios: (income, max_deduction, description, expected_min_roi)
    scenarios = [
        (25000, 2500, "Lower income", 5.0),     # At least 5% ROI expected
        (40000, 6000, "Mid-lower income", 8.0),  # At least 8% ROI expected
        (60000, 8000, "Mid income", 10.0),      # At least 10% ROI expected
        (80000, 12000, "Higher income", 12.0),  # At least 12% ROI expected
        (100000, 15000, "High income", 15.0),   # At least 15% ROI expected
        (150000, 20000, "Very high income", 10.0), # May have lower ROI due to flatter curves
        (200000, 25000, "Ultra high income", 8.0),  # Even lower ROI expected
    ]
    
    print(f"🔍 TaxGlide Optimization Range Validation")
    print("=" * 60)
    print(f"Tax year: {year}")
    print(f"Filing status: {filing_status}")
    print(f"Test scenarios: {len(scenarios)}")
    print()
    
    results = []
    failures = []
    
    for income, max_deduction, description, expected_min_roi in scenarios:
        print(f"🧮 Testing {description} ({income:,} CHF, max deduction {max_deduction:,})...")
        
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
                step=100,
                calc_fn=calc_fn,
                roi_tolerance_bp=10.0
            )
            
            if result["sweet_spot"] is None:
                failures.append(f"{description}: No optimization found")
                print(f"  ❌ No optimization found")
                continue
            
            # Extract results
            sweet_spot = result["sweet_spot"]
            deduction = sweet_spot["deduction"]
            tax_saved = sweet_spot["tax_saved_absolute"]
            new_income = sweet_spot["new_income"]
            roi = (tax_saved / deduction * 100) if deduction > 0 else 0
            
            # Store results
            scenario_result = {
                "description": description,
                "income": income,
                "max_deduction": max_deduction,
                "optimal_deduction": deduction,
                "tax_saved": tax_saved,
                "new_income": new_income,
                "roi": roi,
                "expected_min_roi": expected_min_roi
            }
            results.append(scenario_result)
            
            # Validation checks
            issues = []
            
            # Basic bounds check
            if not (0 < deduction <= max_deduction):
                issues.append(f"Deduction {deduction} outside bounds (0, {max_deduction}]")
            
            # Income reduction check
            if new_income >= income:
                issues.append(f"New income {new_income} not less than original {income}")
            
            # Positive savings check
            if tax_saved <= 0:
                issues.append(f"Non-positive tax savings: {tax_saved:.2f}")
            
            # ROI reasonableness check
            if roi <= 0:
                issues.append(f"Non-positive ROI: {roi:.1f}%")
            elif roi > 300:  # Very high but possible in Swiss system
                issues.append(f"Extremely high ROI: {roi:.1f}% (possible bracket optimization)")
            
            # Expected minimum ROI check
            if roi < expected_min_roi:
                issues.append(f"ROI {roi:.1f}% below expected minimum {expected_min_roi:.1f}%")
            
            # Deduction reasonableness checks
            utilization_ratio = deduction / max_deduction
            income_ratio = deduction / income
            
            # Check for unreasonably small deductions relative to available space
            if utilization_ratio < 0.02:  # Less than 2% of max
                issues.append(f"Very small utilization {utilization_ratio:.1%} of max deduction ({deduction}/{max_deduction})")
            
            # Check for unreasonably small deductions relative to income
            if income_ratio < 0.005 and income >= 60000:  # Less than 0.5% of income for higher incomes
                issues.append(f"Negligible deduction {income_ratio:.2%} of income ({deduction}/{income})")
            
            # Check for tiny absolute amounts on higher incomes
            if deduction < 300 and income >= 50000:
                issues.append(f"Tiny absolute deduction {deduction} CHF for income {income:,} CHF")
            
            # Check for suspiciously precise small amounts (might indicate optimization artifacts)
            if deduction < 1000 and deduction % 100 == 0 and income >= 40000:
                issues.append(f"Suspiciously round small deduction {deduction} CHF (possible optimization artifact)")
            
            if issues:
                failures.extend([f"{description}: {issue}" for issue in issues])
                print(f"  ⚠️ Issues found: {len(issues)}")
                if verbose:
                    for issue in issues:
                        print(f"    - {issue}")
            else:
                status_icon = "🎯" if roi >= expected_min_roi * 1.5 else "✅"
                print(f"  {status_icon} Optimal deduction: {deduction:,} CHF")
                print(f"      Tax savings: {tax_saved:,.0f} CHF ({tax_saved/income*100:.2f}% of income)")
                print(f"      ROI: {roi:.1f}% (expected ≥{expected_min_roi:.1f}%)")
                print(f"      New income: {new_income:,.0f} CHF")
            
        except Exception as e:
            failures.append(f"{description}: Optimization failed - {e}")
            print(f"  ❌ Error: {e}")
        
        print()
    
    # Summary analysis
    print("📊 OPTIMIZATION ANALYSIS SUMMARY")
    print("=" * 60)
    
    if failures:
        print(f"❌ Found {len(failures)} issues:")
        for failure in failures[:10]:  # Show first 10
            print(f"  - {failure}")
        if len(failures) > 10:
            print(f"  ... and {len(failures) - 10} more")
        print()
    
    if results:
        print(f"✅ Successful optimizations: {len(results)}/{len(scenarios)}")
        print()
        
        print("📈 OPTIMIZATION RESULTS TABLE")
        print("-" * 90)
        print(f"{'Description':20} | {'Income':>8} | {'Deduction':>9} | {'Savings':>8} | {'ROI':>6} | {'Status':>8}")
        print("-" * 90)
        
        for r in results:
            status = "GOOD" if r["roi"] >= r["expected_min_roi"] else "LOW"
            if r["roi"] >= r["expected_min_roi"] * 1.5:
                status = "EXCELLENT"
            
            print(f"{r['description']:20} | {r['income']:8,} | {r['optimal_deduction']:9,} | "
                  f"{r['tax_saved']:8,.0f} | {r['roi']:5.1f}% | {status:>8}")
        
        print("-" * 90)
        
        # Statistical analysis
        avg_roi = sum(r["roi"] for r in results) / len(results)
        min_roi = min(r["roi"] for r in results)
        max_roi = max(r["roi"] for r in results)
        
        print(f"\n📊 ROI Statistics:")
        print(f"  Average ROI: {avg_roi:.1f}%")
        print(f"  ROI Range: {min_roi:.1f}% - {max_roi:.1f}%")
        
        # Check for reasonable progression
        low_income_roi = [r["roi"] for r in results if r["income"] <= 50000]
        high_income_roi = [r["roi"] for r in results if r["income"] >= 100000]
        
        if low_income_roi and high_income_roi:
            low_avg = sum(low_income_roi) / len(low_income_roi)
            high_avg = sum(high_income_roi) / len(high_income_roi)
            print(f"  Low income avg ROI: {low_avg:.1f}%")
            print(f"  High income avg ROI: {high_avg:.1f}%")
            
            if high_avg > low_avg * 1.5:
                print("  ⚠️ High-income ROI significantly higher than low-income (unusual)")
            elif low_avg > high_avg * 1.2:
                print("  ✅ Typical pattern: Lower incomes have higher ROI potential")
            else:
                print("  ✅ ROI progression looks reasonable")
    
    print("\n🎯 FINAL ASSESSMENT")
    print("-" * 30)
    
    success_rate = len(results) / len(scenarios) * 100
    issue_rate = len(failures) / len(scenarios) * 100
    
    if len(failures) == 0:
        assessment = "EXCELLENT"
        print("✅ All optimization scenarios passed validation!")
        print("   Deduction suggestions are reasonable across all income levels.")
    elif success_rate >= 80:
        assessment = "GOOD"
        print(f"✅ Most scenarios passed ({success_rate:.0f}% success rate)")
        print(f"⚠️ {len(failures)} issues found - review specific scenarios above")
    elif success_rate >= 60:
        assessment = "NEEDS REVIEW"
        print(f"⚠️ Moderate success rate ({success_rate:.0f}%)")
        print(f"❌ {len(failures)} issues found - optimization may need adjustments")
    else:
        assessment = "POOR"
        print(f"❌ Low success rate ({success_rate:.0f}%)")
        print("   Optimization system needs investigation")
    
    print(f"\n💡 Recommendation: {assessment}")
    
    return len(failures) == 0


def main():
    parser = argparse.ArgumentParser(description="Validate TaxGlide optimization across income ranges")
    parser.add_argument("--year", type=int, default=2025, help="Tax year (default: 2025)")
    parser.add_argument("--filing-status", choices=["single", "married_joint"], 
                       default="single", help="Filing status (default: single)")
    parser.add_argument("--verbose", "-v", action="store_true", help="Show detailed analysis")
    
    args = parser.parse_args()
    
    try:
        success = test_optimization_scenarios(
            year=args.year,
            filing_status=args.filing_status,
            verbose=args.verbose
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
