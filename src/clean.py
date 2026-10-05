"""Python cleaning layer, written independently of sql/01_staging_clean.sql.

Produces data/processed/customers_clean.parquet and logs every decision with its row
impact to reports/cleaning_log.csv. tests/test_metrics.py checks it against stg_customers.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from src.config import DATA_PROCESSED, RAW_FILE, REPORTS

YES_NO = ["Partner", "Dependents", "PhoneService", "PaperlessBilling"]
ADDONS = ["OnlineSecurity", "OnlineBackup", "DeviceProtection", "TechSupport", "StreamingTV", "StreamingMovies"]


def build() -> tuple[pd.DataFrame, pd.DataFrame]:
    log: list[dict] = []

    def add(action, before, after, affected, why):
        log.append({"step": len(log) + 1, "action": action, "rows_before": before, "rows_after": after,
                    "rows_affected": affected, "decision": why})

    df = pd.read_csv(RAW_FILE, dtype={"TotalCharges": str})
    n = len(df)
    df = df.drop_duplicates("customerID")
    add("Drop duplicate customerID", n, len(df), n - len(df), "One row per customer is required for churn rates.")

    obj = df.select_dtypes("object").columns
    df[obj] = df[obj].apply(lambda s: s.str.strip())
    blank = df.TotalCharges.eq("") | df.TotalCharges.isna()
    add("Set blank TotalCharges to 0", len(df), len(df), int(blank.sum()),
        f"All {int(blank.sum())} blanks have tenure 0: new customers not yet billed, so 0 is the true value.")
    df["TotalCharges"] = pd.to_numeric(df.TotalCharges.where(~blank, "0"))

    df["churned"] = (df.Churn == "Yes").astype(int)
    add("Encode Churn Yes/No as 1/0", len(df), len(df), int(df.churned.sum()), "Target for rates and models.")
    for c in YES_NO:
        df[c] = df[c] == "Yes"
    df["SeniorCitizen"] = df.SeniorCitizen == 1
    df["n_addons"] = (df[ADDONS] == "Yes").sum(axis=1)
    df["tenure_band"] = pd.cut(df.tenure, [-1, 12, 24, 48, 72],
                               labels=["00-12 months", "13-24 months", "25-48 months", "49-72 months"]).astype(str)
    df["charges_band"] = pd.cut(df.MonthlyCharges, [0, 35, 70, 90, np.inf], right=False,
                                labels=["1. under $35", "2. $35-70", "3. $70-90", "4. $90+"]).astype(str)
    add("Add tenure and monthly-charge bands", len(df), len(df), 0, "Readable segments for reporting; models use the raw numbers.")
    gap = (df.tenure > 0) & ((df.TotalCharges - df.tenure * df.MonthlyCharges).abs() > 0.2 * df.tenure * df.MonthlyCharges)
    add("Keep TotalCharges that differ from tenure x MonthlyCharges by more than 20%", len(df), len(df), int(gap.sum()),
        "Plan changes over a customer's life explain the gap; values are internally consistent otherwise.")

    df = df.rename(columns={"customerID": "customer_id", "SeniorCitizen": "is_senior", "Partner": "has_partner",
                            "Dependents": "has_dependents", "tenure": "tenure_months", "PhoneService": "has_phone",
                            "MultipleLines": "multiple_lines", "InternetService": "internet_service",
                            "OnlineSecurity": "online_security", "OnlineBackup": "online_backup",
                            "DeviceProtection": "device_protection", "TechSupport": "tech_support",
                            "StreamingTV": "streaming_tv", "StreamingMovies": "streaming_movies", "Contract": "contract",
                            "PaperlessBilling": "paperless_billing", "PaymentMethod": "payment_method",
                            "MonthlyCharges": "monthly_charges", "TotalCharges": "total_charges"}).drop(columns="Churn")
    log_df = pd.DataFrame(log)
    df.to_parquet(DATA_PROCESSED / "customers_clean.parquet", index=False)
    log_df.to_csv(REPORTS / "cleaning_log.csv", index=False)
    print(f"clean: {len(df):,} customers, churn rate {df.churned.mean():.4f}; {len(log_df)} logged decisions")
    return df, log_df


def load() -> pd.DataFrame:
    return pd.read_parquet(DATA_PROCESSED / "customers_clean.parquet")


if __name__ == "__main__":
    build()
