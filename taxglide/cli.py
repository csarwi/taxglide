from __future__ import annotations
from decimal import Decimal
from pathlib import Path
from typing import List, Optional, Dict, Any
import json
import csv
import typer
from rich import print as rprint

from .io.loader import load_configs
from .engine.stgallen import simple_tax_sg, sg_bracket_info
from .engine.federal import (
    tax_federal,
    federal_marginal_hundreds,
    federal_segment_info,
)
from .engine.multipliers import apply_multipliers, MultPick
from .engine.models import chf
from .engine.optimize import optimize_deduction, validate_optimization_inputs
from .viz.curve import plot_curve

app = typer.Typer(help="Swiss tax CLI (SG + Federal), config driven")

CONFIG_ROOT = Path(__file__).resolve().parents[1] / "configs"


def _resolve_incomes(
    income: Optional[int] = None,
    income_sg: Optional[int] = None, 
    income_fed: Optional[int] = None
) -> tuple[int, int]:
    """Resolve income parameters to (sg_income, fed_income) tuple.
    
    Args:
        income: Single income for both SG and Federal (backward compatibility)
        income_sg: Specific SG taxable income
        income_fed: Specific Federal taxable income
        
    Returns:
        (sg_income, fed_income) tuple
        
    Raises:
        ValueError: If invalid combination of parameters provided
    """
    # Scenario 1: Traditional single income (backward compatible)
    if income is not None and income_sg is None and income_fed is None:
        return (income, income)
    
    # Scenario 2: Separate SG and Federal incomes
    if income is None and income_sg is not None and income_fed is not None:
        return (income_sg, income_fed)
    
    # Invalid scenarios
    if income is not None and (income_sg is not None or income_fed is not None):
        raise ValueError(
            "Cannot specify both --income and --income-sg/--income-fed. "
            "Use either --income alone, or both --income-sg and --income-fed together."
        )
    
    if (income_sg is None) != (income_fed is None):  # XOR - only one is provided
        raise ValueError(
            "When using separate incomes, both --income-sg and --income-fed must be provided."
        )
    
    raise ValueError(
        "Must provide either --income, or both --income-sg and --income-fed."
    )


def _calc_once(year: int, income: int, picks: List[str]):
    """Legacy function for backward compatibility. Uses same income for both SG and Federal."""
    return _calc_once_separate(year, income, income, picks)


def _calc_once_separate(year: int, sg_income: int, fed_income: int, picks: List[str]):
    """Calculate taxes with separate SG and Federal taxable incomes.
    
    Args:
        year: Tax year
        sg_income: St. Gallen taxable income
        fed_income: Federal taxable income  
        picks: Multiplier codes to apply
        
    Returns:
        Dict with tax calculation results
    """
    sg_cfg, fed_cfg, mult_cfg = load_configs(CONFIG_ROOT, year)
    sg_income_d = chf(sg_income)
    fed_income_d = chf(fed_income)

    sg_simple = simple_tax_sg(sg_income_d, sg_cfg)
    sg_after = apply_multipliers(sg_simple, mult_cfg, MultPick(picks))
    fed = tax_federal(fed_income_d, fed_cfg)

    total = sg_after + fed
    
    # For average rate calculation, use the higher income as base (more conservative)
    base_income = max(sg_income_d, fed_income_d)
    avg_rate = float(total / base_income) if base_income > 0 else 0.0

    # Combined marginal via 1 CHF diff (finite difference) - check both incomes
    eps = Decimal(1)
    sg_marginal = apply_multipliers(simple_tax_sg(sg_income_d + eps, sg_cfg), mult_cfg, MultPick(picks)) - sg_after
    fed_marginal = tax_federal(fed_income_d + eps, fed_cfg) - fed
    marginal_total = float(sg_marginal + fed_marginal) / 1.0

    m_fed_h = federal_marginal_hundreds(fed_income_d, fed_cfg)

    return {
        "income_sg": sg_income,
        "income_fed": fed_income,
        "income": sg_income if sg_income == fed_income else None,  # For backward compatibility
        "federal": float(fed),
        "sg_simple": float(sg_simple),
        "sg_after_mult": float(sg_after),
        "total": float(total),
        "avg_rate": avg_rate,
        "marginal_total": marginal_total,
        "marginal_federal_hundreds": m_fed_h,
        "picks": picks,
    }


@app.command()
def calc(
    year: int = typer.Option(..., help="Tax year, e.g., 2025"),
    income: Optional[int] = typer.Option(None, help="Taxable income for both SG and Federal (CHF)"),
    income_sg: Optional[int] = typer.Option(None, help="St. Gallen taxable income (CHF)"),
    income_fed: Optional[int] = typer.Option(None, help="Federal taxable income (CHF)"),
    pick: List[str] = typer.Option([], help="Codes to pick"),
    skip: List[str] = typer.Option([], help="Codes to skip (overrides defaults)"),
    json_out: bool = typer.Option(False, "--json", help="Output JSON"),
):
    """Compute federal + SG taxes and show breakdown.
    
    Use either:
      --income 80000                           (same income for both SG and Federal)
      --income-sg 78000 --income-fed 80000     (different incomes due to different deductions)
    """
    try:
        sg_income, fed_income = _resolve_incomes(income, income_sg, income_fed)
    except ValueError as e:
        rprint({"error": str(e)})
        raise typer.Exit(code=2)
    
    # auto-pick defaults
    _, _, mult_cfg = load_configs(CONFIG_ROOT, year)
    default_picks = [i.code for i in mult_cfg.items if i.default_selected]
    codes = set(default_picks) | set(pick)
    codes -= set(skip)

    res = _calc_once_separate(year, sg_income, fed_income, sorted(codes))
    
    # Add FEUER warning if not selected
    feuer_selected = 'FEUER' in codes
    feuer_item = None
    for item in mult_cfg.items:
        if item.code == 'FEUER':
            feuer_item = item
            break
    
    if feuer_item and not feuer_selected:
        # Calculate potential FEUER tax
        sg_simple = res["sg_after_mult"] / sum(item.rate for item in mult_cfg.items if item.code in codes)
        potential_feuer_tax = sg_simple * feuer_item.rate
        res["feuer_warning"] = {
            "message": "⚠️  This might not be the whole picture - Feuerwehr tax might apply if you're not exempt from fire service taxes.",
            "potential_feuer_tax": float(potential_feuer_tax),
            "rate": float(feuer_item.rate),
            "note": f"Add --pick FEUER to include {potential_feuer_tax:.2f} CHF fire service tax in calculations."
        }
    
    if json_out:
        print(json.dumps(res, indent=2))
    else:
        rprint(res)


@app.command()
def optimize(
    year: int = typer.Option(...),
    income: Optional[int] = typer.Option(None, help="Taxable income for both SG and Federal (CHF)"),
    income_sg: Optional[int] = typer.Option(None, help="St. Gallen taxable income (CHF)"),
    income_fed: Optional[int] = typer.Option(None, help="Federal taxable income (CHF)"),
    max_deduction: int = typer.Option(...),
    step: int = typer.Option(100, help="Deduction step (CHF)"),
    pick: List[str] = typer.Option([], help="Codes to pick"),
    skip: List[str] = typer.Option([], help="Codes to skip"),
    json_out: bool = typer.Option(False, "--json"),
    tolerance_bp: float = typer.Option(10.0, help="Near-max ROI tolerance in basis points"),
):
    """Find optimal deduction amounts.
    
    Use either:
      --income 80000                           (same income for both SG and Federal)
      --income-sg 78000 --income-fed 80000     (different incomes due to different deductions)
    
    Note: Optimization assumes the deduction applies equally to both SG and Federal incomes.
    """
    try:
        sg_income, fed_income = _resolve_incomes(income, income_sg, income_fed)
    except ValueError as e:
        rprint({"error": str(e)})
        raise typer.Exit(code=2)
    
    sg_cfg, fed_cfg, mult_cfg = load_configs(CONFIG_ROOT, year)
    default_picks = [i.code for i in mult_cfg.items if i.default_selected]
    codes = set(default_picks) | set(pick)
    codes -= set(skip)

    # Early validation for clearer CLI errors - use the higher income for validation
    base_income = max(sg_income, fed_income)
    try:
        validate_optimization_inputs(Decimal(base_income), max_deduction, 1, step)
    except ValueError as e:
        rprint({"error": str(e)})
        raise typer.Exit(code=2)

    # Store original incomes for reference
    sg_income_decimal = Decimal(sg_income)
    fed_income_decimal = Decimal(fed_income)
    
    def calc_fn(current_income: Decimal):
        # Calculate how much was deducted from the base income
        deduction_amount = Decimal(base_income) - current_income
        
        # Apply same deduction to both SG and Federal incomes
        current_sg = sg_income_decimal - deduction_amount
        current_fed = fed_income_decimal - deduction_amount
        
        # Ensure incomes don't go negative
        current_sg = max(current_sg, Decimal(0))
        current_fed = max(current_fed, Decimal(0))
        
        sg_simple = simple_tax_sg(current_sg, sg_cfg)
        sg_after = apply_multipliers(sg_simple, mult_cfg, MultPick(codes))
        fed = tax_federal(current_fed, fed_cfg)
        total = sg_after + fed
        return {"total": total, "federal": fed}

    # Provide a context function so optimizer can narrate federal bracket before/after
    def context_fn(current_income: Decimal):
        deduction_amount = Decimal(base_income) - current_income
        current_sg = max(sg_income_decimal - deduction_amount, Decimal(0))
        current_fed = max(fed_income_decimal - deduction_amount, Decimal(0))
        return {
            "federal_segment": federal_segment_info(current_fed, fed_cfg),
            "sg_bracket": sg_bracket_info(current_sg, sg_cfg),
        }

    out = optimize_deduction(
        Decimal(base_income),  # Use higher income as baseline for optimization
        max_deduction,
        step,
        calc_fn,
        context_fn=context_fn,
        roi_tolerance_bp=tolerance_bp,
    )

    # Enhance output with separate income information if applicable
    if out.get("sweet_spot") is not None:
        sweet_spot = out["sweet_spot"]
        deduction = sweet_spot["deduction"]
        
        # Calculate separate new incomes after deduction
        new_sg_income = sg_income - deduction
        new_fed_income = fed_income - deduction
        
        # Add detailed income information
        sweet_spot["original_incomes"] = {
            "sg_income": sg_income,
            "fed_income": fed_income,
            "same_income_used": sg_income == fed_income
        }
        
        # Add multiplier information
        sweet_spot["picks"] = sorted(codes)
        
        # Calculate multiplier breakdown at sweet spot if useful
        current_sg = max(sg_income_decimal - Decimal(deduction), Decimal(0))
        sg_simple_at_spot = simple_tax_sg(current_sg, sg_cfg)
        
        multiplier_breakdown = {}
        total_multiplier = Decimal(0)
        for item in mult_cfg.items:
            if item.code in codes:
                rate_decimal = Decimal(str(item.rate))
                multiplier_breakdown[item.code] = {
                    "name": item.name,
                    "rate": float(item.rate),
                    "tax_amount": float(sg_simple_at_spot * rate_decimal)
                }
                total_multiplier += rate_decimal
        
        sweet_spot["multiplier_details"] = {
            "sg_simple_tax": float(sg_simple_at_spot),
            "total_multiplier": float(total_multiplier),
            "breakdown": multiplier_breakdown
        }
        
        # Add FEUER warning and amount if not selected
        feuer_selected = 'FEUER' in codes
        feuer_item = None
        for item in mult_cfg.items:
            if item.code == 'FEUER':
                feuer_item = item
                break
        
        if feuer_item and not feuer_selected:
            potential_feuer_tax = float(sg_simple_at_spot * Decimal(str(feuer_item.rate)))
            sweet_spot["feuer_warning"] = {
                "message": "⚠️  This might not be the whole picture - Feuerwehr tax might apply if you're not exempt from fire service taxes.",
                "potential_feuer_tax": potential_feuer_tax,
                "rate": float(feuer_item.rate),
                "note": f"Add --pick FEUER to include {potential_feuer_tax:.2f} CHF fire service tax in calculations."
            }
        
        if sg_income == fed_income:
            # Legacy single income case - keep simple output
            sweet_spot["new_income"] = float(new_sg_income)  # Same for both
        else:
            # Separate income case - show both new incomes
            sweet_spot["new_income_sg"] = float(new_sg_income)
            sweet_spot["new_income_fed"] = float(new_fed_income)
            # Keep the single value for backward compatibility (use higher income)
            sweet_spot["new_income"] = float(max(new_sg_income, new_fed_income))

    # prettify Decimals for JSON friendliness
    def coerce(d):
        if isinstance(d, dict):
            return {k: float(v) if hasattr(v, "quantize") else coerce(v) for k, v in d.items()}
        if isinstance(d, list):
            return [coerce(x) for x in d]
        return d

    # Add multiplier information to the base output
    out["multiplier_picks"] = sorted(codes)
    
    # Add FEUER warning at top level if not selected
    feuer_selected = 'FEUER' in codes
    feuer_item = None
    for item in mult_cfg.items:
        if item.code == 'FEUER':
            feuer_item = item
            break
    
    if feuer_item and not feuer_selected:
        # Calculate potential FEUER tax at base income
        sg_simple_base = simple_tax_sg(sg_income_decimal, sg_cfg)
        potential_feuer_tax_base = float(sg_simple_base * Decimal(str(feuer_item.rate)))
        out["feuer_warning"] = {
            "message": "⚠️  This might not be the whole picture - Feuerwehr tax might apply if you're not exempt from fire service taxes.",
            "potential_feuer_tax_at_base_income": potential_feuer_tax_base,
            "rate": float(feuer_item.rate),
            "note": f"Add --pick FEUER to include approximately {potential_feuer_tax_base:.0f} CHF fire service tax in calculations."
        }
    
    out = {k: coerce(v) for k, v in out.items()}

    if json_out:
        print(json.dumps(out, indent=2))
    else:
        rprint(out)


@app.command()
def plot(
    year: int = typer.Option(...),
    min: int = typer.Option(..., help="Min income"),
    max: int = typer.Option(..., help="Max income"),
    step: int = typer.Option(100),
    pick: List[str] = typer.Option([], help="Codes to pick"),
    skip: List[str] = typer.Option([], help="Codes to skip"),
    out: str = typer.Option("curve.png"),
    # New: optionally annotate with a sweet spot for a given optimization case
    annotate_sweet_spot: bool = typer.Option(False, help="Annotate the plot with a sweet spot/plateau"),
    opt_income: Optional[int] = typer.Option(None, help="Income used for sweet-spot optimization"),
    opt_max_deduction: Optional[int] = typer.Option(None, help="Max deduction for optimization"),
    opt_step: int = typer.Option(100, help="Deduction step for optimization"),
    opt_tolerance_bp: float = typer.Option(10.0, help="Tolerance (bp) used for plateau and sweet spot"),
):
    """
    Plot the tax curve. If --annotate-sweet-spot is set (and opt_* provided),
    the figure will show a shaded plateau and a vertical line at the sweet spot.
    """
    sg_cfg, fed_cfg, mult_cfg = load_configs(CONFIG_ROOT, year)
    default_picks = [i.code for i in mult_cfg.items if i.default_selected]
    codes = set(default_picks) | set(pick)
    codes -= set(skip)
    picks_sorted = sorted(codes)

    # Build curve
    pts = []
    for x in range(min, max + 1, step):
        # small inline compute (no optimizer), same logic as _calc_once
        inc_d = chf(x)
        sg_simple = simple_tax_sg(inc_d, sg_cfg)
        sg_after = apply_multipliers(sg_simple, mult_cfg, MultPick(picks_sorted))
        fed = tax_federal(inc_d, fed_cfg)
        total = sg_after + fed
        pts.append((x, total))

    annotations: Optional[Dict[str, Any]] = None

    if annotate_sweet_spot and (opt_income is not None) and (opt_max_deduction is not None):
        # Optimizer setup mirrors the optimize command
        def calc_fn(inc: Decimal):
            sg_simple = simple_tax_sg(inc, sg_cfg)
            sg_after = apply_multipliers(sg_simple, mult_cfg, MultPick(picks_sorted))
            fed = tax_federal(inc, fed_cfg)
            total = sg_after + fed
            return {"total": total, "federal": fed}

        # safety: reuse validate
        try:
            validate_optimization_inputs(Decimal(opt_income), int(opt_max_deduction), 1, opt_step)
        except ValueError as e:
            rprint({"warning": f"Cannot annotate sweet spot: {e}"})
            annotations = None
        else:
            res = optimize_deduction(
                Decimal(opt_income),
                int(opt_max_deduction),
                opt_step,
                calc_fn,
                roi_tolerance_bp=opt_tolerance_bp,
            )
            sweet = res.get("sweet_spot")
            plateau = res.get("plateau_near_max_roi")

            if sweet and plateau:
                d_spot = int(sweet["deduction"])
                sweet_income = float(opt_income - d_spot)

                # compute total at sweet spot income to place the marker nicely
                t_inc_d = chf(sweet_income)
                sg_simple = simple_tax_sg(t_inc_d, sg_cfg)
                sg_after = apply_multipliers(sg_simple, mult_cfg, MultPick(picks_sorted))
                fed = tax_federal(t_inc_d, fed_cfg)
                sweet_total = float(sg_after + fed)

                # plateau band in income space
                d_min = int(plateau["min_d"])
                d_max = int(plateau["max_d"])
                annotations = {
                    "sweet_spot_income": sweet_income,
                    "sweet_spot_total": sweet_total,
                    "plateau_income_min": float(opt_income - d_max),
                    "plateau_income_max": float(opt_income - d_min),
                    "label": f"Sweet spot (deduct {d_spot} CHF)",
                }
            else:
                rprint({"info": "No sweet spot/plateau found to annotate."})

    plot_curve(pts, out, annotations=annotations)
    rprint({"saved": out, "annotated": bool(annotations)})


@app.command()
def scan(
    year: int = typer.Option(..., help="Tax year (e.g., 2025)"),
    income: Optional[int] = typer.Option(None, help="Original taxable income for both SG and Federal (CHF)"),
    income_sg: Optional[int] = typer.Option(None, help="St. Gallen taxable income (CHF)"),
    income_fed: Optional[int] = typer.Option(None, help="Federal taxable income (CHF)"),
    max_deduction: int = typer.Option(..., help="Max deduction to explore (CHF)"),
    d_step: int = typer.Option(100, help="Deduction increment (CHF)"),
    pick: List[str] = typer.Option([], help="Codes to pick (multipliers)"),
    skip: List[str] = typer.Option([], help="Codes to skip (multipliers)"),
    out: str = typer.Option("scan.csv", help="Output CSV path"),
    json_out: bool = typer.Option(False, "--json", help="Print JSON instead of writing CSV"),
    include_local_marginal: bool = typer.Option(True, help="Compute local marginal % using Δ100"),
):
    """
    Produce a dense table of values for deductions d = 0..max_deduction (step=d_step):
      - d, new_income
      - total tax, saved, ROI (%)
      - SG simple, SG after multipliers, Federal
      - federal segment (from/to/per100) for each new_income
      - local marginal percent (Δ100) around each new_income (optional)
    
    Use either:
      --income 80000                           (same income for both SG and Federal)
      --income-sg 78000 --income-fed 80000     (different incomes due to different deductions)
    """
    try:
        sg_income, fed_income = _resolve_incomes(income, income_sg, income_fed)
    except ValueError as e:
        rprint({"error": str(e)})
        raise typer.Exit(code=2)
        
    sg_cfg, fed_cfg, mult_cfg = load_configs(CONFIG_ROOT, year)
    default_picks = [i.code for i in mult_cfg.items if i.default_selected]
    codes = set(default_picks) | set(pick)
    codes -= set(skip)
    picks_sorted = sorted(codes)

    # Validate bounds using higher income
    base_income = max(sg_income, fed_income)
    try:
        validate_optimization_inputs(Decimal(base_income), max_deduction, 0, max(1, d_step))
    except ValueError as e:
        rprint({"error": str(e)})
        raise typer.Exit(code=2)

    # Helper to compute totals with separate SG and Federal incomes
    def calc_all(sg_inc: Decimal, fed_inc: Decimal):
        sg_simple = simple_tax_sg(sg_inc, sg_cfg)
        sg_after = apply_multipliers(sg_simple, mult_cfg, MultPick(picks_sorted))
        fed = tax_federal(fed_inc, fed_cfg)
        total = sg_after + fed
        return sg_simple, sg_after, fed, total

    SG0 = Decimal(sg_income)
    FED0 = Decimal(fed_income)
    _, _, _, T0 = calc_all(SG0, FED0)

    rows: List[Dict[str, Any]] = []
    eps = Decimal(100)

    for d in range(0, max_deduction + 1, max(1, d_step)):
        sg_y = SG0 - Decimal(d)
        fed_y = FED0 - Decimal(d)
        
        # Ensure incomes don't go negative
        sg_y = max(sg_y, Decimal(0))
        fed_y = max(fed_y, Decimal(0))

        sg_simple, sg_after, fed, total = calc_all(sg_y, fed_y)
        saved = T0 - total
        roi = (saved / Decimal(d)) if d > 0 else Decimal(0)
        roi_pct = float(roi * 100) if d > 0 else 0.0

        # federal segment info at current federal income
        fseg = federal_segment_info(fed_y, fed_cfg)

        # local marginal around current incomes (Δ100) if requested and feasible
        local_marginal_pct = None
        if include_local_marginal:
            if sg_y >= eps and fed_y >= eps:
                _, _, _, t_hi = calc_all(sg_y, fed_y)
                _, _, _, t_lo = calc_all(sg_y - eps, fed_y - eps)
                local_marginal_pct = float((t_hi - t_lo) / eps * 100)
            else:
                local_marginal_pct = float(0.0)

        row_data = {
            "deduction": d,
            "new_income": float(max(sg_y, fed_y)),  # Keep for backward compatibility
            "total_tax": float(total),
            "saved": float(saved),
            "roi_percent": roi_pct,
            "sg_simple": float(sg_simple),
            "sg_after_multipliers": float(sg_after),
            "federal": float(fed),
            "federal_from": fseg["from"],
            "federal_to": fseg["to"] if fseg["to"] is not None else None,
            "federal_per100": fseg["per100"],
            "local_marginal_percent": local_marginal_pct,
        }
        
        # Add separate income details if different incomes were used
        if sg_income != fed_income:
            row_data["new_income_sg"] = float(sg_y)
            row_data["new_income_fed"] = float(fed_y)
            
        rows.append(row_data)

    if json_out:
        print(json.dumps(rows, indent=2))
        return

    # write CSV
    out_path = Path(out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Build fieldnames dynamically to include separate income fields when applicable
    if rows:
        fieldnames = list(rows[0].keys())
    else:
        fieldnames = [
            "deduction","new_income","total_tax","saved","roi_percent",
            "sg_simple","sg_after_multipliers","federal",
            "federal_from","federal_to","federal_per100","local_marginal_percent"
        ]
        # Add separate income fields if different incomes were used
        if sg_income != fed_income:
            fieldnames.insert(2, "new_income_sg")  # Insert after new_income
            fieldnames.insert(3, "new_income_fed")
    with out_path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(rows)
    rprint({"saved": str(out_path), "rows": len(rows)})

@app.command()
def validate(
    year: int = typer.Option(..., help="Tax year to validate"),
):
    """Validate configuration files for given year."""
    try:
        sg_cfg, fed_cfg, mult_cfg = load_configs(CONFIG_ROOT, year)
        rprint({"status": "valid", "year": year, "message": "All configurations valid"})
    except Exception as e:
        rprint({"status": "invalid", "year": year, "error": str(e)})
        raise typer.Exit(code=1)

@app.command() 
def compare_brackets(
    year: int = typer.Option(...),
    income: Optional[int] = typer.Option(None, help="Taxable income for both SG and Federal (CHF)"),
    income_sg: Optional[int] = typer.Option(None, help="St. Gallen taxable income (CHF)"),
    income_fed: Optional[int] = typer.Option(None, help="Federal taxable income (CHF)"),
    deduction: int = typer.Option(0, "--deduction", help="Amount to deduct"),
):
    """Show which tax brackets apply before/after deduction.
    
    Use either:
      --income 80000                           (same income for both SG and Federal)
      --income-sg 78000 --income-fed 80000     (different incomes due to different deductions)
    """
    try:
        sg_income, fed_income = _resolve_incomes(income, income_sg, income_fed)
    except ValueError as e:
        rprint({"error": str(e)})
        raise typer.Exit(code=2)
        
    sg_cfg, fed_cfg, mult_cfg = load_configs(CONFIG_ROOT, year)
    
    # Original incomes
    original_sg_income = chf(sg_income)
    original_fed_income = chf(fed_income)
    
    # Adjusted incomes (after deduction)
    adjusted_sg_income = chf(sg_income - deduction)
    adjusted_fed_income = chf(fed_income - deduction)
    
    # Federal bracket info
    fed_before = federal_segment_info(original_fed_income, fed_cfg)
    fed_after = federal_segment_info(adjusted_fed_income, fed_cfg)
    # SG bracket info
    sg_before = sg_bracket_info(original_sg_income, sg_cfg)
    sg_after = sg_bracket_info(adjusted_sg_income, sg_cfg)
    
    rprint({
        "original_sg_income": sg_income,
        "original_fed_income": fed_income,
        "adjusted_sg_income": float(adjusted_sg_income),
        "adjusted_fed_income": float(adjusted_fed_income),
        "deduction_amount": deduction,
        "federal_bracket_before": fed_before,
        "federal_bracket_after": fed_after,
        "federal_bracket_changed": fed_before != fed_after,
        "sg_bracket_before": sg_before,
        "sg_bracket_after": sg_after,
        "sg_bracket_changed": sg_before != sg_after,
    })
