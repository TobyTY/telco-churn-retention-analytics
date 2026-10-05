"""Exploratory charts. Each title states the finding; each figure carries a one-line takeaway."""
from __future__ import annotations

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from src import facts
from src.clean import load
from src.plotstyle import INK_2, SERIES, save


def run() -> dict:
    df = load()
    out: dict = {"figures": []}
    ch, st = df[df.churned == 1], df[df.churned == 0]

    # tenure distribution by outcome
    fig, ax = plt.subplots(figsize=(9, 3.8))
    bins = np.arange(0, 74, 3)
    ax.hist(st.tenure_months, bins=bins, color=SERIES[0], alpha=0.85, label="Stayed", edgecolor="#fcfcfb", linewidth=0.5)
    ax.hist(ch.tenure_months, bins=bins, color=SERIES[1], alpha=0.85, label="Churned", edgecolor="#fcfcfb", linewidth=0.5)
    ax.set_xlabel("Tenure (months)")
    ax.set_ylabel("Customers")
    ax.legend()
    out["churned_first_year_share"] = (ch.tenure_months <= 12).mean()
    ax.set_title(f"{out['churned_first_year_share']:.0%} of churners leave within their first 12 months", fontsize=11)
    out["figures"].append(save(fig, "05_tenure_distribution", "Takeaway: churn is an onboarding problem more than a loyalty problem."))

    # monthly charges by outcome
    fig, ax = plt.subplots(figsize=(9, 3.8))
    bins = np.arange(15, 125, 5)
    ax.hist(st.monthly_charges, bins=bins, color=SERIES[0], alpha=0.85, label="Stayed", edgecolor="#fcfcfb", linewidth=0.5)
    ax.hist(ch.monthly_charges, bins=bins, color=SERIES[1], alpha=0.85, label="Churned", edgecolor="#fcfcfb", linewidth=0.5)
    ax.set_xlabel("Monthly charges ($)")
    ax.set_ylabel("Customers")
    ax.legend()
    out["median_charges_churned"], out["median_charges_retained"] = ch.monthly_charges.median(), st.monthly_charges.median()
    ax.set_title(f"Churners pay more: median ${out['median_charges_churned']:.2f} a month vs ${out['median_charges_retained']:.2f}", fontsize=11)
    out["figures"].append(save(fig, "06_charges_distribution", "Takeaway: churners cluster at the higher price points, which are mostly fiber-optic plans."))

    # add-on services
    g = df.groupby("n_addons").churned.agg(["mean", "size"])
    out["churn_0_addons_internet"] = df[(df.n_addons == 0) & (df.internet_service != "No")].churned.mean()
    out["churn_5plus_addons"] = df[df.n_addons >= 5].churned.mean()
    fig, ax = plt.subplots(figsize=(7, 3.8))
    ax.bar(g.index.astype(str), g["mean"] * 100, color=SERIES[0], width=0.6)
    for i, (m, n) in enumerate(zip(g["mean"], g["size"])):
        ax.text(i, m * 100 + 1, f"n={n:,}", ha="center", fontsize=8, color=INK_2)
    ax.set_xlabel("Number of add-on services (security, backup, protection, support, TV, movies)")
    ax.set_ylabel("Churn rate (%)")
    ax.set_title("Churn falls as customers add services", fontsize=11)
    out["figures"].append(save(fig, "07_addons", "Takeaway: bundling support and security is a retention lever, not only an upsell."))

    # contract x internet heatmap
    pv = df.pivot_table(index="contract", columns="internet_service", values="churned", aggfunc="mean")
    fig, ax = plt.subplots(figsize=(7, 3.6))
    im = ax.imshow(pv.values * 100, cmap="Blues", aspect="auto")
    ax.set_xticks(range(pv.shape[1]), pv.columns)
    ax.set_yticks(range(pv.shape[0]), pv.index)
    ax.grid(False)
    for i in range(pv.shape[0]):
        for j in range(pv.shape[1]):
            v = pv.values[i, j] * 100
            ax.text(j, i, f"{v:.0f}%", ha="center", va="center", fontsize=10, color="white" if v > 30 else "#0b0b0b")
    fig.colorbar(im, ax=ax, shrink=0.8).set_label("Churn rate (%)")
    out["m2m_fiber_churn"] = pv.loc["Month-to-month", "Fiber optic"]
    ax.set_title(f"Month-to-month fiber customers churn {pv.loc['Month-to-month', 'Fiber optic']:.0%}", fontsize=11)
    out["figures"].append(save(fig, "08_contract_internet", "Takeaway: contract type matters inside every internet product."))

    facts.update("eda", out)
    print(f"eda: {len(out['figures'])} figures")
    return out


if __name__ == "__main__":
    run()
