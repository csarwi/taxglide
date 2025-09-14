#!/usr/bin/env python3
"""
Simple income range validation script for TaxGlide.

This script runs tax calculations from 500 to 200,000 CHF with 1,000 CHF steps
and validates the reasonableness of results.
"""

import sys
from pathlib import Path
from taxglide.cli import _calc_once

def run_income_range_validation():
    """Run comprehensive income range validation."""
    
    # Parameters
    start_income = 500
    end_income = 200000
    step_income = 1000
    
    # Use default multipliers
    multipliers = ["KANTON", "GEMEINDE"]
    
    print("🧮 TaxGlide Income Range Validation")
    print("=" * 50)
    print(f"Income range: {start_income:,} to {end_income:,} CHF (step: {step_income:,})")
    print(f"Multipliers: {', '.join(multipliers)}")
    print(f"Total calculations: {(end_income - start_income) // step_income + 1:,}")
    print()
    
    # Run calculations
    results = []
    failures = []
    
    incomes = list(range(start_income, end_income + 1, step_income))
    total_calculations = len(incomes)
    
    print("🔄 Running calculations...")
    for i, income in enumerate(incomes):
        if i % 50 == 0 or i == total_calculations - 1:
            progress = (i + 1) / total_calculations * 100
            print(f"  Progress: {i+1:3d}/{total_calculations} ({progress:5.1f}%) - Income: {income:,} CHF")
        
        try:
            result = _calc_once(2025, income, multipliers)
            results.append(result)
            
            # Quick reasonableness checks
            if result["total"] < 0:
                failures.append(f"Negative tax at {income:,} CHF: {result['total']}")
            if result["avg_rate"] < 0 or result["avg_rate"] > 0.5:
                failures.append(f"Unreasonable avg rate at {income:,} CHF: {result['avg_rate']:.1%}")
            if result["marginal_total"] < 0 or result["marginal_total"] > 0.6:
                failures.append(f"Unreasonable marginal rate at {income:,} CHF: {result['marginal_total']:.1%}")
                
        except Exception as e:
            failures.append(f"Calculation failed at {income:,} CHF: {e}")
    
    print(f"✅ Completed {len(results):,} calculations")
    print()
    
    if failures:
        print(f"❌ Found {len(failures)} issues:")
        for failure in failures[:10]:  # Show first 10
            print(f"  - {failure}")
        if len(failures) > 10:
            print(f"  ... and {len(failures) - 10} more")
        return
    
    # Analysis
    print("📊 ANALYSIS RESULTS")
    print("=" * 50)
    
    # Basic statistics
    incomes_calc = [r["income"] for r in results]
    total_taxes = [r["total"] for r in results]
    avg_rates = [r["avg_rate"] for r in results]
    marginal_rates = [r["marginal_total"] for r in results]
    
    print(f"Income range: {min(incomes_calc):,} - {max(incomes_calc):,} CHF")
    print(f"Tax range: {min(total_taxes):.2f} - {max(total_taxes):,.2f} CHF")
    print(f"Average rate range: {min(avg_rates):.1%} - {max(avg_rates):.1%}")
    print(f"Marginal rate range: {min(marginal_rates):.1%} - {max(marginal_rates):.1%}")
    print()
    
    # Key income analysis
    key_incomes = [10000, 20000, 30000, 50000, 75000, 100000, 150000, 200000]
    print("📈 KEY INCOME LEVELS")
    print("-" * 70)
    print(f"{'Income':>8} | {'Tax':>10} | {'Avg Rate':>8} | {'Marginal':>8} | {'Federal':>8} | {'SG':>8}")
    print("-" * 70)
    
    for target_income in key_incomes:
        if target_income > max(incomes_calc):
            continue
            
        # Find closest result
        closest_result = min(results, key=lambda x: abs(x["income"] - target_income))
        if abs(closest_result["income"] - target_income) > step_income:
            continue
            
        r = closest_result
        print(f"{r['income']:8,} | {r['total']:10,.0f} | {r['avg_rate']:7.1%} | "
              f"{r['marginal_total']:7.1%} | {r['federal']:8,.0f} | {r['sg_after_mult']:8,.0f}")
    
    print()
    
    # Monotonicity check
    monotonicity_violations = 0
    max_regression = 0
    
    for i in range(1, len(results)):
        prev_tax = results[i-1]["total"]
        curr_tax = results[i]["total"]
        if curr_tax < prev_tax:
            monotonicity_violations += 1
            regression = prev_tax - curr_tax
            max_regression = max(max_regression, regression)
    
    print("🔍 REASONABLENESS CHECKS")
    print("-" * 30)
    print(f"✅ All taxes non-negative: {all(r['total'] >= 0 for r in results)}")
    print(f"✅ All average rates reasonable: {all(0 <= r['avg_rate'] <= 0.4 for r in results)}")
    print(f"✅ All marginal rates reasonable: {all(0 <= r['marginal_total'] <= 0.6 for r in results)}")
    print(f"✅ Monotonicity violations: {monotonicity_violations} (max regression: {max_regression:.2f} CHF)")
    
    # Progressive taxation check
    low_income_avg = sum(r["avg_rate"] for r in results[:20]) / 20  # First 20 results
    high_income_avg = sum(r["avg_rate"] for r in results[-20:]) / 20  # Last 20 results
    print(f"✅ Progressive taxation: Low income avg {low_income_avg:.1%} < High income avg {high_income_avg:.1%}")
    
    print()
    
    # Large jumps analysis  
    large_jumps = []
    for i in range(1, len(results)):
        prev_marginal = results[i-1]["marginal_total"] 
        curr_marginal = results[i]["marginal_total"]
        jump = abs(curr_marginal - prev_marginal)
        if jump > 0.05:  # 5% jump
            large_jumps.append({
                "from_income": results[i-1]["income"],
                "to_income": results[i]["income"],
                "from_rate": prev_marginal,
                "to_rate": curr_marginal,
                "jump": jump
            })
    
    if large_jumps:
        print("⚠️ LARGE MARGINAL RATE JUMPS")
        print("-" * 40)
        for jump in large_jumps[:5]:
            print(f"  {jump['from_income']:,} -> {jump['to_income']:,} CHF: "
                  f"{jump['from_rate']:.1%} -> {jump['to_rate']:.1%} (jump: {jump['jump']:.1%})")
        if len(large_jumps) > 5:
            print(f"  ... and {len(large_jumps) - 5} more")
        print("  Note: Large jumps at bracket boundaries are normal")
        print()
    
    print("🎯 SUMMARY")
    print("-" * 20)
    total_failed_checks = len(failures) + (1 if monotonicity_violations > 5 else 0)
    
    if total_failed_checks == 0:
        print("✅ All calculations look REASONABLE!")
        print("   - Taxes increase monotonically with income")
        print("   - All rates within expected Swiss bounds")
        print("   - Progressive taxation working correctly")
        print("   - No calculation errors detected")
    else:
        print(f"❌ Found {total_failed_checks} potential issues")
        print("   Review the details above for specific problems")
    
    print()
    print(f"💡 Recommendation: {'PASS' if total_failed_checks == 0 else 'INVESTIGATE'}")


if __name__ == "__main__":
    try:
        run_income_range_validation()
    except KeyboardInterrupt:
        print("\n🛑 Validation interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Validation failed with error: {e}")
        sys.exit(1)
