# Project brief: customer churn and retention analytics

## Problem

Customers leave every month. The business wants to know who churns, why, what it costs, and how a limited retention budget
should be spent: on whom, with what offer, and at what point the offer stops paying for itself.

## Stakeholders

| Stakeholder | What they need |
|---|---|
| Head of Customer / Retention | Who to target and the expected return of a campaign |
| Finance | Revenue at risk, campaign cost, break-even |
| Product and Pricing | Which plans and contract terms drive churn |
| Customer Care | A ranked call list and the reasons behind each customer's risk |
| Data team | A model that is validated, explainable and free of leakage |

## Business questions

1. What is the churn rate overall and by tenure, contract, payment method, services and charges?
2. How much revenue is at risk, and in which segments?
3. Which factors are the statistically strongest churn drivers?
4. How well can churn risk be scored, and what is the score worth to the business?
5. What is the campaign break-even, and which target group gives the best return?

## KPI definitions

| KPI | Definition |
|---|---|
| Churn rate | Churned customers / all customers |
| Segment churn rate | Same, within a segment, with a Wilson 95% interval |
| MRR | Sum of `MonthlyCharges` |
| Revenue lost | MRR of churned customers (monthly and annualised) |
| Expected MRR at risk | Sum over customers of churn probability x monthly charges |
| Lift | Churn rate in a risk decile / overall churn rate |
| Campaign net value | Revenue kept from saved churners minus offer and contact cost |
| Break-even save rate | Campaign cost / (churner MRR x horizon months) |

## Success criteria

- Every question answered with a number, an interval or test where relevant, and a chart.
- Models compared on the same cross-validation folds; test set used once; leakage checks recorded and asserted.
- Headline recommendation names the group, the offer, the saved revenue and the break-even point, with assumptions stated.
- SQL, Python, Excel and dashboard agree on churn rate and revenue lost; `make all` rebuilds everything.
