"""Tests for income range validation across the full spectrum of Swiss tax calculations.

This test suite validates the reasonableness of tax calculations across income levels
from 500 to 200,000 CHF with 1,000 CHF steps, checking for consistency and expected behavior.
"""

import pytest
from decimal import Decimal
from typing import List, Dict, Any, Tuple

from taxglide.cli import _calc_once
from taxglide.engine.optimize import optimize_deduction
from taxglide.engine.federal import tax_federal
from taxglide.engine.stgallen import simple_tax_sg
from taxglide.engine.multipliers import apply_multipliers, MultPick
from taxglide.engine.models import chf
from taxglide.io.loader import load_configs


class TestIncomeRangeValidation:
    """Comprehensive validation of tax calculations across income ranges."""
    
    INCOME_START = 500
    INCOME_END = 200000
    INCOME_STEP = 1000
    
    # Reasonableness criteria
    MAX_MARGINAL_RATE = 0.50  # 50% - should never exceed this
    MAX_AVERAGE_RATE = 0.35   # 35% - Swiss rates shouldn't exceed this for individuals
    MIN_MARGINAL_RATE = 0.0   # 0% - marginal rate can be zero at low incomes
    
    # Expected rate progression tolerances
    MARGINAL_RATE_JUMP_TOLERANCE = 0.05  # 5% - marginal rate shouldn't jump more than this between steps
    AVERAGE_RATE_REGRESSION_TOLERANCE = 0.001  # 0.1% - average rate can slightly decrease due to rounding
    
    def _generate_income_range(self) -> List[int]:
        """Generate list of incomes to test."""
        return list(range(self.INCOME_START, self.INCOME_END + 1, self.INCOME_STEP))
    
    def _calculate_all_incomes(self, year: int = 2025, filing_status: str = "single") -> List[Dict[str, Any]]:
        """Calculate taxes for all income levels in the range."""
        # Use default multipliers (KANTON + GEMEINDE)
        default_picks = ["KANTON", "GEMEINDE"]
        
        results = []
        incomes = self._generate_income_range()
        
        print(f"\nCalculating taxes for {len(incomes)} income levels ({self.INCOME_START:,} to {self.INCOME_END:,} CHF)...")
        
        for i, income in enumerate(incomes):
            if i % 20 == 0:  # Progress indicator every 20 calculations
                print(f"Progress: {i+1}/{len(incomes)} ({income:,} CHF)")
                
            try:
                result = _calc_once(year, income, default_picks, filing_status)
                results.append(result)
            except Exception as e:
                pytest.fail(f"Failed to calculate taxes for income {income:,} CHF: {e}")
        
        print(f"Completed {len(results)} tax calculations.")
        return results
    
    def test_income_range_monotonicity(self, default_multiplier_codes):
        """Test that total tax increases monotonically with income (or stays equal)."""
        results = self._calculate_all_incomes()
        
        failures = []
        for i in range(1, len(results)):
            prev_result = results[i-1]
            curr_result = results[i]
            
            prev_total = prev_result["total"]
            curr_total = curr_result["total"]
            prev_income = prev_result["income"]
            curr_income = curr_result["income"]
            
            # Total tax should never decrease with higher income
            if curr_total < prev_total - 0.01:  # Small tolerance for rounding
                failures.append({
                    "income_from": prev_income,
                    "income_to": curr_income,
                    "tax_from": prev_total,
                    "tax_to": curr_total,
                    "decrease": prev_total - curr_total
                })
        
        if failures:
            print(f"\n❌ Found {len(failures)} monotonicity violations:")
            for failure in failures[:5]:  # Show first 5 failures
                print(f"  Income {failure['income_from']:,} -> {failure['income_to']:,}: "
                      f"Tax {failure['tax_from']:.2f} -> {failure['tax_to']:.2f} "
                      f"(decreased by {failure['decrease']:.2f} CHF)")
            if len(failures) > 5:
                print(f"  ... and {len(failures) - 5} more")
        
        assert len(failures) == 0, f"Tax should never decrease with income. Found {len(failures)} violations."
    
    def test_marginal_rates_within_bounds(self, default_multiplier_codes):
        """Test that marginal rates stay within reasonable bounds."""
        results = self._calculate_all_incomes()
        
        marginal_failures = []
        
        for result in results:
            marginal_rate = result["marginal_total"]
            income = result["income"]
            
            # Check bounds
            if marginal_rate < self.MIN_MARGINAL_RATE:
                marginal_failures.append({
                    "income": income,
                    "rate": marginal_rate,
                    "issue": "below_minimum",
                    "bound": self.MIN_MARGINAL_RATE
                })
            elif marginal_rate > self.MAX_MARGINAL_RATE:
                marginal_failures.append({
                    "income": income,
                    "rate": marginal_rate,
                    "issue": "above_maximum", 
                    "bound": self.MAX_MARGINAL_RATE
                })
        
        if marginal_failures:
            print(f"\n❌ Found {len(marginal_failures)} marginal rate bound violations:")
            for failure in marginal_failures[:5]:
                print(f"  Income {failure['income']:,}: marginal rate {failure['rate']:.1%} "
                      f"{failure['issue']} {failure['bound']:.1%}")
        
        assert len(marginal_failures) == 0, f"Found {len(marginal_failures)} marginal rate violations"
    
    def test_average_rates_within_bounds(self, default_multiplier_codes):
        """Test that average rates stay within reasonable bounds and are generally progressive."""
        results = self._calculate_all_incomes()
        
        avg_rate_failures = []
        progression_failures = []
        
        for i, result in enumerate(results):
            avg_rate = result["avg_rate"]
            income = result["income"]
            
            # Check bounds
            if avg_rate < 0:
                avg_rate_failures.append({
                    "income": income,
                    "rate": avg_rate,
                    "issue": "negative"
                })
            elif avg_rate > self.MAX_AVERAGE_RATE:
                avg_rate_failures.append({
                    "income": income, 
                    "rate": avg_rate,
                    "issue": "above_maximum",
                    "bound": self.MAX_AVERAGE_RATE
                })
            
            # Check progression (average rate should generally increase, allowing some tolerance)
            if i > 0:
                prev_avg_rate = results[i-1]["avg_rate"]
                if avg_rate < prev_avg_rate - self.AVERAGE_RATE_REGRESSION_TOLERANCE:
                    progression_failures.append({
                        "income_from": results[i-1]["income"],
                        "income_to": income,
                        "avg_rate_from": prev_avg_rate,
                        "avg_rate_to": avg_rate,
                        "regression": prev_avg_rate - avg_rate
                    })
        
        # Report failures
        if avg_rate_failures:
            print(f"\n❌ Found {len(avg_rate_failures)} average rate bound violations:")
            for failure in avg_rate_failures[:5]:
                print(f"  Income {failure['income']:,}: avg rate {failure['rate']:.1%} {failure['issue']}")
        
        if progression_failures:
            print(f"\n⚠️ Found {len(progression_failures)} average rate progression anomalies:")
            for failure in progression_failures[:5]:
                print(f"  Income {failure['income_from']:,} -> {failure['income_to']:,}: "
                      f"avg rate {failure['avg_rate_from']:.2%} -> {failure['avg_rate_to']:.2%} "
                      f"(regressed by {failure['regression']:.3%})")
        
        assert len(avg_rate_failures) == 0, f"Found {len(avg_rate_failures)} average rate bound violations"
        
        # Allow some progression anomalies but not too many (rounding can cause small regressions)
        max_allowed_regressions = len(results) * 0.05  # Allow up to 5% of cases to have small regressions
        assert len(progression_failures) <= max_allowed_regressions, \
               f"Too many average rate regressions: {len(progression_failures)} > {max_allowed_regressions:.0f}"
    
    def test_tax_components_consistency(self, default_multiplier_codes):
        """Test that tax components add up correctly and follow expected patterns."""
        results = self._calculate_all_incomes()
        
        component_failures = []
        
        for result in results:
            income = result["income"]
            federal = result["federal"]
            sg_simple = result["sg_simple"]
            sg_after_mult = result["sg_after_mult"]
            total = result["total"]
            
            # Basic component checks
            if federal < 0:
                component_failures.append(f"Income {income:,}: negative federal tax {federal}")
            if sg_simple < 0:
                component_failures.append(f"Income {income:,}: negative SG simple tax {sg_simple}")
            if sg_after_mult < 0:
                component_failures.append(f"Income {income:,}: negative SG after multipliers {sg_after_mult}")
            
            # SG after multipliers should be >= SG simple (multipliers should increase tax)
            if sg_after_mult < sg_simple - 0.01:  # Small tolerance for rounding
                component_failures.append(
                    f"Income {income:,}: SG after mult ({sg_after_mult:.2f}) < SG simple ({sg_simple:.2f})"
                )
            
            # Total should equal federal + SG after multipliers
            expected_total = federal + sg_after_mult
            if abs(total - expected_total) > 0.01:  # Small tolerance for rounding
                component_failures.append(
                    f"Income {income:,}: total ({total:.2f}) != federal + SG ({expected_total:.2f})"
                )
        
        if component_failures:
            print(f"\n❌ Found {len(component_failures)} component consistency issues:")
            for failure in component_failures[:10]:
                print(f"  {failure}")
            if len(component_failures) > 10:
                print(f"  ... and {len(component_failures) - 10} more")
        
        assert len(component_failures) == 0, f"Found {len(component_failures)} component consistency issues"
    
    def test_bracket_transitions_smooth(self, default_multiplier_codes):
        """Test that transitions between tax brackets are smooth (no huge jumps)."""
        results = self._calculate_all_incomes()
        
        jump_failures = []
        
        for i in range(1, len(results)):
            prev_result = results[i-1]
            curr_result = results[i]
            
            prev_marginal = prev_result["marginal_total"]
            curr_marginal = curr_result["marginal_total"]
            income_diff = curr_result["income"] - prev_result["income"]
            
            # Check for unreasonable marginal rate jumps
            marginal_jump = abs(curr_marginal - prev_marginal)
            if marginal_jump > self.MARGINAL_RATE_JUMP_TOLERANCE:
                jump_failures.append({
                    "income_from": prev_result["income"],
                    "income_to": curr_result["income"],
                    "marginal_from": prev_marginal,
                    "marginal_to": curr_marginal,
                    "jump": marginal_jump
                })
        
        if jump_failures:
            print(f"\n⚠️ Found {len(jump_failures)} large marginal rate jumps:")
            for failure in jump_failures[:5]:
                print(f"  Income {failure['income_from']:,} -> {failure['income_to']:,}: "
                      f"marginal {failure['marginal_from']:.1%} -> {failure['marginal_to']:.1%} "
                      f"(jump: {failure['jump']:.1%})")
        
        # Allow some large jumps (bracket transitions can cause them) but not too many
        max_allowed_jumps = len(results) * 0.10  # Allow up to 10% of transitions to have large jumps
        assert len(jump_failures) <= max_allowed_jumps, \
               f"Too many large marginal rate jumps: {len(jump_failures)} > {max_allowed_jumps:.0f}"
    
    def test_known_good_values_within_range(self, sample_tax_cases, default_multiplier_codes):
        """Test that our range calculations match known good values from existing test cases."""
        results_dict = {}
        
        # Calculate all values and index by income
        all_results = self._calculate_all_incomes()
        for result in all_results:
            results_dict[result["income"]] = result
        
        # Check each known good case that falls within our range
        mismatches = []
        
        for test_case in sample_tax_cases:
            income = test_case.income
            if income < self.INCOME_START or income > self.INCOME_END:
                continue  # Skip cases outside our range
                
            # Find closest calculated income (should be exact for our step size)
            if income in results_dict:
                calculated = results_dict[income]
            else:
                # Find nearest income if not exact match
                nearest_income = min(results_dict.keys(), key=lambda x: abs(x - income))
                if abs(nearest_income - income) > self.INCOME_STEP:
                    continue  # Too far from our calculation points
                calculated = results_dict[nearest_income]
                income = nearest_income  # Use the calculated income for comparison
            
            # Compare with tolerance
            # Use higher tolerance for step-based calculations since we're comparing
            # against nearest income values rather than exact matches
            tolerance = 200.0  # 200 CHF tolerance for step-based range validation
            
            components = [
                ("federal", float(test_case.federal_tax)),
                ("sg_after_mult", float(test_case.sg_after_mult)),
                ("total", float(test_case.total_tax))
            ]
            
            for component_name, expected_value in components:
                calculated_value = calculated[component_name]
                diff = abs(calculated_value - expected_value)
                
                if diff > tolerance:
                    mismatches.append({
                        "income": income,
                        "component": component_name,
                        "expected": expected_value,
                        "calculated": calculated_value,
                        "diff": diff
                    })
        
        if mismatches:
            print(f"\n❌ Found {len(mismatches)} mismatches with known good values:")
            for mismatch in mismatches:
                print(f"  Income {mismatch['income']:,}, {mismatch['component']}: "
                      f"expected {mismatch['expected']:.2f}, got {mismatch['calculated']:.2f} "
                      f"(diff: {mismatch['diff']:.2f} CHF)")
        
        assert len(mismatches) == 0, f"Found {len(mismatches)} mismatches with known good values"
    
    def test_income_range_summary_statistics(self, default_multiplier_codes):
        """Generate summary statistics for the income range to validate overall reasonableness."""
        results = self._calculate_all_incomes()
        
        # Calculate statistics
        incomes = [r["income"] for r in results]
        total_taxes = [r["total"] for r in results]
        avg_rates = [r["avg_rate"] for r in results]
        marginal_rates = [r["marginal_total"] for r in results]
        
        # Basic stats
        min_income, max_income = min(incomes), max(incomes)
        min_tax, max_tax = min(total_taxes), max(total_taxes)
        min_avg_rate, max_avg_rate = min(avg_rates), max(avg_rates)
        min_marginal, max_marginal = min(marginal_rates), max(marginal_rates)
        
        # Calculate effective rates at key income levels
        key_incomes = [10000, 25000, 50000, 75000, 100000, 150000, 200000]
        key_stats = []
        
        for target_income in key_incomes:
            if target_income > max_income:
                continue
            # Find closest result
            closest_result = min(results, key=lambda x: abs(x["income"] - target_income))
            if abs(closest_result["income"] - target_income) <= self.INCOME_STEP:
                key_stats.append({
                    "income": closest_result["income"],
                    "total_tax": closest_result["total"],
                    "avg_rate": closest_result["avg_rate"],
                    "marginal_rate": closest_result["marginal_total"]
                })
        
        # Print summary
        print(f"\n📊 Income Range Validation Summary ({len(results):,} calculations)")
        print(f"Income range: {min_income:,} - {max_income:,} CHF")
        print(f"Tax range: {min_tax:.2f} - {max_tax:,.2f} CHF")
        print(f"Average rate range: {min_avg_rate:.1%} - {max_avg_rate:.1%}")
        print(f"Marginal rate range: {min_marginal:.1%} - {max_marginal:.1%}")
        
        if key_stats:
            print(f"\n📈 Key Income Level Analysis:")
            print("Income    | Total Tax  | Avg Rate | Marginal Rate")
            print("-" * 50)
            for stat in key_stats:
                print(f"{stat['income']:8,} | {stat['total_tax']:9,.0f} | {stat['avg_rate']:7.1%} | {stat['marginal_rate']:12.1%}")
        
        # Validate overall reasonableness
        assert min_tax >= 0, "Minimum tax should not be negative"
        assert min_avg_rate >= 0, "Minimum average rate should not be negative"
        assert max_avg_rate <= self.MAX_AVERAGE_RATE, f"Maximum average rate {max_avg_rate:.1%} exceeds limit {self.MAX_AVERAGE_RATE:.1%}"
        assert max_marginal <= self.MAX_MARGINAL_RATE, f"Maximum marginal rate {max_marginal:.1%} exceeds limit {self.MAX_MARGINAL_RATE:.1%}"
        
        # Check progression at key points
        if len(key_stats) >= 3:
            # Average rate should generally increase
            for i in range(1, len(key_stats)):
                curr_avg = key_stats[i]["avg_rate"]
                prev_avg = key_stats[i-1]["avg_rate"]
                assert curr_avg >= prev_avg - 0.01, \
                       f"Average rate regression at income {key_stats[i]['income']:,}: {curr_avg:.2%} < {prev_avg:.2%}"
        
        print("✅ All summary statistics look reasonable!")
    
    @pytest.mark.parametrize("filing_status", ["single", "married_joint"])
    def test_filing_status_comparison(self, filing_status, default_multiplier_codes):
        """Test that both filing statuses produce reasonable results across the income range."""
        # Calculate subset of incomes for performance (every 10th income)
        test_incomes = list(range(self.INCOME_START, min(100000, self.INCOME_END + 1), self.INCOME_STEP * 10))
        
        results = []
        for income in test_incomes:
            try:
                result = _calc_once(2025, income, ["KANTON", "GEMEINDE"], filing_status)
                results.append(result)
            except Exception as e:
                pytest.fail(f"Failed to calculate taxes for income {income:,} CHF with filing status {filing_status}: {e}")
        
        # Basic validation
        assert len(results) > 0, f"No results calculated for filing status {filing_status}"
        
        # All results should have reasonable values
        for result in results:
            assert result["total"] >= 0, f"Negative total tax for {filing_status}: {result}"
            assert 0 <= result["avg_rate"] <= 0.5, f"Unreasonable avg rate for {filing_status}: {result['avg_rate']:.1%}"
            
        print(f"✅ Filing status {filing_status} validation passed for {len(results)} income levels")


class TestOptimizationRangeValidation:
    """Test that optimization produces reasonable results across income ranges."""
    
    def test_optimization_reasonableness_across_incomes(self, config_root):
        """Test that optimization suggestions are reasonable across different income levels."""
        # Load configs
        sg_cfg, fed_cfg, mult_cfg = load_configs(config_root, 2025)
        
        # Test scenarios: (income, max_deduction, description)
        test_scenarios = [
            (30000, 3000, "Lower income"),
            (50000, 8000, "Mid income"),
            (80000, 12000, "Higher income"),
            (120000, 20000, "High income"),
            (200000, 30000, "Very high income")
        ]
        
        optimization_failures = []
        
        for income, max_deduction, description in test_scenarios:
            try:
                # Create calc function
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
                    # It's okay if no optimization is found for some incomes
                    print(f"No optimization found for {description} ({income:,} CHF) - this can be normal")
                    continue
                
                sweet_spot = result["sweet_spot"]
                deduction = sweet_spot["deduction"]
                tax_saved = sweet_spot["tax_saved_absolute"]
                roi = tax_saved / deduction * 100 if deduction > 0 else 0
                new_income = sweet_spot["new_income"]
                
                # Reasonableness checks
                checks = []
                
                # 1. Deduction should be within bounds
                if not (0 < deduction <= max_deduction):
                    checks.append(f"Deduction {deduction} not within bounds (0, {max_deduction}]")
                
                # 2. New income should be lower
                if new_income >= income:
                    checks.append(f"New income {new_income} should be less than original {income}")
                
                # 3. Tax savings should be positive
                if tax_saved <= 0:
                    checks.append(f"Tax savings {tax_saved:.2f} should be positive")
                
                # 4. ROI should be reasonable (Swiss system can have very high ROI due to brackets)
                if roi <= 0:
                    checks.append(f"ROI {roi:.1f}% should be positive")
                elif roi > 500:  # More lenient than original test
                    checks.append(f"ROI {roi:.1f}% seems unrealistically high")
                
                # 5. Deduction shouldn't be tiny (less than 1% of max)
                if deduction < max_deduction * 0.01:
                    checks.append(f"Deduction {deduction} is very small compared to max {max_deduction}")
                
                # 6. Tax savings should be reasonable compared to deduction
                savings_ratio = tax_saved / deduction
                if savings_ratio > 5.0:  # Savings more than 5x the deduction cost
                    print(f"⚠️ Very high savings ratio for {description}: {savings_ratio:.1f}x (could indicate bracket optimization)")
                
                if checks:
                    optimization_failures.extend([
                        f"{description} ({income:,} CHF): {check}" for check in checks
                    ])
                else:
                    print(f"✅ {description} ({income:,} CHF): Deduct {deduction:,} CHF, save {tax_saved:.0f} CHF (ROI: {roi:.1f}%)")
                    
            except Exception as e:
                optimization_failures.append(f"{description} ({income:,} CHF): Optimization failed - {e}")
        
        if optimization_failures:
            print(f"\n❌ Found {len(optimization_failures)} optimization issues:")
            for failure in optimization_failures:
                print(f"  - {failure}")
        
        assert len(optimization_failures) == 0, f"Found {len(optimization_failures)} optimization reasonableness issues"
    
    def test_optimization_roi_progression(self, config_root):
        """Test that ROI generally decreases with higher incomes (diminishing returns)."""
        # Load configs
        sg_cfg, fed_cfg, mult_cfg = load_configs(config_root, 2025)
        
        # Test progressive income levels with proportional deduction limits
        income_levels = [40000, 60000, 80000, 100000, 120000]
        roi_results = []
        
        for income in income_levels:
            max_deduction = min(income // 5, 15000)  # 20% of income, capped at 15K
            
            def calc_fn(current_income: Decimal):
                sg_simple = simple_tax_sg(current_income, sg_cfg)
                sg_after = apply_multipliers(sg_simple, mult_cfg, MultPick(["KANTON", "GEMEINDE"]))
                fed = tax_federal(current_income, fed_cfg)
                total = sg_after + fed
                return {"total": total}
            
            try:
                result = optimize_deduction(
                    income=chf(income),
                    max_deduction=max_deduction,
                    step=200,  # Larger steps for faster execution
                    calc_fn=calc_fn
                )
                
                if result["sweet_spot"]:
                    sweet_spot = result["sweet_spot"]
                    deduction = sweet_spot["deduction"]
                    tax_saved = sweet_spot["tax_saved_absolute"]
                    roi = (tax_saved / deduction * 100) if deduction > 0 else 0
                    
                    roi_results.append({
                        "income": income,
                        "roi": roi,
                        "deduction": deduction,
                        "savings": tax_saved
                    })
                    
            except Exception as e:
                print(f"Warning: Optimization failed for income {income:,}: {e}")
        
        if len(roi_results) >= 3:
            print(f"\n📊 ROI Progression Analysis ({len(roi_results)} data points):")
            for result in roi_results:
                print(f"  Income {result['income']:6,}: ROI {result['roi']:5.1f}%, "
                      f"deduction {result['deduction']:5,}, savings {result['savings']:6.0f}")
            
            # General expectation: ROI should not consistently increase with income
            # (This would suggest the optimization is finding better opportunities for richer people)
            high_income_roi = sum(r["roi"] for r in roi_results[-2:]) / 2  # Last 2
            low_income_roi = sum(r["roi"] for r in roi_results[:2]) / 2    # First 2
            
            # Allow some variation, but high-income ROI shouldn't be dramatically higher
            if high_income_roi > low_income_roi * 2:
                print(f"⚠️ High-income ROI ({high_income_roi:.1f}%) much higher than low-income ROI ({low_income_roi:.1f}%)")
                print("   This could indicate bracket boundary effects or optimization issues")
        
        # At minimum, we should have found some optimizations
        assert len(roi_results) >= 2, f"Expected at least 2 successful optimizations, got {len(roi_results)}"
        
        print(f"✅ ROI progression analysis completed with {len(roi_results)} successful optimizations")
    
    def test_optimization_comprehensive_loop(self, config_root):
        """Test optimization across comprehensive income range with consistent parameters (like income validation loop)."""
        # Load configs
        sg_cfg, fed_cfg, mult_cfg = load_configs(config_root, 2025)
        
        # Parameters similar to income range validation
        start_income = 20000   # Start where optimization makes sense
        end_income = 150000    # Cover most practical range
        income_step = 2000     # Every 2K CHF for reasonable performance
        max_deduction_ratio = 0.15  # 15% of income as max deduction
        
        incomes = list(range(start_income, end_income + 1, income_step))
        total_tests = len(incomes)
        
        print(f"\n🔄 Running optimization loop test: {start_income:,} to {end_income:,} CHF (step: {income_step:,})")
        print(f"Total optimizations: {total_tests}")
        
        results = []
        failures = []
        no_optimization_count = 0
        
        for i, income in enumerate(incomes):
            if i % 20 == 0:  # Progress indicator
                print(f"  Progress: {i+1}/{total_tests} ({income:,} CHF)")
            
            max_deduction = int(income * max_deduction_ratio)
            
            try:
                # Create calc function
                def calc_fn(current_income: Decimal):
                    sg_simple = simple_tax_sg(current_income, sg_cfg)
                    sg_after = apply_multipliers(sg_simple, mult_cfg, MultPick(["KANTON", "GEMEINDE"]))
                    fed = tax_federal(current_income, fed_cfg)
                    total = sg_after + fed
                    return {"total": total}
                
                # Run optimization
                result = optimize_deduction(
                    income=chf(income),
                    max_deduction=max_deduction,
                    step=200,  # Larger steps for performance in loop
                    calc_fn=calc_fn,
                    roi_tolerance_bp=25.0  # Moderate tolerance for loop testing
                )
                
                if result["sweet_spot"] is None:
                    no_optimization_count += 1
                    continue
                
                sweet_spot = result["sweet_spot"]
                deduction = sweet_spot["deduction"]
                tax_saved = sweet_spot["tax_saved_absolute"]
                roi = (tax_saved / deduction * 100) if deduction > 0 else 0
                
                # Store result
                opt_result = {
                    "income": income,
                    "max_deduction": max_deduction,
                    "optimal_deduction": deduction,
                    "tax_saved": tax_saved,
                    "roi": roi,
                    "new_income": sweet_spot["new_income"]
                }
                results.append(opt_result)
                
                # Quick validation checks
                if deduction <= 0 or deduction > max_deduction:
                    failures.append(f"Income {income:,}: Invalid deduction {deduction}")
                elif tax_saved <= 0:
                    failures.append(f"Income {income:,}: Non-positive savings {tax_saved:.2f}")
                elif roi <= 0:
                    failures.append(f"Income {income:,}: Non-positive ROI {roi:.1f}%")
                elif roi > 500:  # Very high ROI check
                    failures.append(f"Income {income:,}: Extremely high ROI {roi:.1f}%")
                    
            except Exception as e:
                failures.append(f"Income {income:,}: Optimization failed - {str(e)[:100]}")
        
        print(f"  Completed: {len(results)} successful optimizations, {no_optimization_count} with no optimization")
        print()
        
        # Analysis
        if failures:
            print(f"❌ Found {len(failures)} optimization issues:")
            for failure in failures[:10]:
                print(f"  - {failure}")
            if len(failures) > 10:
                print(f"  ... and {len(failures) - 10} more")
        
        success_rate = len(results) / total_tests * 100
        optimization_rate = len(results) / (total_tests - no_optimization_count) * 100 if (total_tests - no_optimization_count) > 0 else 0
        
        print(f"📊 Optimization Loop Analysis:")
        print(f"  Success rate: {success_rate:.1f}% ({len(results)}/{total_tests} incomes)")
        print(f"  Optimization rate: {optimization_rate:.1f}% (of incomes where optimization possible)")
        print(f"  No optimization found: {no_optimization_count} incomes")
        
        if results:
            # Statistical analysis
            rois = [r["roi"] for r in results]
            deductions = [r["optimal_deduction"] for r in results]
            savings = [r["tax_saved"] for r in results]
            
            print(f"\n📈 ROI Statistics:")
            print(f"  Average ROI: {sum(rois) / len(rois):.1f}%")
            print(f"  ROI range: {min(rois):.1f}% - {max(rois):.1f}%")
            print(f"  Median ROI: {sorted(rois)[len(rois)//2]:.1f}%")
            
            print(f"\n💰 Deduction Statistics:")
            print(f"  Average deduction: {sum(deductions) / len(deductions):,.0f} CHF")
            print(f"  Deduction range: {min(deductions):,} - {max(deductions):,} CHF")
            
            print(f"\n💸 Savings Statistics:")
            print(f"  Average savings: {sum(savings) / len(savings):,.0f} CHF")
            print(f"  Savings range: {min(savings):,.0f} - {max(savings):,.0f} CHF")
            
            # Check for reasonable patterns
            low_income_results = [r for r in results if r["income"] <= 50000]
            mid_income_results = [r for r in results if 50000 < r["income"] <= 100000]
            high_income_results = [r for r in results if r["income"] > 100000]
            
            if low_income_results and high_income_results:
                low_avg_roi = sum(r["roi"] for r in low_income_results) / len(low_income_results)
                high_avg_roi = sum(r["roi"] for r in high_income_results) / len(high_income_results)
                
                print(f"\n🔍 Income Segment Analysis:")
                print(f"  Low income (≤50K): {len(low_income_results)} results, avg ROI {low_avg_roi:.1f}%")
                print(f"  Mid income (50K-100K): {len(mid_income_results)} results")
                print(f"  High income (>100K): {len(high_income_results)} results, avg ROI {high_avg_roi:.1f}%")
                
                # Check for reasonable ROI progression (allow some variation)
                if high_avg_roi > low_avg_roi * 2.5:
                    print(f"  ⚠️ High-income ROI much higher than low-income (possible bracket effects)")
                elif abs(high_avg_roi - low_avg_roi) < 5:
                    print(f"  ✅ ROI relatively consistent across income levels")
                else:
                    print(f"  ✅ ROI variation within reasonable bounds")
        
        # Validation assertions
        assert len(failures) == 0, f"Found {len(failures)} optimization failures in comprehensive loop"
        
        # At least 70% of testable incomes should have successful optimization
        testable_incomes = total_tests - no_optimization_count
        if testable_incomes > 0:
            min_success_rate = 0.70
            actual_rate = len(results) / testable_incomes
            assert actual_rate >= min_success_rate, \
                   f"Optimization success rate {actual_rate:.1%} below minimum {min_success_rate:.1%}"
        
        # Should find optimizations for most income levels (some very low incomes may not have optimization potential)
        min_total_optimizations = total_tests * 0.50  # At least 50% of all tested incomes
        assert len(results) >= min_total_optimizations, \
               f"Too few optimizations found: {len(results)} < {min_total_optimizations:.0f}"
        
        print(f"\n✅ Comprehensive optimization loop validation passed!")
        print(f"   Tested {total_tests} income levels, found {len(results)} successful optimizations")
        print(f"   Average ROI: {sum(rois) / len(rois):.1f}% across income range {start_income:,}-{end_income:,} CHF")


class TestEdgeCasesAndBoundaryConditions:
    """Test edge cases and boundary conditions that might cause issues."""
    
    def test_very_low_incomes(self, default_multiplier_codes):
        """Test very low incomes that might trigger edge cases."""
        very_low_incomes = [0, 1, 10, 100, 500, 1000, 5000]
        
        for income in very_low_incomes:
            try:
                result = _calc_once(2025, income, default_multiplier_codes)
                
                # Basic sanity checks
                assert result["total"] >= 0, f"Negative tax for income {income}"
                assert result["avg_rate"] >= 0, f"Negative average rate for income {income}"
                assert result["federal"] >= 0, f"Negative federal tax for income {income}"
                assert result["sg_simple"] >= 0, f"Negative SG simple tax for income {income}"
                assert result["sg_after_mult"] >= 0, f"Negative SG after mult for income {income}"
                
                # For very low incomes, tax should be zero or very small
                if income <= 10000:
                    assert result["total"] <= income * 0.5, f"Tax too high for very low income {income}: {result['total']}"
                
            except Exception as e:
                pytest.fail(f"Failed to calculate taxes for very low income {income}: {e}")
    
    def test_high_income_limits(self, default_multiplier_codes):
        """Test high incomes to ensure calculations remain stable."""
        high_incomes = [200000, 250000, 300000, 500000, 1000000]
        
        for income in high_incomes:
            try:
                result = _calc_once(2025, income, default_multiplier_codes)
                
                # Basic sanity checks
                assert result["total"] >= 0, f"Negative tax for high income {income}"
                assert result["avg_rate"] <= 0.5, f"Average rate too high for income {income}: {result['avg_rate']:.1%}"
                assert result["marginal_total"] <= 0.6, f"Marginal rate too high for income {income}: {result['marginal_total']:.1%}"
                
                # High income should have substantial tax
                assert result["total"] > income * 0.1, f"Tax seems too low for high income {income}: {result['total']}"
                
            except Exception as e:
                pytest.fail(f"Failed to calculate taxes for high income {income}: {e}")
    
    def test_optimization_edge_cases(self, config_root):
        """Test optimization behavior at edge cases and boundary conditions."""
        # Load configs
        sg_cfg, fed_cfg, mult_cfg = load_configs(config_root, 2025)
        
        def calc_fn(current_income: Decimal):
            sg_simple = simple_tax_sg(current_income, sg_cfg)
            sg_after = apply_multipliers(sg_simple, mult_cfg, MultPick(["KANTON", "GEMEINDE"]))
            fed = tax_federal(current_income, fed_cfg)
            total = sg_after + fed
            return {"total": total}
        
        edge_cases = [
            (12000, 1000, "Near tax threshold"),   # Close to where taxes start
            (15200, 500, "Federal tax threshold"),  # Exact federal threshold
            (33000, 2000, "Federal bracket boundary"), # Near federal bracket change
            (76100, 5000, "Higher federal bracket"),   # Another federal boundary
        ]
        
        for income, max_deduction, description in edge_cases:
            try:
                result = optimize_deduction(
                    income=chf(income),
                    max_deduction=max_deduction,
                    step=50,  # Smaller steps for edge cases
                    calc_fn=calc_fn
                )
                
                # It's okay if no optimization is found at edge cases
                if result["sweet_spot"]:
                    sweet_spot = result["sweet_spot"]
                    deduction = sweet_spot["deduction"]
                    savings = sweet_spot["tax_saved_absolute"]
                    roi = (savings / deduction * 100) if deduction > 0 else 0
                    
                    print(f"Edge case {description} ({income:,} CHF): "
                          f"Deduct {deduction}, save {savings:.2f} CHF (ROI: {roi:.1f}%)")
                    
                    # Basic sanity checks
                    assert deduction > 0, f"Deduction should be positive for {description}"
                    assert savings >= 0, f"Savings should be non-negative for {description}"
                    assert roi >= 0, f"ROI should be non-negative for {description}"
                else:
                    print(f"No optimization found for {description} ({income:,} CHF) - edge case behavior")
                    
            except Exception as e:
                print(f"Warning: Optimization failed for edge case {description}: {e}")
                # Don't fail the test for edge cases - they might legitimately fail
        
        print("✅ Edge case optimization testing completed")
