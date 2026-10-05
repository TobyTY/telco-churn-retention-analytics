"""Fetch the IBM Telco Customer Churn CSV into data/raw, trying sources in order.

Source order: (a) IBM's public GitHub repository, (b) Kaggle `blastchar/telco-customer-churn`
via kagglehub. A source is accepted only if it has the 21 expected columns, a row count within
20% of 7,043 and a non-null key column.
"""
from __future__ import annotations

import json
import shutil
import sys
from datetime import date
from pathlib import Path

import pandas as pd
import requests

from src.config import RAW_FILE

IBM_URL = "https://raw.githubusercontent.com/IBM/telco-customer-churn-on-icp4d/master/data/Telco-Customer-Churn.csv"
KAGGLE_HANDLE = "blastchar/telco-customer-churn"
EXPECTED_ROWS = 7043
COLUMNS = ["customerID", "gender", "SeniorCitizen", "Partner", "Dependents", "tenure", "PhoneService", "MultipleLines",
           "InternetService", "OnlineSecurity", "OnlineBackup", "DeviceProtection", "TechSupport", "StreamingTV",
           "StreamingMovies", "Contract", "PaperlessBilling", "PaymentMethod", "MonthlyCharges", "TotalCharges", "Churn"]
LICENCE = "Apache License 2.0 (IBM telco-customer-churn-on-icp4d repository); IBM sample data set"


def validate(path: Path) -> list[str]:
    if not path.exists():
        return ["file missing"]
    df = pd.read_csv(path, dtype=str)
    problems = []
    missing = [c for c in COLUMNS if c not in df.columns]
    if missing:
        problems.append(f"missing columns {missing}")
    if not (0.8 * EXPECTED_ROWS <= len(df) <= 1.2 * EXPECTED_ROWS):
        problems.append(f"{len(df)} rows, expected about {EXPECTED_ROWS}")
    if "customerID" in df and df.customerID.isna().mean() > 0.5:
        problems.append("customerID mostly null")
    return problems


def from_ibm() -> str:
    r = requests.get(IBM_URL, timeout=60)
    r.raise_for_status()
    RAW_FILE.write_bytes(r.content)
    return IBM_URL


def from_kaggle() -> str:
    import kagglehub

    src = Path(kagglehub.dataset_download(KAGGLE_HANDLE))
    shutil.copy2(next(src.glob("*.csv")), RAW_FILE)
    return f"https://www.kaggle.com/datasets/{KAGGLE_HANDLE}"


def main() -> int:
    meta_path = RAW_FILE.parent / "_source.json"
    if meta_path.exists() and not validate(RAW_FILE):
        print("download: raw data already present and valid")
        return 0
    for label, fn in (("ibm-github", from_ibm), ("kaggle", from_kaggle)):
        for attempt in range(1, 4):
            try:
                url = fn()
                problems = validate(RAW_FILE)
                if problems:
                    raise ValueError("; ".join(problems))
                meta = {"source": label, "url": url, "licence": LICENCE, "retrieved": date.today().isoformat(),
                        "files": [RAW_FILE.name], "rows": int(len(pd.read_csv(RAW_FILE)))}
                meta_path.write_text(json.dumps(meta, indent=2), encoding="utf-8")
                print(f"download: OK from {label} ({url})")
                return 0
            except Exception as exc:  # noqa: BLE001 - log and try again / next source
                print(f"download: {label} attempt {attempt} failed: {exc}", file=sys.stderr)
    print("download: every source failed", file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
