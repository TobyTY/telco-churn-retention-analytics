"""Display formatters shared by the report templates and the dashboard headline.

All published numbers pass through these, so check_numbers.py only has to recognise
roundings of facts.json values (and their x100, /1e3, /1e6 scalings).
"""
from __future__ import annotations


def usd(x: float, d: int = 1) -> str:
    """Dollars with M/k suffix: 1669570 -> $1.7M, 139130 -> $139k, 74.44 -> $74.44."""
    x = float(x)
    if x < 0:
        return "-" + usd(-x, d)
    if abs(x) >= 1e6:
        return f"${x / 1e6:,.{d}f}M"
    if abs(x) >= 1e5:
        return f"${x / 1e3:,.0f}k"
    if abs(x) >= 1e4:
        return f"${x / 1e3:,.{d}f}k"
    if abs(x) >= 1e3:
        return f"${x:,.0f}"
    return f"${x:,.2f}"


def money(x: float, d: int = 2) -> str:
    return f"${float(x):,.{d}f}"


def pct(x: float, d: int = 1) -> str:
    return f"{100 * float(x):.{d}f}%"


def pp(x: float, d: int = 1) -> str:
    return f"{float(x):.{d}f} pp"


def num(x: float, d: int = 0) -> str:
    return f"{float(x):,.{d}f}"


def sig(x: float, d: int = 2) -> str:
    return f"{float(x):.{d}f}"


def mult(x: float, d: int = 1) -> str:
    return f"{float(x):.{d}f}x"


FILTERS = {"usd": usd, "money": money, "pct": pct, "pp": pp, "num": num, "sig": sig, "mult": mult}
