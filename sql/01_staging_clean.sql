-- 01_staging_clean.sql
-- Business question: is the customer table clean enough to measure churn and revenue at risk?
-- Logic: de-duplicate on customerID, trim text, convert Yes/No to booleans, fix the blank TotalCharges
--        (tenure-0 customers have not been billed yet, so 0 is the correct value), add bands.
-- Output: stg_customers, one row per customer.

CREATE OR REPLACE TABLE stg_customers AS
WITH ranked AS (
    SELECT c.*, ROW_NUMBER() OVER (PARTITION BY customerID ORDER BY customerID) AS rn
    FROM raw.customers c
)
SELECT
    trim(customerID)                                             AS customer_id,
    trim(gender)                                                 AS gender,
    SeniorCitizen = 1                                            AS is_senior,
    trim(Partner) = 'Yes'                                        AS has_partner,
    trim(Dependents) = 'Yes'                                     AS has_dependents,
    tenure                                                       AS tenure_months,
    CASE WHEN tenure <= 12 THEN '00-12 months'
         WHEN tenure <= 24 THEN '13-24 months'
         WHEN tenure <= 48 THEN '25-48 months'
         ELSE '49-72 months' END                                 AS tenure_band,
    trim(PhoneService) = 'Yes'                                   AS has_phone,
    trim(MultipleLines)                                          AS multiple_lines,
    trim(InternetService)                                        AS internet_service,
    trim(OnlineSecurity)                                         AS online_security,
    trim(OnlineBackup)                                           AS online_backup,
    trim(DeviceProtection)                                       AS device_protection,
    trim(TechSupport)                                            AS tech_support,
    trim(StreamingTV)                                            AS streaming_tv,
    trim(StreamingMovies)                                        AS streaming_movies,
    trim(Contract)                                               AS contract,
    trim(PaperlessBilling) = 'Yes'                               AS paperless_billing,
    trim(PaymentMethod)                                          AS payment_method,
    MonthlyCharges                                               AS monthly_charges,
    CASE WHEN MonthlyCharges < 35 THEN '1. under $35'
         WHEN MonthlyCharges < 70 THEN '2. $35-70'
         WHEN MonthlyCharges < 90 THEN '3. $70-90'
         ELSE '4. $90+' END                                      AS charges_band,
    COALESCE(TRY_CAST(NULLIF(trim(TotalCharges), '') AS DOUBLE), 0) AS total_charges,
    NULLIF(trim(TotalCharges), '') IS NULL                       AS total_charges_was_blank,
    -- add-on services held (security, backup, protection, support, TV, movies)
    (CASE WHEN trim(OnlineSecurity) = 'Yes' THEN 1 ELSE 0 END + CASE WHEN trim(OnlineBackup) = 'Yes' THEN 1 ELSE 0 END
     + CASE WHEN trim(DeviceProtection) = 'Yes' THEN 1 ELSE 0 END + CASE WHEN trim(TechSupport) = 'Yes' THEN 1 ELSE 0 END
     + CASE WHEN trim(StreamingTV) = 'Yes' THEN 1 ELSE 0 END + CASE WHEN trim(StreamingMovies) = 'Yes' THEN 1 ELSE 0 END)
                                                                 AS n_addons,
    CASE WHEN trim(Churn) = 'Yes' THEN 1 ELSE 0 END              AS churned
FROM ranked
WHERE rn = 1;

CREATE INDEX IF NOT EXISTS ix_stg_customers_id ON stg_customers (customer_id);
