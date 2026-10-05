-- 02_analysis_views.sql
-- Analysis views behind the churn questions. "Churned" = left within the last month (the dataset is a
-- snapshot). Monthly recurring revenue (MRR) = monthly_charges. Revenue lost = MRR of churned customers.

-- Q1: churn rate by every segment dimension in one long table.
-- Logic: UNION ALL one GROUP BY per dimension; RANK orders segments by churn rate within a dimension.
-- Output: dimension, segment, customers, churned, churn_rate, mrr, mrr_lost, rank_in_dimension.
CREATE OR REPLACE VIEW v_churn_by_segment AS
WITH long AS (
    SELECT 'contract' AS dimension, contract AS segment, churned, monthly_charges FROM stg_customers
    UNION ALL SELECT 'tenure_band', tenure_band, churned, monthly_charges FROM stg_customers
    UNION ALL SELECT 'internet_service', internet_service, churned, monthly_charges FROM stg_customers
    UNION ALL SELECT 'payment_method', payment_method, churned, monthly_charges FROM stg_customers
    UNION ALL SELECT 'charges_band', charges_band, churned, monthly_charges FROM stg_customers
    UNION ALL SELECT 'tech_support', tech_support, churned, monthly_charges FROM stg_customers
    UNION ALL SELECT 'online_security', online_security, churned, monthly_charges FROM stg_customers
    UNION ALL SELECT 'paperless_billing', CASE WHEN paperless_billing THEN 'Yes' ELSE 'No' END, churned, monthly_charges FROM stg_customers
    UNION ALL SELECT 'senior_citizen', CASE WHEN is_senior THEN 'Yes' ELSE 'No' END, churned, monthly_charges FROM stg_customers
    UNION ALL SELECT 'n_addons', CAST(n_addons AS VARCHAR), churned, monthly_charges FROM stg_customers
),
agg AS (
    SELECT dimension, segment,
           COUNT(*)                                   AS customers,
           SUM(churned)                               AS churned,
           AVG(churned)                               AS churn_rate,
           SUM(monthly_charges)                       AS mrr,
           SUM(monthly_charges * churned)             AS mrr_lost
    FROM long GROUP BY 1, 2
)
SELECT *,
       mrr_lost / SUM(mrr_lost) OVER (PARTITION BY dimension)            AS share_of_mrr_lost,
       RANK() OVER (PARTITION BY dimension ORDER BY churn_rate DESC)     AS rank_in_dimension
FROM agg;

-- Q2: revenue lost by the highest-churn combination of contract x internet x tenure band.
-- Logic: three-way segment, ranked by MRR lost; cumulative share shows how concentrated the loss is.
CREATE OR REPLACE VIEW v_revenue_at_risk AS
WITH seg AS (
    SELECT contract, internet_service, tenure_band,
           COUNT(*) AS customers, SUM(churned) AS churned, AVG(churned) AS churn_rate,
           SUM(monthly_charges * churned) AS mrr_lost, SUM(monthly_charges * (1 - churned)) AS mrr_active
    FROM stg_customers GROUP BY 1, 2, 3
)
SELECT *,
       ROW_NUMBER() OVER (ORDER BY mrr_lost DESC)                                         AS loss_rank,
       SUM(mrr_lost) OVER (ORDER BY mrr_lost DESC ROWS UNBOUNDED PRECEDING) / SUM(mrr_lost) OVER () AS cumulative_share_of_loss
FROM seg;

-- Q1/Q3: churn by tenure month, with a manual retention curve.
-- Logic: customers at each tenure month; churned customers leave at their tenure month (event),
--        active customers are censored there. Survival S(t) = product of (1 - events/at_risk), built with
--        running sums: at_risk(t) = customers with tenure >= t.
CREATE OR REPLACE VIEW v_tenure_curve AS
WITH by_t AS (
    SELECT tenure_months AS t, COUNT(*) AS n, SUM(churned) AS events FROM stg_customers GROUP BY 1
),
risk AS (
    SELECT t, n, events,
           SUM(n) OVER (ORDER BY t DESC ROWS UNBOUNDED PRECEDING) AS at_risk
    FROM by_t
)
SELECT t, n, events, at_risk, events / at_risk AS hazard,
       exp(SUM(ln(1 - events / at_risk)) OVER (ORDER BY t ROWS UNBOUNDED PRECEDING)) AS survival
FROM risk
ORDER BY t;

-- Q4: charge deciles (NTILE) and churn, used to show the price-sensitivity gradient.
CREATE OR REPLACE VIEW v_charge_deciles AS
WITH d AS (
    SELECT *, NTILE(10) OVER (ORDER BY monthly_charges, customer_id) AS charge_decile FROM stg_customers
)
SELECT charge_decile, COUNT(*) AS customers, MIN(monthly_charges) AS min_charge, MAX(monthly_charges) AS max_charge,
       AVG(churned) AS churn_rate, SUM(monthly_charges * churned) AS mrr_lost
FROM d GROUP BY 1;
