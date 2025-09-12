from decimal import Decimal
from typing import Iterable
from .models import MultipliersConfig

class MultPick:
    def __init__(self, codes: Iterable[str]):
        self.codes = set(codes)
    def selected(self, code: str) -> bool:
        return code in self.codes

def apply_multipliers(simple_tax: Decimal, cfg: MultipliersConfig, picks: MultPick) -> Decimal:
    """
    SG rule: each Steuerfuss applies to the 'einfache Steuer' independently, then sums up.
    So total = base * (sum of selected rates).
    Example: base * (1.05 + 1.38) = base * 2.43
    Feuerwehr is 0.14 (14% of base), not 1.14.
    """
    selected = [it for it in cfg.items if picks.selected(it.code)]
    if not selected:
        return Decimal(0)  # no multipliers selected → no cantonal/communal tax
    sum_rate = sum(Decimal(str(it.rate)) for it in selected)
    return simple_tax * sum_rate
