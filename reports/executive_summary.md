# Executive summary: who churns, what it costs, and where to spend the retention budget

*IBM Telco Customer Churn sample (real data), 7,043 customers. All figures come from `reports/facts.json`.*

## The problem

26.5% of customers (1,869) churned. They were paying $139k a month between them, which is
30.5% of monthly revenue and $1.7M a year. Churners pay more than the customers who stay
($74.44 vs $61.27 a month), so every lost customer is an above-average one.

## Who churns

- **Short commitments.** Month-to-month customers churn 43%, 15 times the two-year rate
  (3%).
- **New customers.** 55% of churners left within their first year; first-year churn is 47%.
- **Fiber and electronic check.** Fiber-optic customers churn 42% and electronic-check payers 45%.
- **No support services.** Customers without tech support churn 42% vs 15% with it.

The single worst segment is new month-to-month fiber customers: 13% of the base, 70% churn,
38% of lost revenue.

## What to do

Run a retention offer (20% off the bill for 6 months) for the **2,356 customers whose predicted churn
risk is at least 35%**. If the offer keeps 30% of the would-be churners for a year:

| | Value |
|---|---|
| Revenue kept over 12 months | $374k |
| Cost of the offer and outreach | $231k |
| **Net value** | **$143k** (ROI 62%) |
| **Break-even save rate** | **18.5%** |

Targeting everyone would lose $81.7k: the discount given to customers who were never going to leave costs more than it saves.
The ranked list is what makes the campaign pay.

## Structural fixes (beyond the campaign)

1. Move month-to-month customers to annual contracts at renewal with a small loyalty discount.
2. Fix the first-year experience for fiber customers (onboarding call, proactive support in month one).
3. Push automatic payment methods; electronic-check payers churn at 3.0 times the rate of automatic card payers
   (45% vs 15%).
4. Bundle tech support and online security into fiber plans.

## Next step

Pilot the offer on a random half of the target list for one quarter, compare churn with the other half, and replace the assumed
30% save rate with the measured one in `excel/retention_campaign_roi.xlsx`.
