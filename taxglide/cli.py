
from __future__ import annotations
from decimal import Decimal
from pathlib import Path
from typing import List
import json
import typer
from rich import print as rprint

from .io.loader import load_configs
from .engine.stgallen import simple_tax_sg
from .engine.federal import tax_federal, federal_marginal_hundreds
from .engine.multipliers import apply_multipliers, MultPick
from .engine.models import chf
from .engine.optimize import optimize_deduction
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
):
    sg_cfg, fed_cfg, mult_cfg = load_configs(CONFIG_ROOT, year)
    default_picks = [i.code for i in mult_cfg.items if i.default_selected]
    codes = set(default_picks) | set(pick)
    codes -= set(skip)

    def calc_fn(inc: Decimal):
        sg_simple = simple_tax_sg(inc, sg_cfg)
        sg_after = apply_multipliers(sg_simple, mult_cfg, MultPick(codes))
        fed = tax_federal(inc, fed_cfg)
        total = sg_after + fed
        return {"total": total}

    out = optimize_deduction(Decimal(income), max_deduction, step, calc_fn)
    # prettify Decimals
    def coerce(d):
        if isinstance(d, dict):
            return {k: float(v) if hasattr(v, "quantize") else v for k, v in d.items()}
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
):
    _, _, mult_cfg = load_configs(CONFIG_ROOT, year)
    default_picks = [i.code for i in mult_cfg.items if i.default_selected]
    codes = set(default_picks) | set(pick)
    codes -= set(skip)

    pts = []
    for x in range(min, max + 1, step):
        res = _calc_once(year, x, sorted(codes))
        pts.append((x, Decimal(str(res["total"]))))
    plot_curve(pts, out)
    rprint({"saved": out})