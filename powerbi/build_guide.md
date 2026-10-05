# Build guide: assemble the .pbix (about two hours)

No `.pbix` is committed. The HTML dashboard (`dashboard/index.html`) shows the target result.

## 1. Export (5 min)

Run `make all`, then `python -m src.powerbi_export`. It writes `customers.csv`, `segment_churn.csv`, `lift.csv`, `km_curve.csv` and
`drivers.csv` to `powerbi/export/`.

## 2. Load (10 min)

1. **Get data** > **Text/CSV** for each file.
2. Power Query: `churned` as Whole number, `churn_probability` and `monthly_charges` as Decimal, `tenure_months` as Whole number.
3. **Close & Apply**.

## 3. Parameters (15 min)

Create the six What-if parameters listed in `data_model.md` (**Modeling** > **New parameter** > **Numeric range**), each with
**Add slicer to this page** ticked on page 3 only.

## 4. Measures (20 min)

1. **Home** > **Enter data** > table `_Measures`, no rows.
2. Add each block from `measures.dax` as a **New measure** and set the format noted in its comment.
3. Check with no slicers: `[Customers]` = README customers, `[Churn Rate]` = README churn rate, `[MRR Lost]` = README monthly revenue lost.
   With the parameters at their defaults, `[Campaign Net Value]` must equal the README net value.

## 5. Theme (2 min)

**View** > **Themes** > **Browse for themes** > `powerbi/theme.json`.

## 6. Pages (60 min)

Follow `report_layout.md`. For the deep-dive selector use **Modeling** > **New parameter** > **Fields** with contract, tenure_band,
internet_service, payment_method, tech_support and online_security. For helper-table visuals set **Format** > **Edit interactions** to *None*.

## 7. Validate (10 min)

| Check | Expected (`reports/facts.json`) |
|---|---|
| Customers | `analysis.kpi.customers` |
| Churn Rate | `analysis.kpi.churn_rate` |
| MRR Lost | `analysis.kpi.mrr_lost` |
| Targeted Customers at default threshold | `model.campaign.groups.model.customers` |
| Campaign Net Value at defaults | `model.campaign.groups.model.net_value` |

Save as `powerbi/telco_churn.pbix` (git-ignored by default).
