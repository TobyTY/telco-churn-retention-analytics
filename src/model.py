"""Churn risk models, leakage checks, lift, and a campaign-economics threshold.

Protocol
- Stratified 75/25 train/test split (seed 42). The test set is touched once, at the end.
- Preprocessing lives inside each sklearn Pipeline, so CV folds never see each other's scaling.
- Model choice by 5-fold stratified CV ROC-AUC on the training set.
- Class imbalance (about one churner in four) is handled by stratification, PR-AUC reporting and a
  cost-based decision threshold, not by re-weighting: re-weighting inflates the probabilities that the
  revenue-at-risk numbers need. A class-weighted logistic regression is reported for comparison.
- The decision threshold maximises campaign net value on out-of-fold training predictions, then is
  applied unchanged to the test set.
"""
from __future__ import annotations

import warnings

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.base import clone
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import HistGradientBoostingClassifier, RandomForestClassifier
from sklearn.inspection import permutation_importance
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (average_precision_score, brier_score_loss, f1_score, precision_recall_curve, precision_score,
                             recall_score, roc_auc_score, roc_curve)
from sklearn.model_selection import StratifiedKFold, cross_val_predict, cross_validate, train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

from src import facts
from src.clean import load
from src.config import REPORTS, SEED, TEST_SIZE
from src.plotstyle import CRITICAL, INK_2, SERIES, save
from src.warehouse import connect, run_query

NUM = ["tenure_months", "monthly_charges", "total_charges", "n_addons"]
BOOL = ["is_senior", "has_partner", "has_dependents", "has_phone", "paperless_billing"]
CAT = ["gender", "multiple_lines", "internet_service", "online_security", "online_backup", "device_protection",
       "tech_support", "streaming_tv", "streaming_movies", "contract", "payment_method"]
EXCLUDED = {"customer_id": "identifier", "churned": "target", "tenure_band": "derived from tenure_months",
            "charges_band": "derived from monthly_charges"}

# Campaign assumptions (planning inputs, stored in facts.json; change them in the Excel calculator too).
CAMPAIGN = {
    "offer_discount_pct": 20,      # discount on the monthly bill
    "offer_months": 6,             # for this many months; every targeted customer is assumed to take it
    "contact_cost": 5.0,           # $ per targeted customer (outreach, agent time)
    "save_rate": 0.30,             # share of would-be churners the offer retains
    "value_horizon_months": 12,    # months of revenue kept from a saved customer
    "save_rate_grid": [0.1, 0.2, 0.3, 0.4, 0.5],
}
RISK_BANDS = {"high": 0.5, "medium": 0.25}   # probability cut-offs for the at-risk list
# scikit-learn 1.6 passes an option SciPy 1.18 no longer knows; harmless
warnings.filterwarnings("ignore", message="Unknown solver options: iprint")
CV_FOLDS = 5


def preprocessor() -> ColumnTransformer:
    return ColumnTransformer([("num", StandardScaler(), NUM), ("bool", "passthrough", BOOL),
                              ("cat", OneHotEncoder(handle_unknown="ignore"), CAT)])


def models() -> dict[str, Pipeline]:
    return {
        "Logistic regression": Pipeline([("prep", preprocessor()), ("clf", LogisticRegression(max_iter=5000, C=1.0))]),
        "Logistic regression (class-weighted)": Pipeline([("prep", preprocessor()),
                                                           ("clf", LogisticRegression(max_iter=5000, C=1.0, class_weight="balanced"))]),
        "Random forest": Pipeline([("prep", preprocessor()), ("clf", RandomForestClassifier(
            n_estimators=500, min_samples_leaf=5, max_features="sqrt", n_jobs=-1, random_state=SEED))]),
        "Gradient boosting": Pipeline([("prep", preprocessor()), ("clf", HistGradientBoostingClassifier(
            learning_rate=0.05, max_iter=300, max_leaf_nodes=15, l2_regularization=1.0, random_state=SEED))]),
    }


def features(df: pd.DataFrame) -> pd.DataFrame:
    X = df[NUM + BOOL + CAT].copy()
    X[BOOL] = X[BOOL].astype(int)
    return X


def offer_cost(mc: np.ndarray) -> np.ndarray:
    c = CAMPAIGN
    return c["contact_cost"] + c["offer_discount_pct"] / 100 * c["offer_months"] * mc


def campaign(mask: np.ndarray, y: np.ndarray, mc: np.ndarray, save_rate: float | None = None) -> dict:
    """Net value of offering the retention deal to the customers in `mask`."""
    s = CAMPAIGN["save_rate"] if save_rate is None else save_rate
    h = CAMPAIGN["value_horizon_months"]
    n = int(mask.sum())
    churner_mrr = float((mc * y)[mask].sum())
    group_mrr = float(mc[mask].sum())
    cost = float(offer_cost(mc[mask]).sum())
    saved = s * churner_mrr * h
    return {"customers": n, "churners": int(y[mask].sum()), "churn_rate": float(y[mask].mean()) if n else 0.0,
            "churner_mrr": churner_mrr, "group_mrr": group_mrr, "saved_revenue": saved, "cost": cost,
            "net_value": saved - cost, "roi": (saved - cost) / cost if cost else 0.0,
            "breakeven_save_rate": cost / (churner_mrr * h) if churner_mrr else None,
            "customers_saved": s * float(y[mask].sum())}


def best_threshold(p: np.ndarray, y: np.ndarray, mc: np.ndarray) -> tuple[float, pd.DataFrame]:
    grid = np.round(np.arange(0.05, 0.951, 0.01), 2)
    rows = [{"threshold": t, **campaign(p >= t, y, mc)} for t in grid]
    curve = pd.DataFrame(rows)
    return float(curve.loc[curve.net_value.idxmax(), "threshold"]), curve


def run() -> dict:
    df = load()
    X, y, mc = features(df), df.churned.values, df.monthly_charges.values
    assert not set(EXCLUDED) & set(X.columns), "excluded column leaked into features"
    idx_tr, idx_te = train_test_split(np.arange(len(df)), test_size=TEST_SIZE, stratify=y, random_state=SEED)
    Xtr, Xte, ytr, yte = X.iloc[idx_tr], X.iloc[idx_te], y[idx_tr], y[idx_te]
    cv = StratifiedKFold(CV_FOLDS, shuffle=True, random_state=SEED)
    f: dict = {"protocol": {"seed": SEED, "test_size": TEST_SIZE, "cv_folds": CV_FOLDS, "n_train": len(idx_tr), "n_test": len(idx_te),
                            "train_churn_rate": ytr.mean(), "test_churn_rate": yte.mean(), "n_features_raw": X.shape[1]},
               "campaign_assumptions": CAMPAIGN, "risk_bands": RISK_BANDS}

    # ---------------------------------------------------------------- model comparison
    rows, fitted, test_p = [], {}, {}
    for name, pipe in models().items():
        cvr = cross_validate(pipe, Xtr, ytr, cv=cv, scoring=["roc_auc", "average_precision"])
        m = clone(pipe).fit(Xtr, ytr)
        p = m.predict_proba(Xte)[:, 1]
        fitted[name], test_p[name] = m, p
        pred = p >= 0.5
        rows.append({"model": name, "cv_roc_auc": cvr["test_roc_auc"].mean(), "cv_roc_auc_sd": cvr["test_roc_auc"].std(),
                     "cv_pr_auc": cvr["test_average_precision"].mean(), "test_roc_auc": roc_auc_score(yte, p),
                     "test_pr_auc": average_precision_score(yte, p), "precision_at_0.5": precision_score(yte, pred),
                     "recall_at_0.5": recall_score(yte, pred), "f1_at_0.5": f1_score(yte, pred), "brier": brier_score_loss(yte, p)})
    table = pd.DataFrame(rows)
    table.to_csv(REPORTS / "model_comparison.csv", index=False)
    candidates = table[table.model != "Logistic regression (class-weighted)"]
    best_name = candidates.sort_values("cv_roc_auc", ascending=False).iloc[0].model
    best, p_te = fitted[best_name], test_p[best_name]
    lr = table.set_index("model").loc["Logistic regression"]
    f["models"] = {"table": table.to_dict("records"), "best": best_name,
                   "best_beats_baseline": best_name != "Logistic regression",
                   "baseline_cv_roc_auc": lr.cv_roc_auc, "best_cv_roc_auc": table.set_index("model").loc[best_name, "cv_roc_auc"],
                   "best_test_roc_auc": roc_auc_score(yte, p_te), "best_test_pr_auc": average_precision_score(yte, p_te),
                   "test_base_rate": yte.mean(), "cv_gap": candidates.cv_roc_auc.max() - candidates.cv_roc_auc.min(),
                   "baseline_cv_sd": lr.cv_roc_auc_sd}

    fig, axes = plt.subplots(1, 2, figsize=(11, 4.2))
    for i, name in enumerate(["Logistic regression", "Random forest", "Gradient boosting"]):
        fpr, tpr, _ = roc_curve(yte, test_p[name])
        pr, rc, _ = precision_recall_curve(yte, test_p[name])
        axes[0].plot(fpr, tpr, color=SERIES[i], label=f"{name} (AUC {roc_auc_score(yte, test_p[name]):.3f})")
        axes[1].plot(rc, pr, color=SERIES[i], label=f"{name} (AP {average_precision_score(yte, test_p[name]):.3f})")
    axes[0].plot([0, 1], [0, 1], color=INK_2, linewidth=0.8)
    axes[1].axhline(yte.mean(), color=INK_2, linewidth=0.8)
    axes[0].set(xlabel="False positive rate", ylabel="True positive rate", title="ROC curve (test set)")
    axes[1].set(xlabel="Recall", ylabel="Precision", title="Precision-recall curve (test set)")
    for ax in axes:
        ax.legend(fontsize=8, loc="lower right" if ax is axes[0] else "upper right")
    fig.suptitle(f"{best_name} wins on cross-validation; the three models are within "
                 f"{(candidates.cv_roc_auc.max() - candidates.cv_roc_auc.min()):.3f} ROC-AUC", x=0.01, ha="left", fontsize=11, fontweight="bold")
    save(fig, "09_model_curves", "Takeaway: a simple, explainable logistic regression is as good as the tree ensembles on this data.")

    # ---------------------------------------------------------------- leakage checks
    rng = np.random.default_rng(SEED)
    shuffled = clone(models()["Logistic regression"]).fit(Xtr, rng.permutation(ytr))
    no_total = Pipeline([("prep", ColumnTransformer([("num", StandardScaler(), [c for c in NUM if c != "total_charges"]),
                                                     ("bool", "passthrough", BOOL), ("cat", OneHotEncoder(handle_unknown="ignore"), CAT)])),
                         ("clf", LogisticRegression(max_iter=5000))]).fit(Xtr, ytr)
    single = {}
    for c in NUM:
        a = roc_auc_score(y, X[c])
        single[c] = max(a, 1 - a)
    dup = pd.merge(Xte.reset_index(drop=True).assign(_t=1), Xtr.drop_duplicates().assign(_r=1), on=list(X.columns), how="inner")
    f["leakage"] = {
        "excluded_columns": EXCLUDED,
        "id_overlap_train_test": int(len(set(df.customer_id.iloc[idx_tr]) & set(df.customer_id.iloc[idx_te]))),
        "test_rows_with_identical_train_features": int(len(dup)),
        "shuffled_label_test_auc": roc_auc_score(yte, shuffled.predict_proba(Xte)[:, 1]),
        "auc_without_total_charges": roc_auc_score(yte, no_total.predict_proba(Xte)[:, 1]),
        "auc_with_total_charges": lr.test_roc_auc,
        "max_single_feature_auc": max(single.values()), "max_single_feature": max(single, key=single.get),
        "preprocessing_inside_pipeline": True,
        "verdict": "no leakage found",
    }
    assert f["leakage"]["id_overlap_train_test"] == 0
    assert abs(f["leakage"]["shuffled_label_test_auc"] - 0.5) < 0.06, "model learns from shuffled labels: leakage"
    assert f["leakage"]["max_single_feature_auc"] < 0.95, "a single feature nearly separates the classes: check for leakage"

    # ---------------------------------------------------------------- drivers in plain language
    lr_fit = fitted["Logistic regression"]
    names = lr_fit.named_steps["prep"].get_feature_names_out()
    coef = pd.Series(lr_fit.named_steps["clf"].coef_[0], index=names)
    odds = np.exp(coef).sort_values()
    f["drivers_model"] = {"odds_ratios_top_up": odds.tail(5).iloc[::-1].to_dict(), "odds_ratios_top_down": odds.head(5).to_dict()}
    pi = permutation_importance(best, Xte, yte, scoring="roc_auc", n_repeats=10, random_state=SEED, n_jobs=1)
    imp = pd.Series(pi.importances_mean, index=X.columns).sort_values(ascending=False)
    f["drivers_model"]["permutation_top5"] = imp.head(5).to_dict()
    fig, ax = plt.subplots(figsize=(8, 4.2))
    top = imp.head(10)[::-1]
    ax.barh([c.replace("_", " ") for c in top.index], top.values, color=SERIES[0], height=0.6)
    ax.set_xlabel("Drop in test ROC-AUC when the feature is shuffled")
    ax.grid(axis="y", visible=False)
    ax.set_title(f"What the model relies on: {imp.index[0].replace('_', ' ')}, {imp.index[1].replace('_', ' ')}, "
                 f"{imp.index[2].replace('_', ' ')}", fontsize=11)
    save(fig, "10_permutation_importance", "Takeaway: the model agrees with the statistics: commitment and tenure dominate.")

    # ---------------------------------------------------------------- threshold from campaign economics (train OOF)
    oof_tr = cross_val_predict(clone(models()[best_name]), Xtr, ytr, cv=cv, method="predict_proba")[:, 1]
    t_star, curve_tr = best_threshold(oof_tr, ytr, mc[idx_tr])
    pred_te = p_te >= t_star
    f["threshold"] = {"chosen": t_star, "method": "max campaign net value on out-of-fold training predictions",
                      "test_precision": precision_score(yte, pred_te), "test_recall": recall_score(yte, pred_te),
                      "test_f1": f1_score(yte, pred_te), "test_targeted_share": pred_te.mean(),
                      "test_campaign": campaign(pred_te, yte, mc[idx_te])}
    _, curve_te = best_threshold(p_te, yte, mc[idx_te])
    curve_te.to_csv(REPORTS / "threshold_curve_test.csv", index=False)
    fig, ax = plt.subplots(figsize=(8, 4))
    ax.plot(curve_te.threshold, curve_te.net_value / 1e3, color=SERIES[0])
    ax.axvline(t_star, color=CRITICAL, linewidth=1)
    ax.axhline(0, color=INK_2, linewidth=0.8)
    ax.text(t_star + 0.01, curve_te.net_value.max() / 1e3 * 0.9, f"chosen threshold {t_star:.2f}", fontsize=9, color=INK_2)
    ax.set_xlabel("Target customers with predicted churn probability at or above")
    ax.set_ylabel("Campaign net value, test set ($ thousands)")
    ax.set_title(f"Net value peaks around a {t_star:.2f} threshold (chosen on training folds, shown on test)", fontsize=11)
    save(fig, "11_threshold_net_value", "Takeaway: targeting everyone loses money; targeting only the top few leaves value on the table.")

    # ---------------------------------------------------------------- lift / gains (test)
    dec = pd.DataFrame({"p": p_te, "y": yte}).sort_values("p", ascending=False).reset_index(drop=True)
    dec["decile"] = np.repeat(np.arange(1, 11), np.ceil(len(dec) / 10))[:len(dec)]
    g = dec.groupby("decile").agg(n=("y", "size"), churners=("y", "sum"), rate=("y", "mean"), p=("p", "mean"))
    g["cum_capture"] = g.churners.cumsum() / g.churners.sum()
    g["lift"] = g.rate / yte.mean()
    g.to_csv(REPORTS / "lift_table.csv")
    f["lift"] = {"top_decile_lift": g.lift.iloc[0], "top_decile_churn_rate": g.rate.iloc[0],
                 "top2_capture": g.cum_capture.iloc[1], "top3_capture": g.cum_capture.iloc[2],
                 "deciles": g.reset_index().to_dict("records")}
    fig, axes = plt.subplots(1, 2, figsize=(11, 4))
    axes[0].bar(g.index.astype(str), g.lift, color=SERIES[0], width=0.6)
    axes[0].axhline(1, color=INK_2, linewidth=0.8)
    axes[0].set(xlabel="Risk decile (1 = highest predicted risk)", ylabel="Lift vs average churn", title="Lift by decile")
    axes[1].plot(np.r_[0, g.index / 10], np.r_[0, g.cum_capture], color=SERIES[0], marker="o", markersize=4, label=best_name)
    axes[1].plot([0, 1], [0, 1], color=INK_2, linewidth=0.8, label="Random targeting")
    axes[1].set(xlabel="Share of customers contacted", ylabel="Share of churners reached", title="Cumulative gains")
    axes[1].legend(fontsize=8)
    fig.suptitle(f"The top 10% riskiest customers churn at {g.lift.iloc[0]:.1f}x the average; the top 30% contain "
                 f"{g.cum_capture.iloc[2]:.0%} of churners", x=0.01, ha="left", fontsize=11, fontweight="bold")
    save(fig, "12_lift_gains", "Takeaway: a ranked list makes a retention budget several times more efficient than random outreach.")

    # calibration
    cal = pd.DataFrame({"p": p_te, "y": yte})
    cal["bin"] = pd.qcut(cal.p, 10, labels=False, duplicates="drop")
    cb = cal.groupby("bin").agg(pred=("p", "mean"), actual=("y", "mean"))
    f["calibration"] = {"brier": brier_score_loss(yte, p_te), "max_bin_gap": float((cb.pred - cb.actual).abs().max()),
                        "mean_pred": float(p_te.mean()), "mean_actual": float(yte.mean())}

    # ---------------------------------------------------------------- full-base scoring (out of fold) and target groups
    oof_all = cross_val_predict(clone(models()[best_name]), X, y, cv=cv, method="predict_proba")[:, 1]
    band = np.where(oof_all >= RISK_BANDS["high"], "1. High", np.where(oof_all >= RISK_BANDS["medium"], "2. Medium", "3. Low"))
    scores = df[["customer_id", "churned", "monthly_charges", "contract", "internet_service", "tenure_months", "payment_method",
                 "tech_support", "n_addons"]].assign(churn_probability=oof_all.round(5), risk_band=band, targeted=oof_all >= t_star)
    scores.to_csv(REPORTS / "customer_scores.csv", index=False)
    with connect() as con:
        con.execute("CREATE OR REPLACE TABLE model_scores AS SELECT * FROM scores")
        rb = run_query(con, "risk_bands")
    groups = {
        "model": oof_all >= t_star,
        "rule_m2m_fiber_first_year": ((df.contract == "Month-to-month") & (df.internet_service == "Fiber optic") & (df.tenure_months <= 12)).values,
        "all_month_to_month": (df.contract == "Month-to-month").values,
        "everyone": np.ones(len(df), bool),
    }
    gres = {k: campaign(m, y, mc) for k, m in groups.items()}
    best_group = max(gres, key=lambda k: gres[k]["net_value"])
    sens = {f"{s:.1f}": campaign(groups["model"], y, mc, s)["net_value"] for s in CAMPAIGN["save_rate_grid"]}
    tgt = df[groups["model"]]
    f["campaign"] = {"groups": gres, "best_group": best_group, "net_by_save_rate": sens,
                     "target_m2m_share": (tgt.contract == "Month-to-month").mean(),
                     "target_fiber_share": (tgt.internet_service == "Fiber optic").mean(),
                     "target_echeck_share": (tgt.payment_method == "Electronic check").mean(),
                     "target_first_year_share": (tgt.tenure_months <= 12).mean(),
                     "target_avg_charges": tgt.monthly_charges.mean(),
                     "breakeven_probability_at_avg_charges": float(offer_cost(np.array([tgt.monthly_charges.mean()]))[0]
                                                                  / (CAMPAIGN["save_rate"] * tgt.monthly_charges.mean() * CAMPAIGN["value_horizon_months"])),
                     "oof_roc_auc_full_base": roc_auc_score(y, oof_all)}
    f["risk_bands_summary"] = rb.to_dict("records")

    facts.update("model", f)
    g_ = gres["model"]
    print(f"model: best={best_name} cv_auc={f['models']['best_cv_roc_auc']:.3f} test_auc={f['models']['best_test_roc_auc']:.3f}; "
          f"threshold {t_star:.2f}; target {g_['customers']} customers, net ${g_['net_value']:,.0f}, break-even save rate {g_['breakeven_save_rate']:.1%}")
    return f


if __name__ == "__main__":
    run()
