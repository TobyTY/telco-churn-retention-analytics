"""Render README, executive summary, insights, model card, interview notes, assumptions and data README.

Templates in templates/*.j2 read only from reports/facts.json (the cleaning and audit logs are copied
into facts.json first), so check_numbers.py can trace every number.
"""
from __future__ import annotations

import json
import re

import pandas as pd
from jinja2 import Environment, FileSystemLoader, StrictUndefined

from src import facts
from src.config import DATA_RAW, DOCS, PAGES_URL, RAW_FILE, REPO_URL, REPORTS, ROOT, TEMPLATES
from src.fmt import FILTERS

OUTPUTS = {
    "README.md.j2": ROOT / "README.md",
    "executive_summary.md.j2": REPORTS / "executive_summary.md",
    "insights_and_recommendations.md.j2": REPORTS / "insights_and_recommendations.md",
    "model_card.md.j2": DOCS / "model_card.md",
    "interview_talking_points.md.j2": DOCS / "interview_talking_points.md",
    "assumptions.md.j2": DOCS / "assumptions.md",
    "data_README.md.j2": ROOT / "data" / "README.md",
}


def count_measures() -> int:
    """Measures in powerbi/measures.dax are written as a 'Name =' line followed by the expression."""
    text = (ROOT / "powerbi" / "measures.dax").read_text(encoding="utf-8")
    return len([m for m in re.findall(r"^([A-Z][^=\n]*?)\s=\s*$", text, re.M) if not m.startswith(("VAR", "RETURN"))])


def data_quality() -> dict:
    raw = pd.read_csv(RAW_FILE, dtype=str)
    checks = pd.read_csv(REPORTS / "audit_checks.csv")
    return {"log": pd.read_csv(REPORTS / "cleaning_log.csv").to_dict("records"), "checks": checks.to_dict("records"),
            "raw_columns": raw.shape[1], "raw_rows": len(raw), "validation_tolerance_pct": 20,
            "blank_total_charges": int(checks.set_index("check").loc["blank TotalCharges", "count"]),
            "dax_measures": count_measures()}


def build() -> None:
    facts.update("data_quality", data_quality())
    f = facts.read()
    env = Environment(loader=FileSystemLoader(TEMPLATES), undefined=StrictUndefined, keep_trailing_newline=True)
    env.filters.update(FILTERS)
    ctx = {"a": f["analysis"], "m": f["model"], "e": f["eda"], "q": f["data_quality"],
           "src": json.loads((DATA_RAW / "_source.json").read_text(encoding="utf-8")),
           "pages_url": PAGES_URL, "repo_url": REPO_URL, "log": f["data_quality"]["log"], "checks": f["data_quality"]["checks"]}
    for tpl, out in OUTPUTS.items():
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(env.get_template(tpl).render(**ctx), encoding="utf-8")
        print(f"report: wrote {out.relative_to(ROOT)}")


if __name__ == "__main__":
    build()
