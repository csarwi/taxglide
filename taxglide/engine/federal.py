from decimal import Decimal
from math import ceil, floor
from typing import Tuple
from .models import FederalConfig, chf
from .rounding import final_round

StepMode = {"ceil": ceil, "floor": floor}

def _segment_for_income(income: int, cfg: FederalConfig):
    for seg in cfg.segments:
        lo = seg.from_
        hi = seg.to if seg.to is not None else 10**12
        if lo <= income <= hi:
            return seg
    # if higher than all, use last
    return cfg.segments[-1]


def tax_federal(income: Decimal, cfg: FederalConfig) -> Decimal:
    i = int(income)
    seg = _segment_for_income(i, cfg)
    base_at = Decimal(str(seg.base_tax_at))
    per100 = Decimal(str(seg.per100))
    # count started 100s within segment per config
    if cfg.rounding.per_100_step:
        step = cfg.rounding.step_size
        start = seg.at_income
        delta = max(0, i - start)
        if cfg.rounding.step_mode == "ceil":
            units = 0 if delta == 0 else ( (delta + step - 1) // step )
        else:
            units = delta // step
        tax = base_at + per100 * units
    else:
        tax = base_at
    return final_round(tax, cfg.rounding.tax_round_to)


def federal_marginal_hundreds(income: Decimal, cfg: FederalConfig) -> float:
    """Marginal rate aligned to full hundreds (your rule).
    m(i) = [T(h) - T(h-100)] / 100, with h = ceil(i/100)*100
    """
    i = int(income)
    h = ( (i + 99) // 100 ) * 100
    t_hi = tax_federal(Decimal(h), cfg)
    t_lo = tax_federal(Decimal(max(h - 100, 0)), cfg)
    return float((t_hi - t_lo) / Decimal(100))