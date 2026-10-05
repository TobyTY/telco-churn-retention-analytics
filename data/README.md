# Data

**Real data.** IBM Telco Customer Churn sample data set.

| Field | Value |
|---|---|
| Source used | ibm-github (https://raw.githubusercontent.com/IBM/telco-customer-churn-on-icp4d/master/data/Telco-Customer-Churn.csv) |
| Fallback | Kaggle `blastchar/telco-customer-churn` via kagglehub (`src/download.py`) |
| Licence | Apache License 2.0 (IBM telco-customer-churn-on-icp4d repository); IBM sample data set |
| Retrieved | 2026-10-06 |
| Rows | 7,043 customers, 21 columns; downloaded to `data/raw/` at build time (not committed) |

Validation on download: 21 expected columns, row count within 20% of the published size, non-null `customerID`.

## Data dictionary

| Field | Meaning |
|---|---|
| `customerID` | Customer key (excluded from models) |
| `gender`, `SeniorCitizen`, `Partner`, `Dependents` | Demographics |
| `tenure` | Months with the company (0-72) |
| `PhoneService`, `MultipleLines` | Phone products |
| `InternetService` | DSL, Fiber optic or No |
| `OnlineSecurity`, `OnlineBackup`, `DeviceProtection`, `TechSupport`, `StreamingTV`, `StreamingMovies` | Add-ons (Yes / No / No internet service) |
| `Contract` | Month-to-month, One year, Two year |
| `PaperlessBilling`, `PaymentMethod` | Billing |
| `MonthlyCharges` | Current monthly bill ($) |
| `TotalCharges` | Lifetime billed ($); blank for 11 brand-new customers |
| `Churn` | Yes = left within the last month |

## Processed outputs

- `data/warehouse.duckdb`: raw and staging tables, analysis views, `model_scores`.
- `data/processed/customers_clean.parquet`: Python cleaning layer.
- `reports/customer_scores.csv`: out-of-fold churn probability and risk band per customer (regenerated, not committed).
