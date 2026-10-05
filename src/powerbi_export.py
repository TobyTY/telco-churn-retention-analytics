"""Export the customer table (with model scores) and helper tables to powerbi/export/*.csv."""
from __future__ import annotations

import json
import shutil

import pandas as pd

from src.config import REPORTS, ROOT
from src.warehouse import connect

OUT = ROOT / "powerbi" / "export"


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    with connect(read_only=True) as con:
        con.execute(f"""COPY (SELECT c.*, s.churn_probability, s.risk_band, s.targeted
                              FROM stg_customers c JOIN model_scores s USING (customer_id))
                        TO '{(OUT / 'customers.csv').as_posix()}' (HEADER, DELIMITER ',')""")
    for name in ["segment_churn", "drivers"]:
        shutil.copy2(REPORTS / f"{name}.csv", OUT / f"{name}.csv")
    shutil.copy2(REPORTS / "lift_table.csv", OUT / "lift.csv")
    km = json.loads((REPORTS / "km_curves.json").read_text(encoding="utf-8"))
    rows = [{"contract": c, "tenure_month": t, "survival": s} for c, v in km.items() for t, s in zip(v["timeline"], v["survival"])]
    pd.DataFrame(rows).to_csv(OUT / "km_curve.csv", index=False)
    print(f"powerbi_export: wrote {len(list(OUT.glob('*.csv')))} files to {OUT}")


if __name__ == "__main__":
    main()
