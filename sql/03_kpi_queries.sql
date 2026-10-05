-- 03_kpi_queries.sql
-- Named queries run by src/warehouse.py; results go to reports/sql_outputs/<name>.csv and are
-- cross-checked against the Python pipeline in tests/.

-- name: headline_kpis
-- Q: How big is the churn problem?
-- Logic: one row; MRR = sum of monthly charges; lost = MRR of churned customers; annualised = x12.
SELECT COUNT(*)                                         AS customers,
       SUM(churned)                                     AS churned,
       AVG(churned)                                     AS churn_rate,
       SUM(monthly_charges)                             AS mrr_total,
       SUM(monthly_charges * churned)                   AS mrr_lost,
       SUM(monthly_charges * churned) * 12              AS annual_revenue_lost,
       SUM(monthly_charges * churned) / SUM(monthly_charges) AS mrr_lost_share,
       AVG(monthly_charges)                             AS avg_monthly_charges,
       AVG(CASE WHEN churned = 1 THEN monthly_charges END) AS avg_charges_churned,
       AVG(CASE WHEN churned = 0 THEN monthly_charges END) AS avg_charges_retained,
       AVG(tenure_months)                               AS avg_tenure
FROM stg_customers;

-- name: churn_by_segment
-- Q: Churn rate and revenue lost for every segment of every dimension.
SELECT * FROM v_churn_by_segment ORDER BY dimension, rank_in_dimension;

-- name: revenue_at_risk_top10
-- Q: Which contract x internet x tenure segments lose the most revenue?
SELECT * FROM v_revenue_at_risk WHERE loss_rank <= 10 ORDER BY loss_rank;

-- name: tenure_curve
-- Q: Retention curve by tenure month (manual Kaplan-Meier from running sums).
SELECT * FROM v_tenure_curve;

-- name: charge_deciles
-- Q: Churn by monthly-charge decile.
SELECT * FROM v_charge_deciles ORDER BY charge_decile;

-- name: month_to_month_new_fiber
-- Q: How does the highest-risk profile compare with the base?
-- Logic: month-to-month contract, fiber optic, first year of tenure vs everyone else.
SELECT CASE WHEN contract = 'Month-to-month' AND internet_service = 'Fiber optic' AND tenure_months <= 12
            THEN 'M2M + fiber + first year' ELSE 'Everyone else' END AS profile,
       COUNT(*) AS customers, AVG(churned) AS churn_rate, SUM(monthly_charges * churned) AS mrr_lost
FROM stg_customers GROUP BY 1 ORDER BY 1;

-- name: risk_bands
-- Q: How do the model's risk bands perform? (model_scores is written back by src/model.py)
SELECT risk_band, COUNT(*) AS customers, AVG(churned) AS actual_churn_rate, AVG(churn_probability) AS avg_probability,
       SUM(monthly_charges) AS mrr, SUM(monthly_charges * churn_probability) AS expected_mrr_at_risk
FROM model_scores GROUP BY 1 ORDER BY 1;
