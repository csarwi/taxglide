from decimal import Decimal, ROUND_DOWN
from math import ceil, floor
from typing import Tuple, Optional, Dict, Any
from .models import FederalConfig, chf
from .rounding import final_round

StepMode = {"ceil": ceil, "floor": floor}


def _segment_for_income(income: int, cfg: FederalConfig):
    if income < cfg.segments[0].from_:
        return cfg.segments[0]
    for seg in cfg.segments:
        lo = seg.from_
        hi = seg.to if seg.to is not None else 10**12
        if lo <= income <= hi:
            return seg
    return cfg.segments[-1]



def tax_federal(income: Decimal, cfg: FederalConfig) -> Decimal:
    i = max(0, int(income))  # guard against negative inputs
    seg = _segment_for_income(i, cfg)
    base_at = Decimal(str(seg.base_tax_at))
    per100 = Decimal(str(seg.per100))
    # count started 100s within segment per config
    if cfg.rounding.per_100_step:
        step = cfg.rounding.step_size
        start = seg.at_income
        delta = max(0, i - start)
        if cfg.rounding.step_mode == "ceil":
            units = 0 if delta == 0 else ((delta + step - 1) // step)
        else:
            units = delta // step
        tax = base_at + per100 * units
    else:
        tax = base_at
    # Apply official ESTV final rounding for federal:
    # "annual tax is rounded down to the next 5 rappen"
    step = Decimal("0.05")
    tax = (tax / step).to_integral_value(rounding=ROUND_DOWN) * step
    return tax


def federal_marginal_hundreds(income: Decimal, cfg: FederalConfig) -> float:
    """
    Marginal per 100 CHF for the *current* hundred-block (backward difference).
    m(i) = [T(h) - T(h-100)] / 100, with h = floor(i/100)*100.
    This reflects the actual marginal that applies to income inside the current
    block, avoiding the upward bias of always rounding to the next 100.
    """
    i = max(0, int(income))          # guard against negative inputs
    h = (i // 100) * 100
    t_hi = tax_federal(Decimal(h), cfg)
    t_lo = tax_federal(Decimal(max(h - 100, 0)), cfg)
    return float((t_hi - t_lo) / Decimal(100))


def federal_segment_info(income: Decimal | int, cfg: FederalConfig) -> Dict[str, Any]:
    """
    Lightweight inspector used by the optimizer for 'why' explanations.
    Returns: {'from': int, 'to': Optional[int], 'per100': float, 'at_income': int}
    """
    i = int(income)
    seg = _segment_for_income(i, cfg)
    return {
        "from": seg.from_,
        "to": seg.to,
        "per100": float(seg.per100),
        "at_income": seg.at_income,
    }
