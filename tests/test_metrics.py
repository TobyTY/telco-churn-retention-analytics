"""SQL and Python agree; statistics and model protocol behave as documented."""
import numpy as np
import pandas as pd
import pytest

from src.model import EXCLUDED, NUM, BOOL, CAT, campaign
from src.warehouse import named_queries


def test_headline_sql_equals_python(con, customers):
    sql = con.execute(named_queries()["headline_kpis"]).df().iloc[0]
    assert int(sql.customers) == len(customers)
    assert int(sql.churned) == customers.churned.sum()
    assert sql.mrr_lost == pytest.approx((customers.monthly_charges * customers.churned).sum(), abs=0.01)
    assert sql.mrr_total == pytest.approx(customers.monthly_charges.sum(), abs=0.01)


def test_staging_columns_match_python(con, customers):
    stg = con.execute("SELECT customer_id, total_charges, n_addons, tenure_band, charges_band, churned FROM stg_customers").df()
    merged = stg.merge(customers, on="customer_id", suffixes=("_sql", "_py"))
    assert len(merged) == len(customers)
    assert np.allclose(merged.total_charges_sql, merged.total_charges_py)
    assert (merged.n_addons_sql == merged.n_addons_py).all()
    assert (merged.tenure_band_sql == merged.tenure_band_py).all()
    assert (merged.charges_band_sql == merged.charges_band_py).all()
    assert (merged.churned_sql == merged.churned_py).all()


def test_segment_rates_match_sql_view(con, facts):
    sql = con.execute("SELECT churn_rate FROM v_churn_by_segment WHERE dimension='contract' AND segment='Month-to-month'").fetchone()[0]
    assert sql == pytest.approx(facts["analysis"]["segments"]["m2m"]["churn_rate"], abs=1e-6)


def test_wilson_interval_contains_rate(facts):
    for s in facts["analysis"]["segments"].values():
        if isinstance(s, dict):
            assert s["ci_low"] <= s["churn_rate"] <= s["ci_high"]


def test_sql_km_curve_matches_lifelines(con, customers):
    from lifelines import KaplanMeierFitter
    sql = con.execute("SELECT t, survival FROM v_tenure_curve").df().set_index("t").survival
    km = KaplanMeierFitter().fit(customers.tenure_months, customers.churned)
    for t in [1, 12, 24, 48, 72]:
        assert sql.loc[t] == pytest.approx(float(km.survival_function_at_times(t).iloc[0]), abs=1e-9)


def test_no_excluded_feature_used():
    assert not set(EXCLUDED) & set(NUM + BOOL + CAT)


def test_leakage_controls(facts):
    lk = facts["model"]["leakage"]
    assert lk["id_overlap_train_test"] == 0
    assert abs(lk["shuffled_label_test_auc"] - 0.5) < 0.06
    assert lk["max_single_feature_auc"] < 0.95


def test_model_selection_used_cv_not_test(facts):
    t = pd.DataFrame(facts["model"]["models"]["table"])
    cand = t[t.model != "Logistic regression (class-weighted)"]
    assert facts["model"]["models"]["best"] == cand.sort_values("cv_roc_auc", ascending=False).iloc[0].model


def test_campaign_formula():
    y = np.array([1, 0, 1, 0])
    mc = np.array([100.0, 50.0, 80.0, 20.0])
    r = campaign(np.array([True, True, False, False]), y, mc, save_rate=0.5)
    # saved = 0.5 * 100 * 12 = 600; cost = 2 * 5 + 0.2 * 6 * (100 + 50) = 190
    assert r["saved_revenue"] == pytest.approx(600)
    assert r["cost"] == pytest.approx(190)
    assert r["net_value"] == pytest.approx(410)
    assert r["breakeven_save_rate"] == pytest.approx(190 / 1200)


def test_targeting_beats_blanket_offer(facts):
    g = facts["model"]["campaign"]["groups"]
    assert g["model"]["net_value"] > g["everyone"]["net_value"]
