#!/usr/bin/env python3
"""
Customizable income range validation script for TaxGlide.

This script allows you to test different income ranges, steps, and parameters
to validate the reasonableness of tax calculations.
"""

import sys
import argparse
from pathlib import Path
from taxglide.cli import _calc_once

def run_validation(start_income=500, end_income=200000, step_income=1000, filing_status="single", 
                   include_feuer=False, verbose=False):
    """Run income range validation with custom parameters."""
    
    # Use default multipliers, optionally including FEUER
    multipliers = ["KANTON", "GEMEINDE"]
    if include_feuer:
        multipliers.append("FEUER")
    
    print(f"🧮 TaxGlide Custom Income Range Validation")
    print("=" * 60)
    print(f"Income range: {start_income:,} to {end_income:,} CHF (step: {step_income:,})")
    print(f"Filing status: {filing_status}")
    print(f"Multipliers: {', '.join(multipliers)}")
    
    incomes = list(range(start_income, end_income + 1, step_income))
    total_calculations = len(incomes)
    print(f"Total calculations: {total_calculations:,}")
    print()
    
    # Run calculations
    results = []
    failures = []
    
    print("🔄 Running calculations...")
    for i, income in enumerate(incomes):
        if i % 25 == 0 or i == total_calculations - 1:
            progress = (i + 1) / total_calculations * 100
            print(f"  Progress: {i+1:3d}/{total_calculations} ({progress:5.1f}%) - Income: {income:,} CHF")
        
        try:
            result = _calc_once(2025, income, multipliers, filing_status)
            results.append(result)
            
            # Basic reasonableness checks
            if result["total"] < 0:
                failures.append(f"Negative tax at {income:,} CHF: {result['total']}")
            if result["avg_rate"] < 0 or result["avg_rate"] > 0.6:
                failures.append(f"Unreasonable avg rate at {income:,} CHF: {result['avg_rate']:.1%}")
            if result["marginal_total"] < 0 or result["marginal_total"] > 0.7:
                failures.append(f"Unreasonable marginal rate at {income:,} CHF: {result['marginal_total']:.1%}")
                
        except Exception as e:
            failures.append(f"Calculation failed at {income:,} CHF: {e}")
    
    print(f"✅ Completed {len(results):,} calculations")
    print()
    
    if failures:
        print(f"❌ Found {len(failures)} issues:")
        for failure in failures:
            print(f"  - {failure}")
        return False
    
    # Analysis
    print("📊 ANALYSIS RESULTS")
    print("=" * 60)
    
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
    
    # Sample results table
    print("📈 SAMPLE RESULTS")
    print("-" * 85)
    print(f"{'Income':>10} | {'Total Tax':>10} | {'Federal':>8} | {'SG After':>9} | {'Avg Rate':>8} | {'Marginal':>8}")
    print("-" * 85)
    
    # Show every 10th result or key milestones
    sample_indices = []
    for i in range(0, len(results), max(1, len(results) // 15)):  # Show ~15 samples
        sample_indices.append(i)
    if len(results) - 1 not in sample_indices:
        sample_indices.append(len(results) - 1)  # Always show the last one
    
    for i in sample_indices:
        r = results[i]
        print(f"{r['income']:10,} | {r['total']:10,.0f} | {r['federal']:8,.0f} | "
              f"{r['sg_after_mult']:9,.0f} | {r['avg_rate']:7.1%} | {r['marginal_total']:7.1%}")
    
    print()
    
    # Detailed analysis if verbose
    if verbose:
        print("🔍 DETAILED ANALYSIS")
        print("-" * 30)
        
        # Monotonicity check
        violations = []
        for i in range(1, len(results)):
            prev_tax = results[i-1]["total"]
            curr_tax = results[i]["total"]
            if curr_tax < prev_tax:
                violations.append({
                    "from_income": results[i-1]["income"],
                    "to_income": results[i]["income"],
                    "regression": prev_tax - curr_tax
                })
        
        print(f"Monotonicity violations: {len(violations)}")
        if violations:
            for v in violations[:5]:
                print(f"  {v['from_income']:,} -> {v['to_income']:,}: regression {v['regression']:.2f} CHF")
        
        # Large marginal rate jumps
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
        
        print(f"Large marginal rate jumps (>5%): {len(large_jumps)}")
        for jump in large_jumps[:5]:
            print(f"  {jump['from_income']:,} -> {jump['to_income']:,}: "
                  f"{jump['from_rate']:.1%} -> {jump['to_rate']:.1%} (jump: {jump['jump']:.1%})")
        
        print()
    
    # Summary checks
    print("✅ VALIDATION SUMMARY")
    print("-" * 25)
    
    all_non_negative = all(r['total'] >= 0 for r in results)
    rates_reasonable = all(0 <= r['avg_rate'] <= 0.5 for r in results)
    marginal_reasonable = all(0 <= r['marginal_total'] <= 0.6 for r in results)
    
    # Progressive check
    if len(results) >= 10:
        low_income_avg = sum(r["avg_rate"] for r in results[:5]) / 5
        high_income_avg = sum(r["avg_rate"] for r in results[-5:]) / 5
        is_progressive = high_income_avg > low_income_avg
    else:
        is_progressive = True  # Assume true for small samples
    
    print(f"✅ All taxes non-negative: {all_non_negative}")
    print(f"✅ Average rates reasonable (0-50%): {rates_reasonable}")
    print(f"✅ Marginal rates reasonable (0-60%): {marginal_reasonable}")
    print(f"✅ Progressive taxation: {is_progressive}")
    
    all_checks_pass = all([all_non_negative, rates_reasonable, marginal_reasonable, is_progressive])
    
    print()
    print(f"🎯 FINAL RESULT: {'✅ PASS' if all_checks_pass else '❌ FAIL'}")
    
    if all_checks_pass:
        print("   All tax calculations appear reasonable across the income range!")
    else:
        print("   Some calculations may need investigation.")
        
    return all_checks_pass


def main():
    parser = argparse.ArgumentParser(description="Validate TaxGlide calculations across income ranges")
    parser.add_argument("--start", type=int, default=500, 
                       help="Starting income in CHF (default: 500)")
    parser.add_argument("--end", type=int, default=200000,
                       help="Ending income in CHF (default: 200,000)")
    parser.add_argument("--step", type=int, default=1000,
                       help="Income step size in CHF (default: 1,000)")
    parser.add_argument("--filing-status", choices=["single", "married_joint"], 
                       default="single", help="Filing status (default: single)")
    parser.add_argument("--include-feuer", action="store_true",
                       help="Include FEUER (fire service) tax multiplier")
    parser.add_argument("--verbose", "-v", action="store_true",
                       help="Show detailed analysis")
    
    args = parser.parse_args()
    
    # Validation
    if args.start >= args.end:
        print("❌ Error: Start income must be less than end income")
        sys.exit(1)
    
    if args.step <= 0:
        print("❌ Error: Step size must be positive")
        sys.exit(1)
    
    if (args.end - args.start) // args.step > 1000:
        print("❌ Error: Too many calculations requested (max 1000). Use a larger step size.")
        sys.exit(1)
    
    try:
        success = run_validation(
            start_income=args.start,
            end_income=args.end,
            step_income=args.step,
            filing_status=args.filing_status,
            include_feuer=args.include_feuer,
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
