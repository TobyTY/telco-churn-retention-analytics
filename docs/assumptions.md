# Assumptions and cleaning decisions

Generated from `reports/cleaning_log.csv`, `reports/audit_checks.csv` and `reports/facts.json`.

## Definitions

- **Churned:** `Churn = Yes` (left within the last month of the snapshot).
- **Monthly recurring revenue (MRR):** `MonthlyCharges`. Revenue lost = MRR of churned customers; annualised = x12.
- **Tenure bands:** 0-12, 13-24, 25-48, 49-72 months. **Charge bands:** under $35, $35-70, $70-90, $90+.
- **Confidence intervals:** Wilson score, 95%.
- **Driver tests:** chi-square with Cramer's V (categorical), Mann-Whitney U with rank-biserial r (numeric), Bonferroni across 19 tests.

## Campaign assumptions (inputs to `src/model.py` and the Excel calculator)

| Input | Value |
|---|---|
| Discount | 20% of the monthly bill |
| Discount length | 6 months, taken by every targeted customer |
| Contact cost | $5.00 per targeted customer |
| Save rate | 30% of would-be churners retained |
| Value of a saved customer | 12 months of their monthly charges (revenue, not margin) |

Net value of targeting customer *i* = churned<sub>i</sub> x save rate x monthly charge<sub>i</sub> x horizon - (contact cost + discount x months x monthly charge<sub>i</sub>).

## Cleaning log (Python layer, `src/clean.py`)

| Step | Action | Rows before | Rows after | Rows affected | Why |
|---|---|---|---|---|---|
| 1 | Drop duplicate customerID | 7,043 | 7,043 | 0 | One row per customer is required for churn rates. |
| 2 | Set blank TotalCharges to 0 | 7,043 | 7,043 | 11 | All 11 blanks have tenure 0: new customers not yet billed, so 0 is the true value. |
| 3 | Encode Churn Yes/No as 1/0 | 7,043 | 7,043 | 1,869 | Target for rates and models. |
| 4 | Add tenure and monthly-charge bands | 7,043 | 7,043 | 0 | Readable segments for reporting; models use the raw numbers. |
| 5 | Keep TotalCharges that differ from tenure x MonthlyCharges by more than 20% | 7,043 | 7,043 | 59 | Plan changes over a customer's life explain the gap; values are internally consistent otherwise. |

The SQL staging layer (`sql/01_staging_clean.sql`) applies the same rules; `tests/test_metrics.py` checks both give identical results.

## Data audit (`src/audit.py`)

| Check | Count |
|---|---|
| duplicate customerID | 0 |
| blank TotalCharges | 11 |
| blank TotalCharges with tenure > 0 | 0 |
| Churn not in (Yes, No) | 0 |
| tenure outside 0-72 | 0 |
| MonthlyCharges <= 0 | 0 |
| TotalCharges below MonthlyCharges (tenure >= 1) | 0 |
| TotalCharges more than 20% away from tenure x MonthlyCharges | 59 |
| internet add-on set while InternetService = 'No' | 0 |
| MultipleLines set while PhoneService = 'No' | 0 |

Column-level profile: `reports/audit_table.csv`.
