from __future__ import annotations
from decimal import Decimal
from pathlib import Path
from typing import List, Optional, Dict, Any
import json
import csv
import typer
from rich import print as rprint

from .io.loader import load_configs
from .engine.stgallen import simple_tax_sg
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


def _calc_once(year: int, income: int, picks: List[str]):
    sg_cfg, fed_cfg, mult_cfg = load_configs(CONFIG_ROOT, year)
    income_d = chf(income)

    sg_simple = simple_tax_sg(income_d, sg_cfg)
    sg_after = apply_multipliers(sg_simple, mult_cfg, MultPick(picks))
    fed = tax_federal(income_d, fed_cfg)

    total = sg_after + fed
    avg_rate = float(total / income_d) if income_d > 0 else 0.0

    # combined marginal via 1 CHF diff (finite difference)
    eps = Decimal(1)
    total_plus = apply_multipliers(simple_tax_sg(income_d + eps, sg_cfg), mult_cfg, MultPick(picks)) + tax_federal(income_d + eps, fed_cfg)
    marginal_total = float(total_plus - total) / 1.0

    m_fed_h = federal_marginal_hundreds(income_d, fed_cfg)

    return {
        "income": income,
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
    income: int = typer.Option(..., help="Taxable income (CHF)"),
    pick: List[str] = typer.Option([], help="Codes to pick"),
    skip: List[str] = typer.Option([], help="Codes to skip (overrides defaults)"),
    json_out: bool = typer.Option(False, "--json", help="Output JSON"),
):
    """Compute federal + SG taxes and show breakdown."""
    # auto-pick defaults
    _, _, mult_cfg = load_configs(CONFIG_ROOT, year)
    default_picks = [i.code for i in mult_cfg.items if i.default_selected]
    codes = set(default_picks) | set(pick)
    codes -= set(skip)

    res = _calc_once(year, income, sorted(codes))
    if json_out:
        print(json.dumps(res, indent=2))
    else:
        rprint(res)


@app.command()
def optimize(
    year: int = typer.Option(...),
    income: int = typer.Option(...),
    max_deduction: int = typer.Option(...),
    step: int = typer.Option(100, help="Deduction step (CHF)"),
    pick: List[str] = typer.Option([], help="Codes to pick"),
    skip: List[str] = typer.Option([], help="Codes to skip"),
    json_out: bool = typer.Option(False, "--json"),
    tolerance_bp: float = typer.Option(10.0, help="Near-max ROI tolerance in basis points"),
):
    sg_cfg, fed_cfg, mult_cfg = load_configs(CONFIG_ROOT, year)
    default_picks = [i.code for i in mult_cfg.items if i.default_selected]
    codes = set(default_picks) | set(pick)
    codes -= set(skip)

    # Early validation for clearer CLI errors
    try:
        validate_optimization_inputs(Decimal(income), max_deduction, 1, step)
    except ValueError as e:
        rprint({"error": str(e)})
        raise typer.Exit(code=2)

    def calc_fn(inc: Decimal):
        sg_simple = simple_tax_sg(inc, sg_cfg)
        sg_after = apply_multipliers(sg_simple, mult_cfg, MultPick(codes))
        fed = tax_federal(inc, fed_cfg)
        total = sg_after + fed
        return {"total": total, "federal": fed}

    # Provide a context function so optimizer can narrate federal bracket before/after
    def context_fn(inc: Decimal):
        return {"federal_segment": federal_segment_info(inc, fed_cfg)}

    out = optimize_deduction(
        Decimal(income),
        max_deduction,
        step,
        calc_fn,
        context_fn=context_fn,
        roi_tolerance_bp=tolerance_bp,
    )

    # prettify Decimals for JSON friendliness
    def coerce(d):
        if isinstance(d, dict):
            return {k: float(v) if hasattr(v, "quantize") else coerce(v) for k, v in d.items()}
        if isinstance(d, list):
            return [coerce(x) for x in d]
        return d

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
    income: int = typer.Option(..., help="Original taxable income (CHF)"),
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
    """
    sg_cfg, fed_cfg, mult_cfg = load_configs(CONFIG_ROOT, year)
    default_picks = [i.code for i in mult_cfg.items if i.default_selected]
    codes = set(default_picks) | set(pick)
    codes -= set(skip)
    picks_sorted = sorted(codes)

    # Validate bounds
    try:
        validate_optimization_inputs(Decimal(income), max_deduction, 0, max(1, d_step))
    except ValueError as e:
        rprint({"error": str(e)})
        raise typer.Exit(code=2)

    # Helper to compute totals
    def calc_all(inc: Decimal):
        sg_simple = simple_tax_sg(inc, sg_cfg)
        sg_after = apply_multipliers(sg_simple, mult_cfg, MultPick(picks_sorted))
        fed = tax_federal(inc, fed_cfg)
        total = sg_after + fed
        return sg_simple, sg_after, fed, total

    Y0 = Decimal(income)
    _, _, _, T0 = calc_all(Y0)

    rows: List[Dict[str, Any]] = []
    eps = Decimal(100)

    for d in range(0, max_deduction + 1, max(1, d_step)):
        y = Y0 - Decimal(d)

        sg_simple, sg_after, fed, total = calc_all(y)
        saved = T0 - total
        roi = (saved / Decimal(d)) if d > 0 else Decimal(0)
        roi_pct = float(roi * 100) if d > 0 else 0.0

        # federal segment info at this y
        fseg = federal_segment_info(y, fed_cfg)

        # local marginal around y (Δ100) if requested and feasible
        local_marginal_pct = None
        if include_local_marginal:
            if y >= eps:
                _, _, _, t_hi = calc_all(y)
                _, _, _, t_lo = calc_all(y - eps)
                local_marginal_pct = float((t_hi - t_lo) / eps * 100)
            else:
                local_marginal_pct = float(0.0)

        rows.append({
            "deduction": d,
            "new_income": float(y),
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
        })

    if json_out:
        print(json.dumps(rows, indent=2))
        return

    # write CSV
    out_path = Path(out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = list(rows[0].keys()) if rows else [
        "deduction","new_income","total_tax","saved","roi_percent",
        "sg_simple","sg_after_multipliers","federal",
        "federal_from","federal_to","federal_per100","local_marginal_percent"
    ]
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
    income: int = typer.Option(...),
    deduction_amount: int = typer.Option(0, help="Amount to deduct"),
):
    """Show which tax brackets apply before/after deduction."""
    sg_cfg, fed_cfg, mult_cfg = load_configs(CONFIG_ROOT, year)
    
    original_income = chf(income)
    adjusted_income = chf(income - deduction_amount)
    
    # Federal bracket info
    fed_before = federal_segment_info(original_income, fed_cfg)
    fed_after = federal_segment_info(adjusted_income, fed_cfg)
    
    rprint({
        "original_income": income,
        "adjusted_income": float(adjusted_income),
        "federal_bracket_before": fed_before,
        "federal_bracket_after": fed_after,
        "bracket_changed": fed_before != fed_after,
    })