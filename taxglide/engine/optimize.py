
from decimal import Decimal
from typing import Dict, Any
from .models import CalcResult

def optimize_deduction(
    income: Decimal,
    max_deduction: int,
    step: int,
    calc_fn,
) -> Dict[str, Any]:
    """Grid search over deduction d in [0..max] with given step.
    calc_fn should be a function income' -> CalcResult (or dict with 'total').
    Returns best by absolute CHF saved and by savings rate.
    """
    best_abs = None
    best_rate = None
    base = calc_fn(income)
    base_total = base["total"] if isinstance(base, dict) else base.total

    d = 0
    while d <= max_deduction:
        new_income = income - Decimal(d)
        res = calc_fn(new_income)
        total = res["total"] if isinstance(res, dict) else res.total
        saved = base_total - total
        rate = (saved / Decimal(d)) if d > 0 else Decimal(0)
        pack = {
            "deduction": d,
            "new_income": new_income,
            "total": total,
            "saved": saved,
            "savings_rate": rate,
        }
        if best_abs is None or saved > best_abs["saved"]:
            best_abs = pack
        if d > 0 and (best_rate is None or rate > best_rate["savings_rate"]):
            best_rate = pack
        d += step
    return {"best_absolute": best_abs, "best_rate": best_rate}