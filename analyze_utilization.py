#!/usr/bin/env python3
"""
Quick utilization distribution analysis
"""

import sys
from pathlib import Path
from decimal import Decimal

# Add project root to path
project_root = Path(__file__).resolve().parent
sys.path.insert(0, str(project_root))

from taxglide.engine.optimize import optimize_deduction_adaptive
from taxglide.engine.federal import tax_federal
from taxglide.engine.stgallen import simple_tax_sg
from taxglide.engine.multipliers import apply_multipliers, MultPick
from taxglide.engine.models import chf
from taxglide.io.loader import load_configs
from taxglide.cli import _get_adaptive_tolerance_bp

def analyze_utilization_distribution():
    # Load configs
    CONFIG_ROOT = project_root / "configs"
    sg_cfg, fed_cfg, mult_cfg = load_configs(CONFIG_ROOT, 2025)
    
    print("🔍 Analyzing utilization distribution across income spectrum")
    print("=" * 60)
    
    # Fine-stepped analysis as requested
    incomes = list(range(30000, 130001, 100))  # Every 100 CHF from 30K to 130K
    results = []
    
    for income in incomes:
        max_deduction = 30000  # Fixed 30K CHF deduction space for all income levels
        
        def calc_fn(current_income: Decimal):
            sg_simple = simple_tax_sg(current_income, sg_cfg)
            sg_after = apply_multipliers(sg_simple, mult_cfg, MultPick(["KANTON", "GEMEINDE"]))
            fed = tax_federal(current_income, fed_cfg)
            total = sg_after + fed
            return {"total": total, "federal": fed}
        
        tolerance_bp = _get_adaptive_tolerance_bp(income)
        
        result = optimize_deduction_adaptive(
            income=chf(income),
            max_deduction=max_deduction,
            step=100,
            calc_fn=calc_fn,
            initial_roi_tolerance_bp=tolerance_bp,
            enable_adaptive_retry=True,
        )
        
        if result["sweet_spot"]:
            deduction = result["sweet_spot"]["deduction"]
            utilization = deduction / max_deduction
            tax_saved = result["sweet_spot"]["tax_saved_absolute"]
            roi = (tax_saved / deduction * 100) if deduction > 0 else 0
            
            results.append({
                "income": income,
                "utilization": utilization,
                "deduction": deduction,
                "max_deduction": max_deduction,
                "roi": roi,
                "tax_saved": tax_saved
            })
    
    if not results:
        print("No results to analyze!")
        return
    
    # Utilization distribution analysis
    very_low_util = sum(1 for r in results if r["utilization"] < 0.20)   # <20%
    low_util = sum(1 for r in results if 0.20 <= r["utilization"] < 0.40)  # 20-40%  
    medium_util = sum(1 for r in results if 0.40 <= r["utilization"] < 0.70)  # 40-70%
    high_util = sum(1 for r in results if 0.70 <= r["utilization"] < 0.90)  # 70-90%
    very_high_util = sum(1 for r in results if r["utilization"] >= 0.90)  # ≥90%
    
    total = len(results)
    avg_utilization = sum(r["utilization"] for r in results) / total
    over_70_percent = high_util + very_high_util
    
    print(f"Sample size: {total} income levels from 30K to 145K CHF")
    print(f"Average utilization: {avg_utilization:.1%}")
    print()
    
    print("📊 UTILIZATION DISTRIBUTION:")
    print("-" * 40)
    print(f"Very Low (<20%):     {very_low_util:3d} ({very_low_util/total*100:5.1f}%)")
    print(f"Low (20-40%):        {low_util:3d} ({low_util/total*100:5.1f}%) ← TARGET RANGE")  
    print(f"Medium (40-70%):     {medium_util:3d} ({medium_util/total*100:5.1f}%)")
    print(f"High (70-90%):       {high_util:3d} ({high_util/total*100:5.1f}%) ← PROBLEMATIC")
    print(f"Very High (≥90%):    {very_high_util:3d} ({very_high_util/total*100:5.1f}%) ← VERY PROBLEMATIC")
    print()
    print(f"🚨 KEY FINDING: {over_70_percent} out of {total} cases ({over_70_percent/total*100:.1f}%) have >70% utilization")
    print()
    
    # Show some examples of high utilization cases
    high_cases = [r for r in results if r["utilization"] >= 0.70]
    if high_cases:
        print("Examples of high utilization cases:")
        print("-" * 50)
        for case in high_cases[:5]:
            print(f"  Income {case['income']:,}: {case['utilization']:.1%} utilization ({case['deduction']:,}/{case['max_deduction']:,} CHF)")
    
    # Show some examples of good utilization cases  
    good_cases = [r for r in results if 0.25 <= r["utilization"] <= 0.40]
    if good_cases:
        print()
        print("Examples of good utilization cases (25-40%):")
        print("-" * 50)
        for case in good_cases[:5]:
            print(f"  Income {case['income']:,}: {case['utilization']:.1%} utilization ({case['deduction']:,}/{case['max_deduction']:,} CHF)")

if __name__ == "__main__":
    analyze_utilization_distribution()
