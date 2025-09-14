#!/usr/bin/env python3
"""
Enhanced optimization validation with adaptive tolerance retry.

This script demonstrates a solution to the low-utilization problem by automatically
retrying optimization with different tolerance settings when suboptimal deductions are detected.
"""

import sys
from pathlib import Path
from decimal import Decimal

# Add project root to path
project_root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(project_root))

from taxglide.engine.optimize import optimize_deduction
from taxglide.engine.federal import tax_federal
from taxglide.engine.stgallen import simple_tax_sg
from taxglide.engine.multipliers import apply_multipliers, MultPick
from taxglide.engine.models import chf
from taxglide.io.loader import load_configs


def enhanced_optimize_deduction(income, max_deduction, step, calc_fn, initial_tolerance_bp=10.0):
    """
    Enhanced optimization that retries with different tolerances if initial result shows low utilization.
    
    Args:
        income: Income amount (Decimal)
        max_deduction: Maximum deduction allowed
        step: Optimization step size
        calc_fn: Tax calculation function
        initial_tolerance_bp: Initial ROI tolerance in basis points
    
    Returns:
        Dictionary with optimization results including retry information
    """
    
    # Tolerance progression strategy
    tolerance_strategies = [
        (initial_tolerance_bp, "initial"),
        (initial_tolerance_bp * 3, "relaxed"),     # 3x more relaxed
        (initial_tolerance_bp * 0.3, "strict"),   # Much stricter
        (100.0, "very_relaxed"),                  # Very wide tolerance
        (1.0, "very_strict"),                     # Very tight tolerance
    ]
    
    results = []
    best_result = None
    best_absolute_savings = 0
    
    for tolerance_bp, strategy_name in tolerance_strategies:
        try:
            result = optimize_deduction(
                income=income,
                max_deduction=max_deduction,
                step=step,
                calc_fn=calc_fn,
                roi_tolerance_bp=tolerance_bp
            )
            
            if result["sweet_spot"] is not None:
                sweet_spot = result["sweet_spot"]
                deduction = sweet_spot["deduction"]
                tax_saved = sweet_spot["tax_saved_absolute"]
                utilization_ratio = deduction / max_deduction
                
                # Store result with strategy info
                enhanced_result = {
                    "strategy": strategy_name,
                    "tolerance_bp": tolerance_bp,
                    "deduction": deduction,
                    "tax_saved": tax_saved,
                    "utilization_ratio": utilization_ratio,
                    "roi": (tax_saved / deduction * 100) if deduction > 0 else 0,
                    "new_income": sweet_spot["new_income"],
                    "full_result": result
                }
                results.append(enhanced_result)
                
                # Track best by absolute savings (not just ROI)
                if tax_saved > best_absolute_savings:
                    best_absolute_savings = tax_saved
                    best_result = enhanced_result
                
                # Early exit if we get good utilization and good ROI
                if utilization_ratio > 0.30 and enhanced_result["roi"] > 15:
                    print(f"    ✅ Good solution found with {strategy_name} strategy")
                    break
                
            else:
                results.append({
                    "strategy": strategy_name,
                    "tolerance_bp": tolerance_bp,
                    "deduction": None,
                    "tax_saved": 0,
                    "utilization_ratio": 0,
                    "roi": 0,
                    "new_income": float(income),
                    "full_result": result
                })
        
        except Exception as e:
            print(f"    ⚠️ Strategy {strategy_name} failed: {e}")
            continue
    
    return {
        "all_results": results,
        "best_result": best_result,
        "improvement_found": len(results) > 1 and best_result and best_result["strategy"] != "initial"
    }


def test_enhanced_optimization():
    """Test the enhanced optimization approach on problematic cases."""
    
    # Load configs
    CONFIG_ROOT = project_root / "configs"
    sg_cfg, fed_cfg, mult_cfg = load_configs(CONFIG_ROOT, 2025)
    
    # Test cases that showed low utilization
    test_cases = [
        (60000, 8000, "60K income case"),
        (100000, 15000, "100K income case"),
        (80000, 12000, "80K income case"),
        (120000, 18000, "120K income case"),
    ]
    
    print("🔬 Testing Enhanced Multi-Tolerance Optimization")
    print("=" * 60)
    print("This approach retries optimization with different tolerances")
    print("when low utilization is detected, seeking better absolute savings.")
    print()
    
    for income, max_deduction, description in test_cases:
        print(f"🧮 Testing {description}: {income:,} CHF (max deduction: {max_deduction:,})")
        
        # Create calculation function
        def calc_fn(current_income: Decimal):
            sg_simple = simple_tax_sg(current_income, sg_cfg)
            sg_after = apply_multipliers(sg_simple, mult_cfg, MultPick(["KANTON", "GEMEINDE"]))
            fed = tax_federal(current_income, fed_cfg)
            total = sg_after + fed
            return {"total": total, "federal": fed}
        
        # Run enhanced optimization
        enhanced_result = enhanced_optimize_deduction(
            income=chf(income),
            max_deduction=max_deduction,
            step=100,
            calc_fn=calc_fn,
            initial_tolerance_bp=10.0
        )
        
        # Analyze results
        all_results = enhanced_result["all_results"]
        best_result = enhanced_result["best_result"]
        improvement_found = enhanced_result["improvement_found"]
        
        if not best_result:
            print("  ❌ No optimization found with any strategy")
            continue
        
        # Show comparison table
        print(f"  📊 Strategy Comparison:")
        print(f"  {'Strategy':12} | {'Tolerance':9} | {'Deduction':9} | {'Savings':8} | {'ROI':6} | {'Utiliz':7}")
        print(f"  {'-'*12} | {'-'*9} | {'-'*9} | {'-'*8} | {'-'*6} | {'-'*7}")
        
        for result in all_results[:5]:  # Show first 5 strategies
            if result["deduction"] is not None:
                print(f"  {result['strategy']:12} | {result['tolerance_bp']:7.1f}bp | "
                      f"{result['deduction']:7,.0f} | {result['tax_saved']:6,.0f} | "
                      f"{result['roi']:5.1f}% | {result['utilization_ratio']:6.1%}")
            else:
                print(f"  {result['strategy']:12} | {result['tolerance_bp']:7.1f}bp | {'No opt':>7} | {'—':>6} | {'—':>5} | {'—':>6}")
        
        # Show best recommendation
        if improvement_found:
            initial_result = next(r for r in all_results if r["strategy"] == "initial")
            best = best_result
            
            if initial_result["deduction"] is not None:
                improvement_savings = best["tax_saved"] - initial_result["tax_saved"]
                improvement_utilization = best["utilization_ratio"] - initial_result["utilization_ratio"]
                
                print(f"  🎯 RECOMMENDATION: Use {best['strategy']} strategy")
                print(f"     Initial: {initial_result['deduction']:,.0f} CHF deduction, "
                      f"{initial_result['tax_saved']:,.0f} CHF savings ({initial_result['utilization_ratio']:.1%} utilization)")
                print(f"     Better:  {best['deduction']:,.0f} CHF deduction, "
                      f"{best['tax_saved']:,.0f} CHF savings ({best['utilization_ratio']:.1%} utilization)")
                print(f"     Improvement: +{improvement_savings:,.0f} CHF savings, "
                      f"+{improvement_utilization:.1%} utilization")
            else:
                print(f"  🎯 RECOMMENDATION: Use {best['strategy']} strategy (initial found no optimization)")
                print(f"     Solution: {best['deduction']:,.0f} CHF deduction, "
                      f"{best['tax_saved']:,.0f} CHF savings ({best['utilization_ratio']:.1%} utilization)")
        else:
            print(f"  ✅ Initial strategy was already optimal")
            print(f"     Solution: {best_result['deduction']:,.0f} CHF deduction, "
                  f"{best_result['tax_saved']:,.0f} CHF savings ({best_result['utilization_ratio']:.1%} utilization)")
        
        print()
    
    print("💡 IMPLEMENTATION STRATEGY")
    print("-" * 40)
    print("1. Run initial optimization with standard tolerance (10bp)")
    print("2. Check if utilization < 30% AND income > 50K CHF")
    print("3. If yes, retry with relaxed tolerance (30bp) and very strict (3bp)")
    print("4. Compare absolute savings (not just ROI) and recommend best")
    print("5. This catches cases where ROI optimization misses larger beneficial deductions")
    print()
    
    print("🔧 INTEGRATION OPTIONS")
    print("-" * 30)
    print("A. CLI Enhancement: Add --adaptive-tolerance flag to optimize command")
    print("B. Engine Enhancement: Build into optimize_deduction as default behavior")  
    print("C. Validation Enhancement: Use in validation scripts for better benchmarks")
    print("D. User Warning: Alert when low utilization detected, suggest retry")


if __name__ == "__main__":
    test_enhanced_optimization()
