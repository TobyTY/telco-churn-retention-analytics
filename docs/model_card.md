# Model card: churn risk score

**Purpose.** Rank customers by probability of churning so a retention offer can be targeted. Not for pricing or credit decisions.

**Data.** IBM Telco Customer Churn sample, 7,043 customers, churn rate 26.5%.

## Protocol

| Item | Choice |
|---|---|
| Split | Stratified train/test, 5,282 / 1,761 customers, seed 42 (train churn 26.5%, test 26.5%) |
| Model selection | 5-fold stratified CV ROC-AUC on the training set only |
| Features | 20 raw fields: tenure, monthly and total charges, add-on count, five yes/no flags, eleven categorical fields (one-hot) |
| Excluded | `customer_id` (identifier), `churned` (target), `tenure_band` (derived from tenure_months), `charges_band` (derived from monthly_charges) |
| Imbalance | Stratification, PR-AUC, cost-based threshold; class-weighted variant reported for comparison |
| Threshold | 0.35, maximising campaign net value on out-of-fold training predictions |

## Results

| Model | CV ROC-AUC (sd) | CV PR-AUC | Test ROC-AUC | Test PR-AUC | Precision / recall / F1 at 0.5 | Brier |
|---|---|---|---|---|---|---|
| Logistic regression | 0.844 (0.015) | 0.661 | 0.847 | 0.638 | 0.66 / 0.55 / 0.60 | 0.136 |
| Logistic regression (class-weighted) | 0.844 (0.015) | 0.659 | 0.846 | 0.636 | 0.52 / 0.80 / 0.63 | 0.166 |
| Random forest | 0.843 (0.013) | 0.659 | 0.843 | 0.645 | 0.65 / 0.48 / 0.55 | 0.136 |
| Gradient boosting | 0.838 (0.013) | 0.657 | 0.839 | 0.645 | 0.66 / 0.50 / 0.57 | 0.138 |

Chosen: **Logistic regression**. The tree ensembles did not beat the logistic-regression baseline, so the baseline is used.

At the campaign threshold on the test set: precision 55.1%, recall 71.7%, F1 0.62,
34.5% of customers targeted. Calibration: mean predicted 26.6% vs actual 26.5%;
largest decile gap 5.0%.

## Leakage checks

| Check | Result |
|---|---|
| Customers in both train and test | 0 |
| Test rows whose features exactly match a training row | 15 (common plan profiles of different customers; labels can differ) |
| Shuffled-label control, test ROC-AUC | 0.523 (chance = 0.5) |
| Strongest single feature ROC-AUC | 0.740 (`tenure_months`) |
| Test ROC-AUC with / without `total_charges` | 0.847 / 0.845 |
| Preprocessing fitted inside the pipeline | True |

The shuffled-label and single-feature checks are also assertions in `src/model.py`: the build fails if either signals leakage.

## Plain-language drivers

Odds ratios from the logistic regression (numeric features standardised, so they compare one standard deviation):
`cat__internet_service_Fiber optic` x1.78, `num__total_charges` x1.73, `cat__contract_Month-to-month` x1.68, `bool__paperless_billing` x1.50, `bool__is_senior` x1.20 raise churn odds;
`num__tenure_months` x0.29, `cat__contract_Two year` x0.46, `cat__internet_service_DSL` x0.50, `num__monthly_charges` x0.55, `cat__device_protection_No internet service` x0.73 lower them.
Tenure, monthly charges and total charges are correlated, so read their individual coefficients with care; the univariate statistics in the README are
the safer explanation for business readers.

Permutation importance (drop in test ROC-AUC when shuffled): tenure_months 0.179, internet_service 0.039, contract 0.037, monthly_charges 0.031, total_charges 0.014.
