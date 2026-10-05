"""Data-quality checks on the staging table and the cleaned data."""


def scalar(con, sql):
    return con.execute(sql).fetchone()[0]


def test_one_row_per_customer(con, customers):
    assert scalar(con, "SELECT COUNT(*) - COUNT(DISTINCT customer_id) FROM stg_customers") == 0
    assert customers.customer_id.is_unique


def test_no_missing_total_charges(con, customers):
    assert scalar(con, "SELECT COUNT(*) FROM stg_customers WHERE total_charges IS NULL") == 0
    assert customers.total_charges.notna().all()


def test_blank_total_charges_only_for_new_customers(con):
    assert scalar(con, "SELECT COUNT(*) FROM stg_customers WHERE total_charges_was_blank AND tenure_months > 0") == 0


def test_value_domains(customers):
    assert set(customers.churned.unique()) <= {0, 1}
    assert customers.tenure_months.between(0, 72).all()
    assert (customers.monthly_charges > 0).all()
    assert set(customers.contract) == {"Month-to-month", "One year", "Two year"}


def test_bands_cover_everyone(customers):
    assert customers.tenure_band.notna().all() and (customers.tenure_band != "nan").all()
    assert customers.charges_band.notna().all() and (customers.charges_band != "nan").all()


def test_model_scores_are_probabilities(con):
    assert scalar(con, "SELECT COUNT(*) FROM model_scores WHERE churn_probability < 0 OR churn_probability > 1") == 0
    assert scalar(con, "SELECT COUNT(*) FROM model_scores") == scalar(con, "SELECT COUNT(*) FROM stg_customers")
