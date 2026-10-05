"""Descriptive and statistical churn analysis: segments with confidence intervals, revenue at risk,
chi-square / Cramer's V driver ranking, and Kaplan-Meier retention by contract.

Writes facts.json section "analysis" plus reports/segment_churn.csv and reports/drivers.csv.
"""
from __future__ import annotations

import json

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from lifelines import KaplanMeierFitter
from lifelines.statistics import multivariate_logrank_test
from scipy import stats
from statsmodels.stats.proportion import proportion_confint

from src import facts
from src.clean import load
from src.config import REPORTS, SQL_OUT
from src.plotstyle import CRITICAL, INK_2, SERIES, save, usd

DIMENSIONS = ["contract", "tenure_band", "internet_service", "payment_method", "charges_band", "tech_support",
              "online_security", "online_backup", "device_protection", "streaming_tv", "streaming_movies",
              "paperless_billing", "is_senior", "has_partner", "has_dependents", "multiple_lines", "has_phone", "gender"]
LABELS = {"contract": "Contract", "tenure_band": "Tenure", "internet_service": "Internet service",
          "payment_method": "Payment method", "charges_band": "Monthly charges", "tech_support": "Tech support",
          "online_security": "Online security", "online_backup": "Online backup", "device_protection": "Device protection",
          "streaming_tv": "Streaming TV", "streaming_movies": "Streaming movies", "paperless_billing": "Paperless billing",
          "is_senior": "Senior citizen", "has_partner": "Has partner", "has_dependents": "Has dependents",
          "multiple_lines": "Multiple lines", "has_phone": "Phone service", "gender": "Gender"}
CONSTANTS = {"ci_level_pct": 95, "alpha": 0.05, "p_floor": 0.001, "months_per_year": 12,
             "charge_band_edges": [35, 70, 90], "tenure_band_edges": [12, 24, 48, 72], "tenure_band_starts": [0, 13, 25, 49], "survival_checkpoints": [12, 24, 72],
             "total_charges_gap_pct": 20, "min_segment_size": 100}


def cramers_v(table: pd.DataFrame) -> tuple[float, float, float]:
    chi2, p, dof, _ = stats.chi2_contingency(table, correction=False)
    n = table.values.sum()
    k = min(table.shape) - 1
    return chi2, p, float(np.sqrt(chi2 / (n * k))) if k > 0 else 0.0


def segment_table(df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for dim in DIMENSIONS:
        g = df.groupby(df[dim].astype(str)).agg(customers=("churned", "size"), churned=("churned", "sum"),
                                                mrr=("monthly_charges", "sum"))
        g["mrr_lost"] = df.assign(l=df.monthly_charges * df.churned).groupby(df[dim].astype(str)).l.sum()
        lo, hi = proportion_confint(g.churned, g.customers, alpha=0.05, method="wilson")
        g["churn_rate"], g["ci_low"], g["ci_high"] = g.churned / g.customers, lo, hi
        g["dimension"] = dim
        rows.append(g.reset_index().rename(columns={dim: "segment"}))
    return pd.concat(rows, ignore_index=True)


def run() -> dict:
    df = load()
    f: dict = {"constants": CONSTANTS}
    churned = df[df.churned == 1]
    kpi = {
        "customers": len(df), "churned": int(df.churned.sum()), "retained": int((df.churned == 0).sum()),
        "churn_rate": df.churned.mean(), "mrr_total": df.monthly_charges.sum(), "mrr_lost": churned.monthly_charges.sum(),
        "annual_revenue_lost": churned.monthly_charges.sum() * 12,
        "mrr_lost_share": churned.monthly_charges.sum() / df.monthly_charges.sum(),
        "avg_charges_churned": churned.monthly_charges.mean(), "avg_charges_retained": df[df.churned == 0].monthly_charges.mean(),
        "avg_tenure_churned": churned.tenure_months.mean(), "avg_tenure_retained": df[df.churned == 0].tenure_months.mean(),
        "median_tenure_churned": churned.tenure_months.median(),
        "churned_in_first_year_share": (churned.tenure_months <= 12).mean(),
        "lifetime_revenue_lost": churned.total_charges.sum(),
    }
    f["kpi"] = kpi
    sql = pd.read_csv(SQL_OUT / "headline_kpis.csv").iloc[0]
    f["crosscheck"] = {"sql_churn_rate": sql.churn_rate, "python_churn_rate": kpi["churn_rate"],
                       "sql_mrr_lost": sql.mrr_lost, "python_mrr_lost": kpi["mrr_lost"]}

    # ---------------------------------------------------------------- Q1 segments with Wilson CIs
    seg = segment_table(df)
    seg.to_csv(REPORTS / "segment_churn.csv", index=False)
    s = seg.set_index(["dimension", "segment"])
    pick = lambda d, v: {c: s.loc[(d, v), c] for c in ["customers", "churned", "churn_rate", "ci_low", "ci_high", "mrr_lost"]}
    f["segments"] = {
        "m2m": pick("contract", "Month-to-month"), "one_year": pick("contract", "One year"), "two_year": pick("contract", "Two year"),
        "tenure_0_12": pick("tenure_band", "00-12 months"), "tenure_49_72": pick("tenure_band", "49-72 months"),
        "fiber": pick("internet_service", "Fiber optic"), "dsl": pick("internet_service", "DSL"),
        "no_internet": pick("internet_service", "No"), "echeck": pick("payment_method", "Electronic check"),
        "auto_card": pick("payment_method", "Credit card (automatic)"), "no_tech_support": pick("tech_support", "No"),
        "tech_support": pick("tech_support", "Yes"), "senior": pick("is_senior", "True"), "non_senior": pick("is_senior", "False"),
        "paperless": pick("paperless_billing", "True"), "charges_90_plus": pick("charges_band", "4. $90+"),
        "charges_under_35": pick("charges_band", "1. under $35"),
    }
    f["segments"]["echeck_vs_auto_card_ratio"] = f["segments"]["echeck"]["churn_rate"] / f["segments"]["auto_card"]["churn_rate"]
    f["segments"]["m2m_vs_two_year_ratio"] = f["segments"]["m2m"]["churn_rate"] / f["segments"]["two_year"]["churn_rate"]
    f["segments"]["m2m_share_of_mrr_lost"] = f["segments"]["m2m"]["mrr_lost"] / kpi["mrr_lost"]
    f["segments"]["m2m_share_of_customers"] = f["segments"]["m2m"]["customers"] / kpi["customers"]

    fig, axes = plt.subplots(1, 3, figsize=(12, 3.8), sharey=True)
    for ax, dim in zip(axes, ["contract", "tenure_band", "payment_method"]):
        d = seg[seg.dimension == dim].sort_values("churn_rate", ascending=False)
        lab = d.segment.str.replace(" (automatic)", " (auto)", regex=False)
        ax.bar(lab, d.churn_rate * 100, color=SERIES[0], width=0.6,
               yerr=[(d.churn_rate - d.ci_low) * 100, (d.ci_high - d.churn_rate) * 100], error_kw={"elinewidth": 1, "ecolor": INK_2})
        ax.set_title(LABELS[dim], fontsize=10)
        ax.tick_params(axis="x", labelsize=8, rotation=20)
    axes[0].set_ylabel("Churn rate (%) with 95% CI")
    fig.suptitle(f"Month-to-month contracts churn {f['segments']['m2m']['churn_rate']:.0%} vs "
                 f"{f['segments']['two_year']['churn_rate']:.0%} on two-year; first-year customers churn "
                 f"{f['segments']['tenure_0_12']['churn_rate']:.0%}", x=0.01, ha="left", fontsize=11, fontweight="bold")
    save(fig, "01_churn_by_segment", "Takeaway: contract length, tenure and payment method separate high and low churn cleanly; intervals do not overlap.")

    # ---------------------------------------------------------------- Q2 revenue at risk
    rar = pd.read_csv(SQL_OUT / "revenue_at_risk_top10.csv")
    top = rar.iloc[0]
    hot = df[(df.contract == "Month-to-month") & (df.internet_service == "Fiber optic") & (df.tenure_months <= 12)]
    f["revenue_at_risk"] = {
        "top_segment": f"{top.contract} / {top.internet_service} / {top.tenure_band}",
        "hot_customers": len(hot), "hot_churn_rate": hot.churned.mean(), "hot_mrr_lost": (hot.monthly_charges * hot.churned).sum(),
        "hot_share_of_customers": len(hot) / len(df), "hot_share_of_mrr_lost": (hot.monthly_charges * hot.churned).sum() / kpi["mrr_lost"],
        "top3_share_of_loss": float(rar.cumulative_share_of_loss.iloc[2]),
        "mrr_lost_by_contract": {k: v for k, v in seg[seg.dimension == "contract"].set_index("segment").mrr_lost.items()},
    }
    by = seg[seg.dimension == "internet_service"].set_index("segment")
    fig, ax = plt.subplots(figsize=(8, 3.8))
    r10 = rar.head(8).iloc[::-1]
    lab = (r10.contract.str.replace("Month-to-month", "M2M") + " / " + r10.internet_service + " / " + r10.tenure_band.str.replace(" months", "m"))
    ax.barh(lab, r10.mrr_lost / 1e3, color=[CRITICAL if i == 0 else SERIES[0] for i in range(len(r10))][::-1], height=0.6)
    ax.set_xlabel("Monthly revenue lost to churn ($ thousands)")
    ax.grid(axis="y", visible=False)
    ax.set_title(f"One segment, {f['revenue_at_risk']['hot_share_of_customers']:.0%} of customers, carries "
                 f"{f['revenue_at_risk']['hot_share_of_mrr_lost']:.0%} of lost revenue", fontsize=11)
    save(fig, "02_revenue_at_risk", "Takeaway: new month-to-month fiber customers are where the money leaks.")

    # ---------------------------------------------------------------- Q3 drivers: chi-square + Cramer's V
    drv = []
    for dim in [d for d in DIMENSIONS if not d.endswith("_band")]:   # bands duplicate the numeric tests below
        tab = pd.crosstab(df[dim].astype(str), df.churned)
        chi2, p, v = cramers_v(tab)
        drv.append({"feature": dim, "label": LABELS[dim], "type": "categorical", "chi2": chi2, "p_value": p, "effect": v,
                    "effect_measure": "Cramer's V"})
    for col, lab in [("tenure_months", "Tenure (months)"), ("monthly_charges", "Monthly charges"), ("total_charges", "Total charges")]:
        u, p = stats.mannwhitneyu(churned[col], df[df.churned == 0][col])
        rbc = 2 * u / (len(churned) * (len(df) - len(churned))) - 1
        drv.append({"feature": col, "label": lab, "type": "numeric", "chi2": None, "p_value": p, "effect": abs(rbc),
                    "effect_measure": "rank-biserial |r|", "direction": "higher for churners" if rbc > 0 else "lower for churners"})
    drivers = pd.DataFrame(drv).sort_values("effect", ascending=False).reset_index(drop=True)
    drivers["significant_bonferroni"] = drivers.p_value < 0.05 / len(drivers)
    drivers.to_csv(REPORTS / "drivers.csv", index=False)
    f["drivers"] = {
        "top": drivers.head(6)[["feature", "label", "effect", "effect_measure", "p_value"]].to_dict("records"),
        "n_tested": len(drivers), "n_significant": int(drivers.significant_bonferroni.sum()),
        "not_significant": drivers[~drivers.significant_bonferroni].label.tolist(),
        "gender_v": float(drivers.set_index("feature").loc["gender", "effect"]),
        "gender_p": float(drivers.set_index("feature").loc["gender", "p_value"]),
        "contract_v": float(drivers.set_index("feature").loc["contract", "effect"]),
        "tenure_rbc": float(drivers.set_index("feature").loc["tenure_months", "effect"]),
    }
    d8 = drivers.head(10).iloc[::-1]
    fig, ax = plt.subplots(figsize=(8, 4.2))
    ax.barh(d8.label, d8.effect, color=SERIES[0], height=0.6)
    ax.set_xlabel("Effect size (Cramer's V for categories, |rank-biserial| for numbers)")
    ax.grid(axis="y", visible=False)
    ax.set_title(f"Strongest churn drivers: {drivers.label[0].lower()}, {drivers.label[1].lower()} and {drivers.label[2].lower()}", fontsize=11)
    save(fig, "03_churn_drivers", f"Takeaway: {f['drivers']['n_significant']} of {len(drivers)} features are significant after Bonferroni; gender is not.")

    # ---------------------------------------------------------------- Kaplan-Meier by contract
    fig, ax = plt.subplots(figsize=(8, 4.2))
    km_out = {}
    for i, c in enumerate(["Month-to-month", "One year", "Two year"]):
        d = df[df.contract == c]
        km = KaplanMeierFitter().fit(d.tenure_months, d.churned, label=c)
        km.plot_survival_function(ax=ax, ci_show=True, color=SERIES[i], linewidth=2)
        km_out[c] = {f"s{t}": float(km.survival_function_at_times(t).iloc[0]) for t in CONSTANTS["survival_checkpoints"]}
        km_out[c]["timeline"] = km.timeline.tolist()
        km_out[c]["survival"] = km.survival_function_.iloc[:, 0].round(5).tolist()
    lr = multivariate_logrank_test(df.tenure_months, df.contract, df.churned)
    kall = KaplanMeierFitter().fit(df.tenure_months, df.churned)
    f["survival"] = {
        "m2m_s12": km_out["Month-to-month"]["s12"], "m2m_s24": km_out["Month-to-month"]["s24"], "m2m_s72": km_out["Month-to-month"]["s72"],
        "one_year_s72": km_out["One year"]["s72"], "two_year_s72": km_out["Two year"]["s72"],
        "all_s12": float(kall.survival_function_at_times(12).iloc[0]), "all_s72": float(kall.survival_function_at_times(72).iloc[0]),
        "logrank_stat": lr.test_statistic, "logrank_p": lr.p_value,
    }
    ax.set_xlabel("Tenure (months)")
    ax.set_ylabel("Share of customers still active")
    ax.set_ylim(0, 1.02)
    ax.legend(loc="lower left")
    ax.set_title(f"Kaplan-Meier: only {f['survival']['m2m_s72']:.0%} of month-to-month customers survive 72 months vs "
                 f"{f['survival']['two_year_s72']:.0%} on two-year contracts", fontsize=11)
    save(fig, "04_kaplan_meier_contract", "Takeaway: the first year decides most month-to-month churn (log-rank p < 0.001).")
    facts_km = {c: {"timeline": v["timeline"], "survival": v["survival"]} for c, v in km_out.items()}
    (REPORTS / "km_curves.json").write_text(json.dumps(facts_km), encoding="utf-8")

    facts.update("analysis", f)
    print(f"analysis: churn {kpi['churn_rate']:.2%}, MRR lost {usd(kpi['mrr_lost'])}, top driver {drivers.label[0]}")
    return f


if __name__ == "__main__":
    run()
