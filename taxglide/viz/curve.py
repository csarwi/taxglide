
from decimal import Decimal
from typing import Iterable, Tuple
import matplotlib.pyplot as plt


def plot_curve(points: Iterable[Tuple[int, Decimal]], out_path: str):
    xs = [x for x, _ in points]
    ys = [float(y) for _, y in points]
    plt.figure()
    plt.plot(xs, ys)
    plt.xlabel("Taxable income (CHF)")
    plt.ylabel("Total tax (CHF)")
    plt.title("Personal tax curve")
    plt.tight_layout()
    plt.savefig(out_path, dpi=150)
    plt.close()