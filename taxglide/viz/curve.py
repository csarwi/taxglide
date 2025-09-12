from decimal import Decimal
from typing import Iterable, Tuple, Optional, Dict, Any
import matplotlib.pyplot as plt


def plot_curve(
    points: Iterable[Tuple[int, Decimal]],
    out_path: str,
    annotations: Optional[Dict[str, Any]] = None,
):
    """
    points: iterable of (income:int, total_tax:Decimal)
    annotations (optional):
      {
        "sweet_spot_income": float|int,
        "sweet_spot_total": float|int,
        "plateau_income_min": float|int,
        "plateau_income_max": float|int,
        "label": str,                          # text near the sweet spot
      }
    """
    xs = [x for x, _ in points]
    ys = [float(y) for _, y in points]

    plt.figure()
    plt.plot(xs, ys)
    plt.xlabel("Taxable income (CHF)")
    plt.ylabel("Total tax (CHF)")
    plt.title("Personal tax curve")

    if annotations:
        ax = plt.gca()
        s_inc = annotations.get("sweet_spot_income", None)
        s_tot = annotations.get("sweet_spot_total", None)
        p_min = annotations.get("plateau_income_min", None)
        p_max = annotations.get("plateau_income_max", None)
        label = annotations.get("label", "Sweet spot")

        # Shade plateau income band if available
        if p_min is not None and p_max is not None and p_min < p_max:
            ax.axvspan(p_min, p_max, alpha=0.12)

        # Vertical line + marker for sweet spot
        if s_inc is not None:
            ax.axvline(float(s_inc), linestyle="--")
            if s_tot is not None:
                ax.scatter([float(s_inc)], [float(s_tot)])
                # place annotation slightly above point
                ax.annotate(
                    label,
                    xy=(float(s_inc), float(s_tot)),
                    xytext=(10, 12),
                    textcoords="offset points",
                    arrowprops=dict(arrowstyle="->", lw=0.8),
                )

    plt.tight_layout()
    plt.savefig(out_path, dpi=150)
    plt.close()
