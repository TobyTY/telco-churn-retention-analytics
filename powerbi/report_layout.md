# Report layout (three pages, 16:9)

Slicers in one row at the top of every page: Contract, Internet service, Payment method, Tenure band, Risk band (synced across pages).

## Page 1: Churn Overview

```
+-----------+-----------+-----------+-----------+-----------------------------+
| Customers | Churned   | Churn Rate| MRR Lost  | Annual Revenue Lost         |
+-----------+-----------+-----------+-----------+-----------------------------+
| Column: Churn Rate by contract      | Column: Churn Rate by tenure band     |
| (error bars: CI Low / CI High)      |                                       |
+-------------------------------------+---------------------------------------+
| Column: Churn Rate by payment method| Line: km_curve survival by month,     |
|                                     | legend = contract (interactions off)  |
+-------------------------------------+---------------------------------------+
```

## Page 2: Segment Deep-Dive

```
+-------------------------------------+---------------------------------------+
| Field parameter selector:           | Column: MRR Lost by selected field    |
| Churn Rate by selected field        |                                       |
+-------------------------------------+---------------------------------------+
| Matrix: contract x internet_service | Bar: Cramer's V by feature            |
| values = Churn Rate, colour scale   | (drivers.csv, interactions off)       |
+-------------------------------------+---------------------------------------+
```

## Page 3: At-Risk Customers

```
+-----------+---------------+-------------+---------------------+---------------+
| Customers | Avg Churn Prob| Expected MRR| Targeted Customers  | Net Value     |
|           |               | at Risk     |                     | Break-even    |
+-----------+---------------+-------------+---------------------+---------------+
| What-if slicers: Threshold, Save Rate, Discount, Months, Contact, Horizon      |
+--------------------------------------+-----------------------------------------+
| Column: Expected MRR at Risk by band | Table: customer_id, contract, tenure,   |
|                                      | monthly_charges, churn_probability      |
|                                      | (filter churned = 0, sort desc, Top 50) |
+--------------------------------------+-----------------------------------------+
| Column: lift by decile (lift table, interactions off)                          |
+--------------------------------------------------------------------------------+
```
