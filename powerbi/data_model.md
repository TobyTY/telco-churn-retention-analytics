# Power BI data model

Small model: one customer table at customer grain plus two helper tables.

## Export the tables

```bash
python -m src.powerbi_export     # writes powerbi/export/*.csv after `make all`
```

| Table | Grain | Source | Use |
|---|---|---|---|
| `customers` | one row per customer | `stg_customers` joined to `model_scores` | All measures; slicers on contract, internet, payment, tenure band, risk band |
| `segment_churn` | one row per (dimension, segment) | `reports/segment_churn.csv` | Pre-computed rates and Wilson intervals for the deep-dive page |
| `lift` | one row per test-set risk decile | `reports/lift_table.csv` | Lift and cumulative gains visuals |
| `km_curve` | one row per (contract, tenure month) | `reports/km_curves.json` flattened | Kaplan-Meier line chart |

No relationships are needed: `segment_churn`, `lift` and `km_curve` are standalone helper tables and should not be filtered by the customer slicers
(set **Edit interactions** to *None* for those visuals).

## What-if parameters (Modeling > New parameter > Numeric range)

| Parameter | Min | Max | Increment | Default |
|---|---|---|---|---|
| Threshold | 0.05 | 0.95 | 0.01 | value of `model.threshold.chosen` in `reports/facts.json` |
| Save Rate | 0 | 1 | 0.05 | `model.campaign_assumptions.save_rate` |
| Discount | 0 | 0.5 | 0.05 | `offer_discount_pct` / 100 |
| Discount Months | 1 | 24 | 1 | `offer_months` |
| Contact Cost | 0 | 50 | 1 | `contact_cost` |
| Horizon Months | 1 | 36 | 1 | `value_horizon_months` |

Each parameter creates a `<Name> Value` measure used in `measures.dax`.
