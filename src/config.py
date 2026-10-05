"""Paths and analysis constants shared by every pipeline step."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA_RAW = ROOT / "data" / "raw"
DATA_PROCESSED = ROOT / "data" / "processed"
RAW_FILE = DATA_RAW / "Telco-Customer-Churn.csv"
DB_PATH = ROOT / "data" / "warehouse.duckdb"
SQL_DIR = ROOT / "sql"
REPORTS = ROOT / "reports"
FIGURES = REPORTS / "figures"
SQL_OUT = REPORTS / "sql_outputs"
FACTS = REPORTS / "facts.json"
TEMPLATES = ROOT / "templates"
DOCS = ROOT / "docs"
EXCEL_PATH = ROOT / "excel" / "retention_campaign_roi.xlsx"
DASHBOARD = ROOT / "dashboard" / "index.html"

SEED = 42
TEST_SIZE = 0.25

GITHUB_USER = "TobyTY"
REPO_NAME = "telco-churn-retention-analytics"
PAGES_URL = f"https://{GITHUB_USER.lower()}.github.io/{REPO_NAME}/"
REPO_URL = f"https://github.com/{GITHUB_USER}/{REPO_NAME}"

for p in (DATA_RAW, DATA_PROCESSED, FIGURES, SQL_OUT):
    p.mkdir(parents=True, exist_ok=True)
