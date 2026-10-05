"""reports/facts.json is the single source of truth for every published number.

Each pipeline step owns one top-level section and rewrites only that section, so steps
can be re-run independently. Values are plain JSON numbers (cents for amounts of 100 or more, 6 significant
places below that); templates format them for display.
"""
from __future__ import annotations

import json
import math

import numpy as np
import pandas as pd

from src.config import FACTS


def _clean(v):
    if isinstance(v, dict):
        return {str(k): _clean(x) for k, x in v.items()}
    if isinstance(v, (list, tuple)):
        return [_clean(x) for x in v]
    if isinstance(v, (np.integer,)):
        return int(v)
    if isinstance(v, (np.floating, float)):
        f = float(v)
        if not math.isfinite(f):
            return None
        return round(f, 2) if abs(f) >= 100 else float(f"{f:.6g}")
    if isinstance(v, (np.bool_,)):
        return bool(v)
    if isinstance(v, (pd.Timestamp,)):
        return v.strftime("%Y-%m-%d")
    return v


def read() -> dict:
    return json.loads(FACTS.read_text(encoding="utf-8")) if FACTS.exists() else {}


def update(section: str, values: dict) -> dict:
    facts = read()
    facts[section] = _clean(values)
    FACTS.write_text(json.dumps(facts, indent=2, ensure_ascii=False), encoding="utf-8")
    return facts
