from __future__ import annotations
from decimal import Decimal
from pathlib import Path
from typing import List, Optional, Dict, Any
import json
import csv
import typer
from rich import print as rprint

from .io.loader import load_configs, load_configs_with_filing_status
from .engine.stgallen import simple_tax_sg, sg_bracket_info, simple_tax_sg_with_filing_status
from .engine.federal import (
    tax_federal,
    federal_marginal_hundreds,
    federal_segment_info,
    tax_federal_with_filing_status,
)
from .engine.multipliers import apply_multipliers, MultPick
from .engine.models import chf, FilingStatus
from .engine.optimize import optimize_deduction, optimize_deduction_adaptive, validate_optimization_inputs
from .viz.curve import plot_curve

app = typer.Typer(help="Swiss tax CLI (SG + Federal), config driven")

CONFIG_ROOT = Path(__file__).resolve().parents[1] / "configs"


def _get_adaptive_tolerance_bp(income: int) -> float:
    """Return income-adaptive tolerance in basis points.
    
    Lower incomes have steeper ROI curves and benefit from precise optimization.
    Higher incomes have flatter ROI curves and need broader tolerance to find the true optimum.
    """
    if income < 50000:
        return 10.0  # 0.1% - precise for steep curves
    elif income < 80000:
        return 25.0  # 0.25% - moderate tolerance
    elif income < 120000:
        return 50.0  # 0.5% - broader for flatter curves
    else:
        return 100.0  # 1.0% - wide tolerance for very flat curves


def _print_optimization_result(result: dict, tolerance_bp: float, tolerance_source: str, base_income: int):
    """Print a clean, user-friendly optimization result."""
    from rich.console import Console
    from rich.panel import Panel
    from rich.text import Text
    
    console = Console()
    
    sweet_spot = result.get("sweet_spot")
    if not sweet_spot:
        console.print("❌ No optimization result found", style="red")
        return
    
    # Core recommendation
    deduction = sweet_spot["deduction"]
    tax_saved = sweet_spot["tax_saved_absolute"]
    roi = sweet_spot["optimization_summary"]["roi_percent"]
    new_income = sweet_spot["new_income"]
    
    # Create main result panel
    result_text = Text()
    result_text.append("💰 OPTIMAL DEDUCTION RECOMMENDATION\n\n", style="bold green")
    result_text.append(f"Deduct: {deduction:,} CHF\n", style="bold cyan")
    result_text.append(f"Tax savings: {tax_saved:,.0f} CHF\n", style="bold yellow")
    result_text.append(f"Return on investment: {roi:.1f}%\n", style="bold magenta")
    result_text.append(f"New taxable income: {new_income:,.0f} CHF", style="dim")
    
    # Add FEUER warning if present
    multipliers = sweet_spot.get("multipliers", {})
    feuer_warning = multipliers.get("feuer_warning")
    if feuer_warning:
        result_text.append(f"\n\n{feuer_warning}", style="yellow")
    
    console.print(Panel(result_text, title="TaxGlide Optimization", border_style="green"))
    
    # Show adaptive retry info if it was used
    adaptive_info = result.get("adaptive_retry_used")
    if adaptive_info:
        console.print(f"\n🔄 Enhanced with adaptive optimization (retried with {adaptive_info['chosen_tolerance_bp']:.0f}bp tolerance)", 
                     style="dim blue")
    
    # Concise technical details (optional)
    opt_summary = sweet_spot.get("optimization_summary", {})
    if opt_summary.get("plateau_width_chf"):
        console.print(f"\n📊 Technical: {opt_summary['plateau_width_chf']:,} CHF ROI plateau, "
                     f"{tolerance_bp:.0f}bp tolerance ({tolerance_source})", style="dim")


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


def _calc_once(year: int, income: int, picks: List[str], filing_status: FilingStatus = "single"):
    """Legacy function for backward compatibility. Uses same income for both SG and Federal."""
    return _calc_once_separate(year, income, income, picks, filing_status)


def _calc_once_separate(
    year: int, 
    sg_income: int, 
    fed_income: int, 
    picks: List[str], 
    filing_status: FilingStatus = "single"
):
    """Calculate taxes with separate SG and Federal taxable incomes.
    
    Args:
        year: Tax year
        sg_income: St. Gallen taxable income
        fed_income: Federal taxable income  
        picks: Multiplier codes to apply
        filing_status: Filing status ("single" or "married_joint")
        
    Returns:
        Dict with tax calculation results
    """
    sg_cfg, fed_cfg, mult_cfg = load_configs_with_filing_status(CONFIG_ROOT, year, filing_status)
    sg_income_d = chf(sg_income)
    fed_income_d = chf(fed_income)

    sg_simple = simple_tax_sg_with_filing_status(sg_income_d, sg_cfg, filing_status)
    sg_after = apply_multipliers(sg_simple, mult_cfg, MultPick(picks))
    fed = tax_federal_with_filing_status(fed_income_d, fed_cfg, filing_status)

    total = sg_after + fed
    
    # For average rate calculation, use the higher income as base (more conservative)
    base_income = max(sg_income_d, fed_income_d)
    avg_rate = float(total / base_income) if base_income > 0 else 0.0

    # Combined marginal via 1 CHF diff (finite difference) - check both incomes
    eps = Decimal(1)
    sg_marginal = apply_multipliers(
        simple_tax_sg_with_filing_status(sg_income_d + eps, sg_cfg, filing_status), 
        mult_cfg, 
        MultPick(picks)
    ) - sg_after
    fed_marginal = tax_federal_with_filing_status(fed_income_d + eps, fed_cfg, filing_status) - fed
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
        "filing_status": filing_status,
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
    filing_status: str = typer.Option("single", help="Filing status: single or married_joint"),
):
    """Compute federal + SG taxes and show breakdown.
    
    Use either:
      --income 80000                           (same income for both SG and Federal)
      --income-sg 78000 --income-fed 80000     (different incomes due to different deductions)
    
    Filing status:
      --filing-status single                   (default - individual filing)
      --filing-status married_joint            (married filing jointly - uses income splitting)
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

    res = _calc_once_separate(year, sg_income, fed_income, sorted(codes), filing_status)
    
    # Add FEUER warning if not selected (simplified)
    feuer_item = next((item for item in mult_cfg.items if item.code == 'FEUER'), None)
    if feuer_item and 'FEUER' not in codes:
        # Note: FEUER is typically calculated on the simple tax, which already includes filing status
        sg_simple_base = Decimal(str(res["sg_simple"]))  # already computed with filing status
        potential_feuer_tax = sg_simple_base * Decimal(str(feuer_item.rate))
        res["feuer_warning"] = f"⚠️ Missing FEUER tax: +{potential_feuer_tax:.0f} CHF (add --pick FEUER)"
    
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
    tolerance_bp: Optional[float] = typer.Option(None, help="Near-max ROI tolerance in basis points (auto-selected by income if not specified)"),
    filing_status: str = typer.Option("single", help="Filing status: single or married_joint"),
    disable_adaptive: bool = typer.Option(False, "--disable-adaptive", help="Disable adaptive multi-tolerance retry for low utilization"),
):
    """Find optimal deduction amounts with adaptive multi-tolerance optimization.
    
    Use either:
      --income 80000                           (same income for both SG and Federal)
      --income-sg 78000 --income-fed 80000     (different incomes due to different deductions)
    
    The optimizer automatically retries with different tolerance settings if low deduction
    utilization is detected (< 30% for incomes > 50K CHF), choosing the best ROI result.
    Use --disable-adaptive to use only the initial tolerance setting.
    
    Note: Optimization assumes the deduction applies equally to both SG and Federal incomes.
    """
    try:
        sg_income, fed_income = _resolve_incomes(income, income_sg, income_fed)
    except ValueError as e:
        rprint({"error": str(e)})
        raise typer.Exit(code=2)
    
    sg_cfg, fed_cfg, mult_cfg = load_configs_with_filing_status(CONFIG_ROOT, year, filing_status)
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
    
    # Determine tolerance: user-provided or income-adaptive
    if tolerance_bp is None:
        tolerance_bp = _get_adaptive_tolerance_bp(base_income)
        tolerance_source = "auto-selected"
    else:
        tolerance_source = "user-specified"

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
        
        sg_simple = simple_tax_sg_with_filing_status(current_sg, sg_cfg, filing_status)
        sg_after = apply_multipliers(sg_simple, mult_cfg, MultPick(codes))
        fed = tax_federal_with_filing_status(current_fed, fed_cfg, filing_status)
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

    # Use adaptive optimization by default, unless disabled
    if disable_adaptive:
        out = optimize_deduction(
            Decimal(base_income),  # Use higher income as baseline for optimization
            max_deduction,
            step,
            calc_fn,
            context_fn=context_fn,
            roi_tolerance_bp=tolerance_bp,
        )
    else:
        out = optimize_deduction_adaptive(
            Decimal(base_income),  # Use higher income as baseline for optimization
            max_deduction,
            step,
            calc_fn,
            context_fn=context_fn,
            initial_roi_tolerance_bp=tolerance_bp,
            enable_adaptive_retry=True,
        )

    # Enhance output with separate income information if applicable
    if out.get("sweet_spot") is not None:
        sweet_spot = out["sweet_spot"]
        deduction = sweet_spot["deduction"]
        
        # Calculate separate new incomes after deduction
        new_sg_income = sg_income - deduction
        new_fed_income = fed_income - deduction
        
        # Add income information (simplified)
        if sg_income != fed_income:
            sweet_spot["income_details"] = {
                "original_sg": sg_income,
                "original_fed": fed_income,
                "after_deduction_sg": float(new_sg_income),
                "after_deduction_fed": float(new_fed_income)
            }
        
        # Add concise multiplier info with FEUER warning if needed
        sweet_spot["multipliers"] = {
            "applied": sorted(codes),
            "total_rate": float(sum(Decimal(str(item.rate)) for item in mult_cfg.items if item.code in codes))
        }
        
        # Add FEUER warning if not selected (consolidated)
        feuer_item = next((item for item in mult_cfg.items if item.code == 'FEUER'), None)
        if feuer_item and 'FEUER' not in codes:
            current_sg = max(sg_income_decimal - Decimal(deduction), Decimal(0))
            sg_simple_at_spot = simple_tax_sg_with_filing_status(current_sg, sg_cfg, filing_status)
            potential_feuer_tax = float(sg_simple_at_spot * Decimal(str(feuer_item.rate)))
            sweet_spot["multipliers"]["feuer_warning"] = f"⚠️ Missing FEUER tax: +{potential_feuer_tax:.0f} CHF (add --pick FEUER)"
        
        if sg_income == fed_income:
            # Legacy single income case - keep simple output
            sweet_spot["new_income"] = float(new_sg_income)  # Same for both
        else:
            # Separate income case - new_income for compatibility, details in income_details
            sweet_spot["new_income"] = float(max(new_sg_income, new_fed_income))

    # prettify Decimals for JSON friendliness
    def coerce(d):
        from decimal import Decimal
        if isinstance(d, Decimal):
            return float(d)
        elif isinstance(d, dict):
            return {k: coerce(v) for k, v in d.items()}
        elif isinstance(d, list):
            return [coerce(x) for x in d]
        return d

    # Add basic multiplier info at top level
    out["multipliers_applied"] = sorted(codes)
    
    # Simplify output by hiding overly verbose sections
    if out.get("sweet_spot") and "why" in out["sweet_spot"]:
        why = out["sweet_spot"]["why"]
        # Keep only essential info
        simplified_why = {
            "roi_percent": why.get("roi_at_spot_percent"),
            "plateau_width_chf": why.get("plateau_width_chf"),
            "federal_bracket_changed": why.get("federal_bracket_changed"),
            "marginal_rate_percent": why.get("local_marginal_percent_at_spot")
        }
        # Add notes if they exist
        if why.get("notes"):
            simplified_why["notes"] = why["notes"]
            
        out["sweet_spot"]["optimization_summary"] = simplified_why
        # Remove verbose why section
        del out["sweet_spot"]["why"]
        
    # Remove redundant marginal info at top level (it's in optimization_summary now)
    out.pop("local_marginal_percent_at_best", None)
    out.pop("local_marginal_percent_at_spot", None)
    
    out = {k: coerce(v) for k, v in out.items()}
    
    if json_out:
        # Full detailed JSON output for programmatic use
        tolerance_explanation = {
            "tolerance_used_bp": tolerance_bp,
            "tolerance_percent": tolerance_bp / 100.0,
            "tolerance_source": tolerance_source,
            "explanation": f"Tolerance {tolerance_bp:.1f} basis points ({tolerance_bp/100:.2f}%) {tolerance_source} based on income {base_income:,} CHF. "
                          f"This sets how close to the maximum ROI a deduction must be to be considered 'near-optimal'. "
                          f"Higher incomes use wider tolerances because ROI curves are flatter at higher tax brackets."
        }
        out["tolerance_info"] = tolerance_explanation
        print(json.dumps(out, indent=2))
    else:
        # Clean, user-friendly output for terminal use
        _print_optimization_result(out, tolerance_bp, tolerance_source, base_income)


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
    filing_status: str = typer.Option("single", help="Filing status: single or married_joint"),
):
    """
    Plot the tax curve. If --annotate-sweet-spot is set (and opt_* provided),
    the figure will show a shaded plateau and a vertical line at the sweet spot.
    """
    sg_cfg, fed_cfg, mult_cfg = load_configs_with_filing_status(CONFIG_ROOT, year, filing_status)
    default_picks = [i.code for i in mult_cfg.items if i.default_selected]
    codes = set(default_picks) | set(pick)
    codes -= set(skip)
    picks_sorted = sorted(codes)

    # Build curve
    pts = []
    for x in range(min, max + 1, step):
        # small inline compute (no optimizer), same logic as _calc_once
        inc_d = chf(x)
        sg_simple = simple_tax_sg_with_filing_status(inc_d, sg_cfg, filing_status)
        sg_after = apply_multipliers(sg_simple, mult_cfg, MultPick(picks_sorted))
        fed = tax_federal_with_filing_status(inc_d, fed_cfg, filing_status)
        total = sg_after + fed
        pts.append((x, total))

    annotations: Optional[Dict[str, Any]] = None

    if annotate_sweet_spot and (opt_income is not None) and (opt_max_deduction is not None):
        # Optimizer setup mirrors the optimize command
        def calc_fn(inc: Decimal):
            sg_simple = simple_tax_sg_with_filing_status(inc, sg_cfg, filing_status)
            sg_after = apply_multipliers(sg_simple, mult_cfg, MultPick(picks_sorted))
            fed = tax_federal_with_filing_status(inc, fed_cfg, filing_status)
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
                sg_simple = simple_tax_sg_with_filing_status(t_inc_d, sg_cfg, filing_status)
                sg_after = apply_multipliers(sg_simple, mult_cfg, MultPick(picks_sorted))
                fed = tax_federal_with_filing_status(t_inc_d, fed_cfg, filing_status)
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
    filing_status: str = typer.Option("single", help="Filing status: single or married_joint"),
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
        
    sg_cfg, fed_cfg, mult_cfg = load_configs_with_filing_status(CONFIG_ROOT, year, filing_status)
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
        sg_simple = simple_tax_sg_with_filing_status(sg_inc, sg_cfg, filing_status)
        sg_after = apply_multipliers(sg_simple, mult_cfg, MultPick(picks_sorted))
        fed = tax_federal_with_filing_status(fed_inc, fed_cfg, filing_status)
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
    filing_status: str = typer.Option("single", help="Filing status: single or married_joint"),
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
        
    sg_cfg, fed_cfg, mult_cfg = load_configs_with_filing_status(CONFIG_ROOT, year, filing_status)
    
    # Original incomes
    original_sg_income = chf(sg_income)
    original_fed_income = chf(fed_income)
    
    # Adjusted incomes (after deduction)
    adjusted_sg_income = chf(max(0, sg_income - deduction))
    adjusted_fed_income = chf(max(0, fed_income - deduction))

    
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
