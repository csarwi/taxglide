
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