
from decimal import Decimal
from .models import StGallenConfig, chf
from .rounding import final_round

def simple_tax_sg(income: Decimal, cfg: StGallenConfig) -> Decimal:
    # override: flat percent for whole income above threshold
    if cfg.override and cfg.override.flat_percent_above:
        thr = int(cfg.override.flat_percent_above.get("threshold", 0))
        pct = Decimal(str(cfg.override.flat_percent_above.get("percent", 0))) / Decimal(100)
        if income > thr:
            tax = income * pct
            return final_round(tax, cfg.rounding.tax_round_to)
    # progressive portion-of-bracket model
    tax = Decimal(0)
    remaining = income
    for b in cfg.brackets:
        upper = b.lower + b.width
        if income <= b.lower:
            continue
        portion = min(income, upper) - b.lower
        rate = Decimal(str(b.rate_percent)) / Decimal(100)
        tax += chf(portion) * rate
        if income <= upper:
            break
    return final_round(tax, cfg.rounding.tax_round_to)


def sg_bracket_info(income: Decimal | int, cfg: StGallenConfig):
    """
    Lightweight inspector for SG that mirrors federal_segment_info.
    Returns either:
      - {'model': 'flat_percent_above', 'threshold': int, 'percent': float}
        when the override is active (income > threshold), or
      - {'lower': int, 'upper': int, 'rate_percent': float}
        for the progressive brackets.
    """
    i = int(income)
    # Flat override active?
    if cfg.override and cfg.override.flat_percent_above:
        thr = int(cfg.override.flat_percent_above.get("threshold", 0))
        pct = float(cfg.override.flat_percent_above.get("percent", 0))
        if i > thr:
            return {"model": "flat_percent_above", "threshold": thr, "percent": pct}

    # Progressive model: find current bracket
    for b in cfg.brackets:
        lower = b.lower
        upper = b.lower + b.width
        if i > lower and i <= upper:
            return {"lower": lower, "upper": upper, "rate_percent": float(b.rate_percent)}
    # If below the very first taxable lower bound, treat as in the first bracket
    if cfg.brackets:
        b0 = cfg.brackets[0]
        return {"lower": b0.lower, "upper": b0.lower + b0.width, "rate_percent": float(b0.rate_percent)}
    return {"lower": 0, "upper": 0, "rate_percent": 0.0}