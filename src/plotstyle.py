"""One chart style for every figure: thin marks, hairline grid, fixed categorical order."""
from __future__ import annotations

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

from src.config import FIGURES  # noqa: E402

SERIES = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300", "#4a3aa7", "#e34948"]
MUTED = "#898781"
GRID = "#e1e0d9"
INK = "#0b0b0b"
INK_2 = "#52514e"
SURFACE = "#fcfcfb"
GOOD, CRITICAL = "#0ca30c", "#d03b3b"
SEQ_BLUE = "Blues"

plt.rcParams.update({
    "figure.facecolor": SURFACE, "axes.facecolor": SURFACE, "savefig.facecolor": SURFACE,
    "axes.edgecolor": "#c3c2b7", "axes.linewidth": 0.8, "axes.grid": True, "grid.color": GRID,
    "grid.linewidth": 0.6, "axes.axisbelow": True, "axes.spines.top": False, "axes.spines.right": False,
    "axes.titlesize": 12, "axes.titleweight": "bold", "axes.titlelocation": "left", "axes.titlepad": 12,
    "axes.labelcolor": INK_2, "axes.labelsize": 10, "xtick.color": INK_2, "ytick.color": INK_2,
    "xtick.labelsize": 9, "ytick.labelsize": 9, "font.family": ["Segoe UI", "DejaVu Sans", "sans-serif"],
    "legend.frameon": False, "legend.fontsize": 9, "lines.linewidth": 2, "figure.dpi": 110,
    "axes.prop_cycle": matplotlib.cycler(color=SERIES), "text.parse_math": False,
})


def save(fig, name: str, takeaway: str | None = None) -> str:
    """Save a figure to reports/figures; the takeaway line sits under the plot."""
    if takeaway:
        fig.text(0.01, 0.01, takeaway, fontsize=9, color=INK_2, ha="left", va="bottom")
        fig.subplots_adjust(bottom=0.2)
    path = FIGURES / f"{name}.png"
    fig.savefig(path, dpi=130, bbox_inches="tight")
    plt.close(fig)
    return path.name


def usd(x: float, decimals: int = 1) -> str:
    if abs(x) >= 1e6:
        return f"${x / 1e6:.{decimals}f}M"
    if abs(x) >= 1e3:
        return f"${x / 1e3:.{decimals}f}k"
    return f"${x:.0f}"
