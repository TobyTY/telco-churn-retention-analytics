-- 00_schema.sql
-- Business question: none directly; lands the Telco CSV in a typed raw table.
-- Logic: explicit types; TotalCharges stays VARCHAR because the source holds blank strings for
--        brand-new customers (tenure 0), which are cleaned in staging. ${RAW} is replaced by src/warehouse.py.
-- Output: raw.customers, one row per customer, identical to the CSV.

CREATE SCHEMA IF NOT EXISTS raw;

CREATE OR REPLACE TABLE raw.customers (
    customerID       VARCHAR NOT NULL,
    gender           VARCHAR,
    SeniorCitizen    INTEGER,
    Partner          VARCHAR,
    Dependents       VARCHAR,
    tenure           INTEGER,
    PhoneService     VARCHAR,
    MultipleLines    VARCHAR,
    InternetService  VARCHAR,
    OnlineSecurity   VARCHAR,
    OnlineBackup     VARCHAR,
    DeviceProtection VARCHAR,
    TechSupport      VARCHAR,
    StreamingTV      VARCHAR,
    StreamingMovies  VARCHAR,
    Contract         VARCHAR,
    PaperlessBilling VARCHAR,
    PaymentMethod    VARCHAR,
    MonthlyCharges   DOUBLE,
    TotalCharges     VARCHAR,
    Churn            VARCHAR
);

INSERT INTO raw.customers
SELECT * FROM read_csv('${RAW}/Telco-Customer-Churn.csv', header = true, all_varchar = true);

CREATE INDEX IF NOT EXISTS ix_raw_customers_id ON raw.customers (customerID);
