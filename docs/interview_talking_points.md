# Interview talking points

## 60-second pitch

"I took IBM's Telco churn data, 7,043 customers with a 26.5% churn rate, and turned it into a retention budget decision.
SQL in DuckDB for churn by segment and revenue at risk, chi-square and Cramer's V to rank drivers, Kaplan-Meier for retention by contract. Then I compared
logistic regression, random forest and gradient boosting with stratified cross-validation; the logistic regression won, so I kept the simple model. The key
step was choosing the targeting threshold from campaign economics instead of using 0.5. At a 35% risk threshold the offer reaches
2,356 customers and is worth about $143k net; it breaks even at a 18.5% save rate, and a blanket offer
would lose money. Everything is in a live dashboard and an Excel ROI calculator where the assumptions can be changed."

## Five hard questions

**1. Why not just use the best-scoring model, or tune the forest until it wins?**
Because none of them is meaningfully better: CV ROC-AUC differs by 0.006 between the best and worst model,
well inside one standard deviation across folds (0.015). Tuning until the complex model wins on the same folds is overfitting the evaluation. The logistic regression is
explainable to a retention manager and its probabilities are calibrated (Brier 0.136).

**2. How do you know there is no leakage?**
I excluded the ID and derived bands, kept preprocessing inside the pipeline, checked train and test share no customers, and ran a shuffled-label control:
test ROC-AUC 0.523, which is chance. The strongest single feature reaches only 0.740. `TotalCharges` grows with tenure, so I
re-ran without it: ROC-AUC 0.845 vs 0.847. Nothing is doing suspicious work.

**3. You handled class imbalance without re-weighting. Why?**
About one customer in four churns, which is imbalanced but not extreme. Re-weighting moves the probabilities away from reality, and the revenue-at-risk numbers
need real probabilities. So I stratified the split, reported PR-AUC, and moved the decision threshold using costs. I show the class-weighted model too: same
ROC-AUC, higher recall at 0.5, worse calibration.

**4. Your save rate is an assumption. Isn't the whole answer made up?**
The sizing depends on it, which is why I report the break-even point: the campaign pays if it saves more than 18.5% of would-be churners.
Net value goes from $18.2k at a 20% save rate to $267k at 40%.
The recommendation is to measure it with a randomised pilot, then update the calculator.

**5. Is a "churn rate" from a snapshot meaningful?**
It is the share of this customer base that left in the observed period, which is enough to rank segments and size a campaign on a base like this one. What it
cannot do is give a monthly trend or seasonality; for that I would need repeated snapshots. Kaplan-Meier on tenure is the closest I can get to a retention curve.

## Three things I would do differently

1. **Uplift modelling.** The model predicts who will churn, not who the offer will change; with pilot data I would model the treatment effect directly.
2. **Margin instead of revenue.** Customer value should be contribution margin over expected lifetime, not twelve months of charges.
3. **Repeated snapshots.** Monthly snapshots would allow time-based validation (train on earlier months, test on later), which is stricter than a random split.
