"""Build data/warehouse.duckdb from the raw CSV and run the named KPI queries.

Runs sql/00..02, then every `-- name:` block in sql/03_kpi_queries.sql except the ones that
need model scores (run later by src/model.py), saving each result to reports/sql_outputs/.
"""
from __future__ import annotations

import re

import duckdb
import pandas as pd

from src.config import DATA_RAW, DB_PATH, SQL_DIR, SQL_OUT

BUILD_FILES = ["00_schema.sql", "01_staging_clean.sql", "02_analysis_views.sql"]
POST_MODEL = {"risk_bands"}


def connect(read_only: bool = False) -> duckdb.DuckDBPyConnection:
    return duckdb.connect(str(DB_PATH), read_only=read_only)


def named_queries(path=SQL_DIR / "03_kpi_queries.sql") -> dict[str, str]:
    blocks = re.split(r"^-- name:\s*(\w+)\s*$", path.read_text(encoding="utf-8"), flags=re.M)
    return {blocks[i]: blocks[i + 1].strip().rstrip(";") for i in range(1, len(blocks), 2)}


def run_query(con, name: str) -> pd.DataFrame:
    df = con.execute(named_queries()[name]).df()
    df.to_csv(SQL_OUT / f"{name}.csv", index=False)
    return df


def build() -> None:
    if DB_PATH.exists():
        DB_PATH.unlink()
    with connect() as con:
        for f in BUILD_FILES:
            con.execute((SQL_DIR / f).read_text(encoding="utf-8").replace("${RAW}", DATA_RAW.as_posix()))
            print(f"warehouse: ran {f}")
        names = [n for n in named_queries() if n not in POST_MODEL]
        for name in names:
            run_query(con, name)
        n_raw, n_stg = con.execute("SELECT (SELECT COUNT(*) FROM raw.customers), (SELECT COUNT(*) FROM stg_customers)").fetchone()
    print(f"warehouse: raw.customers {n_raw:,}, stg_customers {n_stg:,}; saved {len(names)} KPI query outputs")


if __name__ == "__main__":
    build()
