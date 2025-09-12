from decimal import Decimal
from typing import Dict, Any, Callable, Optional, Tuple, List

Number = Decimal

def _as_total(res: Dict[str, Any]) -> Number:
    return res["total"] if isinstance(res, dict) else res.total

def _as_federal_maybe(res: Dict[str, Any]) -> Optional[Number]:
    if isinstance(res, dict) and "federal" in res:
        return res["federal"]
    return None

def _roi(saved: Number, d: int) -> Number:
    return saved / Decimal(d)

def _within_tol(a: Number, b: Number, tol: Number) -> bool:
    return abs(a - b) <= tol

def optimize_deduction(
    income: Number,
    max_deduction: int,
    step: int,
    calc_fn: Callable[[Number], Dict[str, Any]],
    *,
    fine_window: int = 300,
    fine_step: int = 1,
    min_deduction: int = 1,              # NEW: ignore tiny d below this
    roi_tolerance_bp: float = 10.0,       # NEW: 5 basis points tolerance to form a plateau (0.05%)
    prefer_smallest_on_tie: bool = True, # keep old behavior by default
) -> Dict[str, Any]:
    """
    Maximize ROI(d) = (T0 - T(Y0-d)) / d for d in [min_deduction..max_deduction].
    Returns best ROI point, best absolute savings point, a near-max ROI plateau,
    local marginal at best ROI, and optional federal 100-step nudge.
    """
    base = calc_fn(income)
    T0 = _as_total(base)

    if max_deduction <= 0 or min_deduction > max_deduction:
        return {
            "base_total": T0,
            "best_rate": None,
            "best_absolute": None,
            "diagnostics": {"note": "no search space"},
        }

    # -------- Coarse scan --------
    best_rate = None  # by ROI
    best_abs = None   # by CHF saved

    d = max(step, ((min_deduction + step - 1) // step) * step)
    while d <= max_deduction:
        y = income - Decimal(d)
        r = calc_fn(y)
        T = _as_total(r)
        saved = T0 - T
        roi = _roi(saved, d)

        pack = {"deduction": d, "new_income": y, "total": T, "saved": saved, "savings_rate": roi}

        if (best_abs is None) or (saved > best_abs["saved"]):
            best_abs = pack

        def _is_better(lhs, rhs):
            if rhs is None:
                return True
            if roi > rhs["savings_rate"]:
                return True
            if _within_tol(roi, rhs["savings_rate"], Decimal("1e-12")):
                return d < rhs["deduction"] if prefer_smallest_on_tie else d > rhs["deduction"]
            return False

        if _is_better(pack, best_rate):
            best_rate = pack

        d += step

    if best_rate is None:
        return {"base_total": T0, "best_rate": None, "best_absolute": best_abs}

    # -------- Fine scan around best ROI --------
    center = best_rate["deduction"]
    d_min = max(min_deduction, center - fine_window)
    d_max = min(max_deduction, center + fine_window)

    for d in range(d_min, d_max + 1, fine_step):
        y = income - Decimal(d)
        r = calc_fn(y)
        T = _as_total(r)
        saved = T0 - T
        roi = _roi(saved, d)
        if (roi > best_rate["savings_rate"]) or (
            _within_tol(roi, best_rate["savings_rate"], Decimal("1e-12")) and
            ((d < best_rate["deduction"]) if prefer_smallest_on_tie else (d > best_rate["deduction"]))
        ):
            best_rate = {"deduction": d, "new_income": y, "total": T, "saved": saved, "savings_rate": roi}

    # -------- Plateau detection (within tolerance bp) --------
    tol = Decimal(roi_tolerance_bp) / Decimal(10000)
    roi_star = best_rate["savings_rate"]

    plateau: List[Tuple[int, float]] = []
    for d in range(max(min_deduction, 1), max_deduction + 1, fine_step):  # <— changed
        y = max(income - Decimal(d), Decimal(0))                          # clamp
        r = calc_fn(y)
        T = _as_total(r)
        saved = T0 - T
        roi = _roi(saved, d)
        if roi_star - roi <= tol:
            plateau.append((d, float(roi * 100)))


    plateau_range = None
    if plateau:
        plateau_range = {
            "min_d": plateau[0][0],
            "max_d": plateau[-1][0],
            "roi_min_percent": plateau[-1][1],
            "roi_max_percent": plateau[0][1],
            "tolerance_bp": roi_tolerance_bp,
        }

    # -------- Local marginal after best (Δ100) --------
    eps = Decimal(100)
    y_best = best_rate["new_income"]
    r0 = calc_fn(y_best)
    r1 = calc_fn(max(y_best - eps, Decimal(0)))
    T0_best = _as_total(r0)
    T1_best = _as_total(r1)
    local_marginal_percent = float((T0_best - T1_best) / eps * 100)

    # -------- Optional federal 100-step nudge --------
    fed_now = _as_federal_maybe(r0)
    nudge_diag = None
    if fed_now is not None:
        fed_now = Decimal(fed_now)
        for k in range(1, 100):
            r_prev = calc_fn(y_best - Decimal(k))
            fed_prev = _as_federal_maybe(r_prev)
            if fed_prev is None:
                break
            fed_prev = Decimal(fed_prev)
            if fed_prev < fed_now - Decimal("1e-9"):
                nudge_diag = {"nudge_chf": k, "estimated_federal_saving": float(fed_now - fed_prev)}
                break

    sweet_spot = None
    if plateau_range:
        # choose the *max* d in the near-max band = last CHF before ROI drops
        sweet_spot = {
            "deduction": plateau_range["max_d"],
            "explanation": "End of near-max ROI plateau before a sustained drop."
        }

    return {
        "base_total": T0,
        "best_rate": {
            **best_rate,
            "savings_rate_percent": float(best_rate["savings_rate"] * 100),
        },
        "best_absolute": best_abs,
        "plateau_near_max_roi": plateau_range,  # NEW: shows the whole “almost best” band
        "sweet_spot": sweet_spot,
        "local_marginal_percent_after_best": local_marginal_percent,
        "federal_100_nudge": nudge_diag,
    }
