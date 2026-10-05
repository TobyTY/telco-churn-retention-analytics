"""Generate and execute the four notebooks so they ship with outputs.

The notebooks call the same src/ modules as the pipeline, so there is one implementation of every calculation.
"""
from __future__ import annotations

import nbformat
from nbclient import NotebookClient
from nbformat.v4 import new_code_cell, new_markdown_cell, new_notebook

from src.config import ROOT

SETUP = """import json, pandas as pd
from IPython.display import Image, display
pd.set_option("display.max_columns", 30); pd.set_option("display.width", 160)
facts = json.load(open("reports/facts.json", encoding="utf-8"))"""

NOTEBOOKS = {
    "01_audit.ipynb": [
        new_markdown_cell("# 01 Audit\nNulls, blank strings, dtypes, duplicates, domains and outliers in the raw Telco table (`src/audit.py`)."),
        new_code_cell(SETUP + "\nfrom src import audit\nprofile, checks = audit.run()\nchecks"),
        new_code_cell("profile"),
        new_markdown_cell("**Read-out.** The only defect is blank `TotalCharges` for tenure-0 customers; a minority of rows have lifetime charges "
                          "that differ from tenure x monthly charges, which plan changes explain. Both are handled in `02_cleaning`."),
    ],
    "02_cleaning.ipynb": [
        new_markdown_cell("# 02 Cleaning\n`src/clean.py` is independent of the SQL staging layer; this notebook re-runs it and compares the two."),
        new_code_cell(SETUP + "\nfrom src import clean\ndf, log = clean.build()\nlog"),
        new_code_cell("from src.warehouse import connect\nwith connect(read_only=True) as con:\n"
                      "    sql = con.execute('SELECT COUNT(*) n, AVG(churned) churn_rate, SUM(monthly_charges*churned) mrr_lost, SUM(total_charges) total FROM stg_customers').df()\n"
                      "py = pd.DataFrame({'n': [len(df)], 'churn_rate': [df.churned.mean()], 'mrr_lost': [(df.monthly_charges*df.churned).sum()], 'total': [df.total_charges.sum()]})\n"
                      "pd.concat({'SQL stg_customers': sql, 'Python customers_clean': py})"),
    ],
    "03_eda.ipynb": [
        new_markdown_cell("# 03 Exploratory analysis\nChart titles state the finding (`src/eda.py`)."),
        new_code_cell(SETUP + "\nfrom src import eda\nout = eda.run()\nfor fig in out['figures']:\n    display(Image(filename=f'reports/figures/{fig}'))"),
    ],
    "04_analysis.ipynb": [
        new_markdown_cell("# 04 Statistics and modelling\nSegments with Wilson intervals, driver tests, Kaplan-Meier (`src/analysis.py`); model comparison, "
                          "leakage checks, lift and campaign economics (`src/model.py`)."),
        new_code_cell(SETUP + "\nfrom src import analysis\na = analysis.run()\npd.read_csv('reports/segment_churn.csv').query('dimension in [\"contract\", \"tenure_band\", \"payment_method\"]')"),
        new_code_cell("display(Image(filename='reports/figures/01_churn_by_segment.png'))\npd.read_csv('reports/drivers.csv')"),
        new_code_cell("display(Image(filename='reports/figures/04_kaplan_meier_contract.png'))\npd.Series(a['survival'])"),
        new_markdown_cell("## Models\nStratified split, CV on train only, test touched once. The tree models are kept in the table even though they do not win."),
        new_code_cell("from src import model\nm = model.run()\npd.read_csv('reports/model_comparison.csv')"),
        new_code_cell("display(Image(filename='reports/figures/09_model_curves.png'))\npd.Series(m['leakage'])"),
        new_markdown_cell("## Lift and campaign economics"),
        new_code_cell("display(Image(filename='reports/figures/12_lift_gains.png'))\ndisplay(Image(filename='reports/figures/11_threshold_net_value.png'))\n"
                      "pd.DataFrame(m['campaign']['groups']).T"),
    ],
}


def build() -> None:
    nb_dir = ROOT / "notebooks"
    nb_dir.mkdir(exist_ok=True)
    for name, cells in NOTEBOOKS.items():
        nb = new_notebook(cells=cells, metadata={"kernelspec": {"name": "python3", "display_name": "Python 3", "language": "python"}})
        NotebookClient(nb, timeout=900, kernel_name="python3", resources={"metadata": {"path": str(ROOT)}}).execute()
        nbformat.write(nb, nb_dir / name)
        print(f"notebooks: executed {name}")


if __name__ == "__main__":
    build()
