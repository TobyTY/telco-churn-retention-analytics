"""Data audit of the raw Telco table: nulls, dtypes, duplicates, domains, ranges and outliers.

Writes reports/audit_table.csv (one row per column) and reports/audit_checks.csv (one row per check).
"""
from __future__ import annotations

import pandas as pd

from src.config import REPORTS
from src.warehouse import connect

CHECKS = {
    "duplicate customerID": "SELECT COUNT(*) - COUNT(DISTINCT customerID) FROM raw.customers",
    "blank TotalCharges": "SELECT COUNT(*) FROM raw.customers WHERE TotalCharges IS NULL OR trim(TotalCharges) = ''",
    "blank TotalCharges with tenure > 0": "SELECT COUNT(*) FROM raw.customers WHERE (TotalCharges IS NULL OR trim(TotalCharges) = '') AND tenure > 0",
    "Churn not in (Yes, No)": "SELECT COUNT(*) FROM raw.customers WHERE Churn NOT IN ('Yes', 'No')",
    "tenure outside 0-72": "SELECT COUNT(*) FROM raw.customers WHERE tenure < 0 OR tenure > 72",
    "MonthlyCharges <= 0": "SELECT COUNT(*) FROM raw.customers WHERE MonthlyCharges <= 0",
    "TotalCharges below MonthlyCharges (tenure >= 1)":
        "SELECT COUNT(*) FROM raw.customers WHERE tenure >= 1 AND TRY_CAST(TotalCharges AS DOUBLE) < MonthlyCharges - 0.01",
    "TotalCharges more than 20% away from tenure x MonthlyCharges":
        "SELECT COUNT(*) FROM raw.customers WHERE tenure >= 1 AND abs(TRY_CAST(TotalCharges AS DOUBLE) - tenure * MonthlyCharges) > 0.2 * tenure * MonthlyCharges",
    "internet add-on set while InternetService = 'No'":
        "SELECT COUNT(*) FROM raw.customers WHERE InternetService = 'No' AND (OnlineSecurity <> 'No internet service' OR TechSupport <> 'No internet service')",
    "MultipleLines set while PhoneService = 'No'":
        "SELECT COUNT(*) FROM raw.customers WHERE PhoneService = 'No' AND MultipleLines <> 'No phone service'",
}


def run() -> tuple[pd.DataFrame, pd.DataFrame]:
    with connect(read_only=True) as con:
        df = con.execute("SELECT * FROM raw.customers").df()
        checks = pd.DataFrame([{"check": k, "count": int(con.execute(v).fetchone()[0])} for k, v in CHECKS.items()])
    rows = []
    for col in df.columns:
        s = df[col]
        row = {"column": col, "dtype": str(s.dtype), "nulls": int(s.isna().sum()),
               "blank_strings": int((s.astype(str).str.strip() == "").sum()), "distinct": int(s.nunique()),
               "min": None, "max": None, "iqr_outliers": None, "top_values": None}
        if pd.api.types.is_numeric_dtype(s):
            q1, q3 = s.quantile([0.25, 0.75])
            iqr = q3 - q1
            row.update(min=s.min(), max=s.max(), iqr_outliers=int(((s < q1 - 1.5 * iqr) | (s > q3 + 1.5 * iqr)).sum()))
        elif s.nunique() <= 6:
            row["top_values"] = "; ".join(f"{k}={v}" for k, v in s.value_counts().items())
        rows.append(row)
    profile = pd.DataFrame(rows).astype({"min": object, "max": object, "iqr_outliers": object})
    profile.to_csv(REPORTS / "audit_table.csv", index=False)
    checks.to_csv(REPORTS / "audit_checks.csv", index=False)
    print(f"audit: profiled {len(profile)} columns; {len(checks)} checks")
    return profile, checks


if __name__ == "__main__":
    run()
