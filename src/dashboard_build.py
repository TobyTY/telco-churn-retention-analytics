"""Build dashboard/index.html: one self-contained file (Plotly and customer-level data inlined).

The page works offline from file:// and is copied to docs/index.html for GitHub Pages. With only
7,043 customers the full customer table ships with the page, so every filter is exact.
"""
from __future__ import annotations

import json
import shutil
from datetime import date

import pandas as pd
from plotly.offline import get_plotlyjs

from src import facts
from src.clean import load
from src.config import DASHBOARD, DOCS, REPO_URL, REPORTS
from src.fmt import pct, usd


def build() -> dict:
    df = load()
    scores = pd.read_csv(REPORTS / "customer_scores.csv")[["customer_id", "churn_probability", "risk_band"]]
    df = df.merge(scores, on="customer_id", validate="one_to_one")
    fx = facts.read()
    a, m = fx["analysis"], fx["model"]

    lk = {
        "contract": ["Month-to-month", "One year", "Two year"],
        "internet": ["Fiber optic", "DSL", "No"],
        "payment": sorted(df.payment_method.unique()),
        "tenure": sorted(df.tenure_band.unique()),
        "risk": ["1. High", "2. Medium", "3. Low"],
        "tech": ["No", "Yes", "No internet service"],
        "security": ["No", "Yes", "No internet service"],
        "addons": [str(i) for i in range(7)],
        "yesno": ["No", "Yes"],
    }
    idx = lambda col, key: df[col].map({v: i for i, v in enumerate(lk[key])}).astype(int)
    rows = pd.DataFrame({
        "c": idx("contract", "contract"), "i": idx("internet_service", "internet"), "p": idx("payment_method", "payment"),
        "t": idx("tenure_band", "tenure"), "ten": df.tenure_months, "mc": df.monthly_charges.round(2), "y": df.churned,
        "prob": df.churn_probability.round(4), "rb": idx("risk_band", "risk"), "ts": idx("tech_support", "tech"),
        "n": df.n_addons, "sen": df.is_senior.astype(int), "pap": df.paperless_billing.astype(int),
        "sec": idx("online_security", "security"), "id": df.customer_id,
    })
    km = json.loads((REPORTS / "km_curves.json").read_text(encoding="utf-8"))
    drivers = pd.read_csv(REPORTS / "drivers.csv").head(10)
    curve = pd.read_csv(REPORTS / "threshold_curve_test.csv")
    lift = pd.read_csv(REPORTS / "lift_table.csv")
    data = {
        "lookups": lk, "customers": rows.values.tolist(), "km": km, "threshold": m["threshold"]["chosen"],
        "drivers": {"label": drivers.label.tolist(), "effect": drivers.effect.round(4).tolist(), "measure": drivers.effect_measure.tolist()},
        "thresholdCurve": {"threshold": curve.threshold.tolist(), "net": curve.net_value.round(0).tolist()},
        "lift": {"decile": lift.decile.tolist(), "lift": lift.lift.round(3).tolist()},
    }
    g = m["campaign"]["groups"]["model"]
    headline = (f"{pct(a['kpi']['churn_rate'])} of {a['kpi']['customers']:,} customers churned, taking {usd(a['kpi']['mrr_lost'])} of monthly "
                f"revenue. Offering the {g['customers']:,} customers above a {pct(m['threshold']['chosen'], 0)} predicted risk a "
                f"{m['campaign_assumptions']['offer_discount_pct']}%-off deal is worth about {usd(g['net_value'])} net over "
                f"{m['campaign_assumptions']['value_horizon_months']} months; it breaks even if the offer saves "
                f"{pct(g['breakeven_save_rate'])} of would-be churners.")
    html = (DASHBOARD.parent / "template.html").read_text(encoding="utf-8")
    html = (html.replace("{{HEADLINE}}", headline).replace("{{REPO_URL}}", REPO_URL).replace("{{GENERATED}}", date.today().isoformat())
            .replace("{{N_CUSTOMERS}}", f"{a['kpi']['customers']:,}")
            .replace("/*DATA*/", json.dumps(data, separators=(",", ":"))).replace("/*PLOTLY*/", get_plotlyjs()))
    DASHBOARD.write_text(html, encoding="utf-8")
    DOCS.mkdir(exist_ok=True)
    shutil.copy2(DASHBOARD, DOCS / "index.html")
    (DOCS / ".nojekyll").write_text("", encoding="utf-8")
    checks = {"customers": len(rows), "churned": int(rows.y.sum()), "mrr_lost": float((rows.mc * rows.y).sum()),
              "size_mb": round(len(html.encode()) / 1e6, 2), "headline": headline}
    facts.update("dashboard", checks)
    print(f"dashboard: wrote {DASHBOARD.name} ({checks['size_mb']} MB), {len(rows):,} customers")
    return checks


if __name__ == "__main__":
    build()
