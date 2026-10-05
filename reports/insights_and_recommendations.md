# Insights and recommendations

Each insight: finding, evidence (values from `reports/facts.json`), why it matters, action, and impact with assumptions.
Real data: IBM Telco Customer Churn sample, 7,043 customers.

---

## 1. Contract length is the biggest lever

- **Finding.** Month-to-month customers churn far more than contract customers.
- **Evidence.** 42.7% vs 11.3% (one year) and 2.8% (two year), 95% intervals
  do not overlap; Cramer's V 0.41. Month-to-month is 55% of customers and 87% of lost revenue.
- **So what.** Commitment, not price alone, is what keeps customers.
- **Action.** Offer month-to-month customers an annual plan at renewal with a loyalty discount; make it the default in the sales flow.
- **Impact.** Not sized separately; it is the mechanism behind the campaign below (98% of the target list is month-to-month).

## 2. Churn is decided in the first year

- **Finding.** Most churn happens early.
- **Evidence.** 55% of churners left within twelve months; first-year churn is 47.4% vs 9.5%
  after four years. Kaplan-Meier: 70% of month-to-month customers are still active after a year.
- **So what.** Onboarding is a retention function.
- **Action.** First-quarter programme for new fiber customers: setup call, a service check after the first bill, proactive support contact.
- **Impact.** Included in the campaign sizing (58% of targeted customers are in their first year).

## 3. One segment carries 38% of lost revenue

- **Finding.** New month-to-month fiber customers are the leak.
- **Evidence.** 916 customers (13%), churn 70%,
  $53.2k of monthly revenue lost.
- **So what.** A simple rule finds the worst segment without a model.
- **Action.** Target this rule group first if the model cannot be deployed yet.
- **Impact.** $96.6k net at default assumptions, ROI 102% (the best ROI of any group).

## 4. Electronic-check payers churn at 3.0 times the rate of automatic card payers

- **Finding.** Payment method separates churners.
- **Evidence.** Electronic check 45.3% vs automatic credit card 15.2%; 65% of the target list pays by electronic check.
- **So what.** Manual payment is a monthly decision point to leave; it may also signal lower engagement.
- **Action.** Incentivise switching to automatic payment (one-off bill credit). Test it; the link may not be causal.
- **Impact.** Not sized: needs an experiment.

## 5. Support services protect customers

- **Finding.** Customers with tech support or online security churn much less.
- **Evidence.** No tech support 41.6% vs with tech support 15.2%; churn falls with every add-on held
  (52% for internet customers with none, 10% with five or more).
- **So what.** Add-ons are a retention tool, not just upsell revenue.
- **Action.** Bundle tech support into fiber plans for the first six months.
- **Impact.** Not sized separately.

## 6. A simple model ranks risk well enough to make a campaign pay

- **Finding.** Logistic regression is as good as tree ensembles here.
- **Evidence.** CV ROC-AUC logistic regression 0.844; logistic regression (class-weighted) 0.844; random forest 0.843; gradient boosting 0.838.
  Test ROC-AUC 0.847, PR-AUC 0.638; top-decile lift 2.8x.
- **So what.** The explainable model is the right one to deploy; the fancier models did not beat it and were not tuned until they did.
- **Action.** Score customers monthly; refresh the target list.
- **Impact.** See insight 7.

## 7. Target by risk, not by blanket offer

- **Finding.** Only a targeted campaign makes money.
- **Evidence.** Threshold 0.35 (chosen on training folds) targets 2,356 customers: saved revenue $374k,
  cost $231k, net $143k, break-even save rate 18.5%. Everyone: net -$81.7k.
- **So what.** Discounts given to loyal customers are pure cost.
- **Action.** Launch the offer for the model's target list; hold out a random control half.
- **Impact.** $143k net over 12 months at a 30% save rate ($18.2k at
  20%, $267k at 40%). Assumptions: 20% discount for
  6 months taken by every targeted customer, $5.00 contact cost, 12 months of revenue per saved customer.
