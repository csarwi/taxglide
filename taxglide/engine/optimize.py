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


def validate_optimization_inputs(
    income: Number,
    max_deduction: int,
    min_deduction: int,
    step: int,
):
    if income < 0:
        raise ValueError("Income must be non-negative")
    if step <= 0:
        raise ValueError("Step must be positive")
    if min_deduction < 0:
        raise ValueError("Min deduction must be non-negative")
    if max_deduction < 0:
        raise ValueError("Max deduction must be non-negative")
    if max_deduction < min_deduction:
        raise ValueError("Max deduction must be >= min deduction")
    if max_deduction > int(income):
        raise ValueError(f"Max deduction ({max_deduction}) cannot exceed income ({int(income)})")


def optimize_deduction(
    income: Number,
    max_deduction: int,
    step: int,
    calc_fn: Callable[[Number], Dict[str, Any]],
    *,
    # context_fn can provide extra info for explanation, e.g. federal bracket
    context_fn: Optional[Callable[[Number], Dict[str, Any]]] = None,
    fine_window: int = 300,
    fine_step: int = 100,                 # increased to avoid rounding artifacts
    min_deduction: int = 100,             # increased to avoid meaningless tiny deductions and rounding artifacts
    roi_tolerance_bp: float = 10.0,       # 10 bp = 0.10% band for near-max plateau
    prefer_smallest_on_tie: bool = True,  # keep old behavior by default
    max_realistic_roi: float = 100.0,     # filter out ROI spikes above this % (unrealistic)
) -> Dict[str, Any]:
    """
    Maximize ROI(d) = (T0 - T(Y0-d)) / d for d in [min_deduction..max_deduction].
    Returns:
      - base_total
      - best_rate (ROI-optimal point)
      - plateau_near_max_roi (band of near-max ROI within tolerance)
      - sweet_spot (chosen end-of-plateau with clear 'why')
      - local_marginal_percent_* (at ROI-best and at sweet spot)
      - federal_100_nudge (optional micro-nudge)
    """
    # --- Validate & normalize search space ---
    validate_optimization_inputs(income, max_deduction, min_deduction, step)
    max_deduction = min(max_deduction, int(income))

    base = calc_fn(income)
    T0 = _as_total(base)

    if max_deduction <= 0 or min_deduction > max_deduction:
        return {
            "base_total": T0,
            "best_rate": None,
            "plateau_near_max_roi": None,
            "sweet_spot": None,
            "diagnostics": {"note": "no search space"},
        }

    # -------- Coarse scan --------
    best_rate = None  # by ROI

    d = max(step, ((min_deduction + step - 1) // step) * step)
    while d <= max_deduction:
        y = income - Decimal(d)  # safe (d <= income)
        r = calc_fn(y)
        T = _as_total(r)
        saved = T0 - T
        roi = _roi(saved, d)

        # Filter out unrealistic ROI spikes caused by tax rounding artifacts
        roi_percent = float(roi * 100)
        if roi_percent <= max_realistic_roi:
            pack = {"deduction": d, "new_income": y, "total": T, "saved": saved, "savings_rate": roi}

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
        return {"base_total": T0, "best_rate": None, "plateau_near_max_roi": None, "sweet_spot": None}

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
        
        # Skip unrealistic ROI values in fine scan too
        roi_percent = float(roi * 100)
        if roi_percent > max_realistic_roi:
            continue
            
        if (roi > best_rate["savings_rate"]) or (
            _within_tol(roi, best_rate["savings_rate"], Decimal("1e-12")) and
            ((d < best_rate["deduction"]) if prefer_smallest_on_tie else (d > best_rate["deduction"]))
        ):
            best_rate = {"deduction": d, "new_income": y, "total": T, "saved": saved, "savings_rate": roi}

    # -------- Plateau detection (within tolerance bp, symmetric) --------
    tol = Decimal(roi_tolerance_bp) / Decimal(10000)
    roi_star = best_rate["savings_rate"]

    plateau: List[Tuple[int, float]] = []
    for d in range(max(min_deduction, fine_step), max_deduction + 1, fine_step):
        y = income - Decimal(d)  # d <= income by validation
        r = calc_fn(y)
        T = _as_total(r)
        saved = T0 - T
        roi = _roi(saved, d)
        
        # Skip unrealistic ROI values in plateau detection
        roi_percent = float(roi * 100)
        if roi_percent > max_realistic_roi:
            continue
            
        # symmetric tolerance: keep points within ±tol of best ROI
        if abs(roi_star - roi) <= tol:
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

    # -------- Local marginal at ROI-best (Δ100) --------
    eps = Decimal(100)
    y_best = best_rate["new_income"]
    r0 = calc_fn(y_best)
    r1 = calc_fn(y_best - eps)  # safe: y_best >= 0 and eps <= y_best by construction
    T0_best = _as_total(r0)
    T1_best = _as_total(r1)
    local_marginal_percent_at_best = float((T0_best - T1_best) / eps * 100)

    # -------- Optional federal 100-step nudge (from ROI-best) --------
    fed_now = _as_federal_maybe(r0)
    nudge_diag = None
    if fed_now is not None:
        fed_now = Decimal(fed_now)
        for k in range(1, 100):
            r_prev = calc_fn(y_best - Decimal(k))  # k <= 99; safe
            fed_prev = _as_federal_maybe(r_prev)
            if fed_prev is None:
                break
            fed_prev = Decimal(fed_prev)
            if fed_prev < fed_now - Decimal("1e-9"):
                nudge_diag = {"nudge_chf": k, "estimated_federal_saving": float(fed_now - fed_prev)}
                break

    # -------- Sweet spot selection & explanation --------
    sweet_spot = None
    local_marginal_percent_at_spot = None
    why: Optional[Dict[str, Any]] = None

    if plateau_range:
        # choose end of plateau (max d) as conservative optimal point
        d_spot = plateau_range["max_d"]
        y_spot = income - Decimal(d_spot)
        r_spot = calc_fn(y_spot)
        T_spot = _as_total(r_spot)
        saved_spot = T0 - T_spot
        roi_spot = _roi(saved_spot, d_spot)  # Decimal
        # Components (if available from calc_fn)
        fed_spot_maybe = _as_federal_maybe(r_spot)
        fed_base_maybe = _as_federal_maybe(base)
        sg_spot_maybe = (T_spot - fed_spot_maybe) if (fed_spot_maybe is not None) else None
        sg_base_maybe = (T0 - fed_base_maybe) if (fed_base_maybe is not None) else None
        roi_spot = _roi(saved_spot, d_spot)  # Decimal

        # local marginal at the sweet spot (Δ100)
        r_spot_lo = calc_fn(y_spot - eps if y_spot >= eps else y_spot)
        T_spot_lo = _as_total(r_spot_lo)
        local_marginal_percent_at_spot = float((T_spot - T_spot_lo) / (y_spot - (y_spot - eps if y_spot >= eps else y_spot)) * 100) if y_spot > 0 else float(0.0)

        # federal bracket awareness (optional context_fn)
        ctx_before = context_fn(income) if context_fn else None
        ctx_after = context_fn(y_spot) if context_fn else None
        fed_before = ctx_before.get("federal_segment") if ctx_before else None
        fed_after = ctx_after.get("federal_segment") if ctx_after else None
        sg_before = ctx_before.get("sg_bracket") if ctx_before else None
        sg_after = ctx_after.get("sg_bracket") if ctx_after else None

        # --- Bracket change flags ---
        federal_bracket_changed = (fed_before != fed_after) if (fed_before and fed_after) else None
        sg_bracket_changed = (sg_before != sg_after) if (sg_before and sg_after) else None

        # --- Extra deduction needed to force a change (if unchanged) ---
        # Federal rule: segment contains income if lo <= i <= hi; to move to a lower segment, need i < lo.
        extra_deduction_to_change_federal = None
        if federal_bracket_changed is False:
            lo = int(fed_before.get("from", 0))
            if lo <= 0:
                # Already at the lowest bracket — cannot change further down
                extra_deduction_to_change_federal = None
            else:
                # Need to go below lo, i.e., target income <= lo-1
                target_income = Decimal(lo - 1)
                extra = y_spot - target_income
                extra_deduction_to_change_federal = int(extra) if extra > 0 else 0

        # SG rule has two shapes:
        #  - flat_percent_above override active if income > threshold → to exit, need income <= threshold
        #  - progressive bracket when (i > lower and i <= upper) → to move down, need i <= lower
        extra_deduction_to_change_sg = None
        if sg_bracket_changed is False and sg_before:
            if sg_before.get("model") == "flat_percent_above":
                thr = int(sg_before.get("threshold", 0))
                target_income = Decimal(thr)   # need <= thr
                extra = y_spot - target_income
                extra_deduction_to_change_sg = int(extra) if extra > 0 else 0
            else:
                lower = int(sg_before.get("lower", 0))
                if lower <= 0:
                    # Already at the lowest bracket — cannot change further down
                    extra_deduction_to_change_sg = None
                else:
                    # Need i <= lower to fall into previous bracket (note: SG logic uses i > lower for current)
                    target_income = Decimal(lower)
                    extra = y_spot - target_income
                    extra_deduction_to_change_sg = int(extra) if extra > 0 else 0

        # Explain with compact, decision-relevant metrics
        roi_best_pct = float(best_rate["savings_rate"] * 100)
        roi_spot_pct = float(roi_spot * 100)
        drop_bp = abs(roi_best_pct - roi_spot_pct) * 100  # basis points
        plateau_width = plateau_range["max_d"] - plateau_range["min_d"]

        notes = []
        if federal_bracket_changed is False and extra_deduction_to_change_federal is None:
            notes.append("Federal: already at the lowest bracket.")
        if sg_bracket_changed is False and extra_deduction_to_change_sg is None:
            notes.append("SG: already at the lowest bracket or override floor.")

        why = {
            "roi_at_spot_percent": roi_spot_pct,
            "roi_best_percent": roi_best_pct,
            "difference_from_best_bp": drop_bp,
            "plateau_width_chf": plateau_width,
            "plateau_bounds_chf": [plateau_range["min_d"], plateau_range["max_d"]],
            "local_marginal_percent_at_spot": local_marginal_percent_at_spot,
            "federal_bracket_before": fed_before,
            "federal_bracket_after": fed_after,
            "sg_bracket_before": sg_before,
            "sg_bracket_after": sg_after,
            "federal_bracket_changed": federal_bracket_changed,
            "sg_bracket_changed": sg_bracket_changed,
            "extra_deduction_to_change_federal_bracket": extra_deduction_to_change_federal,
            "extra_deduction_to_change_sg_bracket": extra_deduction_to_change_sg,
            "notes": notes or None,
            "federal_100_nudge_from_best": nudge_diag,
        }
        # Saved percent vs baseline
        saved_pct_spot = float((saved_spot / T0 * 100)) if T0 > 0 else 0.0

        sweet_spot = {
            "deduction": d_spot,
            "new_income": float(y_spot),
            "total_tax_at_spot": float(T_spot),
            "tax_saved_absolute": float(saved_spot),
            "tax_saved_percent": saved_pct_spot,
            # Optional quick breakdowns if calc_fn provided components
            "federal_tax_at_spot": float(fed_spot_maybe) if fed_spot_maybe is not None else None,
            "sg_tax_at_spot": float(sg_spot_maybe) if sg_spot_maybe is not None else None,
            "baseline": {
                "total_tax": float(T0),
                "federal_tax": float(fed_base_maybe) if fed_base_maybe is not None else None,
                "sg_tax": float(sg_base_maybe) if sg_base_maybe is not None else None,
            },
            "explanation": "End of near-max ROI plateau: last CHF before ROI drops meaningfully.",
            "why": why,
        }

    return {
        "base_total": T0,
        #"best_rate": {
        #    **best_rate,
        #    "savings_rate_percent": float(best_rate["savings_rate"] * 100),
        #},
        #"plateau_near_max_roi": plateau_range,   # full near-max band
        "sweet_spot": sweet_spot,
        "local_marginal_percent_at_best": local_marginal_percent_at_best,
        "local_marginal_percent_at_spot": local_marginal_percent_at_spot,
        #"federal_100_nudge": nudge_diag,
    }
