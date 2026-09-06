# FunnelIQ — Findings & Recommendations

A summary of what the data says about Northbound Media's funnel, and what to do about it. Each
section links to the notebook with the full analysis, code, and verification — this report is
the business-facing distillation, not a replacement for them.

## The one-paragraph version

Northbound has been optimizing on gut feel. The data says something consistent and somewhat
counter-intuitive across every one of the six work packages: **the customers who are cheapest
and fastest to acquire are, on every dimension measured, the best ones** — they stay longer, are
more likely to buy more, are more likely to refer a friend, and are dramatically more profitable.
The founder's instinct to spend more to get more is backwards for this business: past a fairly
low budget threshold, more spend buys *worse* customers, not better ones. Concretely: allocate ad
budget in the ₪2,000–5,000 range per campaign rather than a few large ones, treat "closed quickly"
as a positive quality signal rather than just a sales win, and don't cut the follow-up sequence
short — every recorded sale in this dataset required all five rounds.

## Cross-cutting theme: one signal keeps winning

`calls_to_closed` — how many calls it took to close a deal — is the single most recurring driver
across three independent models built for this project:

| Package | Target | `calls_to_closed`'s role |
|---|---|---|
| 2 (LTV) | `ltv_months` | Strongest feature in all 3 models; **negative** — fewer calls, longer tenure |
| 3 (Upsell) | `upsell` | Strongest feature in 2 of 3 models; fewer calls → more likely to upsell |
| 6 (Profit) | `cumulative_profit` | Strongest feature in 2 of 3 models; fewer calls → more profit |

A second, related throughline runs through Packages 1, 4, and 6: campaigns in the
**₪2,000–5,000 budget tier** convert best (Package 1), best predict which customers will become
future "super customers" (Package 4, where the engineered `budget_tier` feature dominates ~75%
of importance), and are dramatically the most profitable tier to fund (Package 6). Put together:
**cheap, easy, mid-budget conversions are simply better customers** — not a coincidence repeating
across four separate models trained independently on different targets.

## Package 1 — Exploration & cleaning
*[`02_EDA_and_Cleaning.ipynb`](./02_EDA_and_Cleaning.ipynb)*

- **Data quality**: 10 exact duplicate rows (dropped), 4 nulls in `ltv_months`, 29 in
  `cumulative_profit` (not imputed — see [`FunnelIQ_Decisions_Explained.ipynb`](./FunnelIQ_Decisions_Explained.ipynb)
  for why). `num_leads` is an exact sum of `leads_answered` + `leads_not_answered` for all 3,500
  rows — a perfect identity, not just a correlation.
- **`ad_budget` → `num_leads`**: diminishing returns — the first ₪1,000 spent buys noticeably
  more leads than the last ₪1,000 at a ₪20,000 budget.
- **Conversion rate by budget tier is non-monotonic**: Mid (₪2,000–5,000) converts at 8.29%,
  clearly beating both Low (4.70%) and High (5.37%). More budget does not straightforwardly buy
  a better conversion rate — the first hint of the theme that recurs through the rest of this
  report.

## Package 2 — Predicting customer lifetime
*[`03_Package2_LTV_Regression.ipynb`](./03_Package2_LTV_Regression.ipynb)*

CatBoost, XGBoost, and LightGBM compared via 5-fold CV on `ltv_months`. CatBoost wins narrowly
(RMSE **2.87 months** vs. a 12.4-month naive baseline, R² **0.946**). `cumulative_profit` was
excluded as a feature — it's 0.85-correlated with the target by mechanical construction (more
tenure → more profit), not because it's a legitimate early signal.

**Recommendation**: treat a high calls-to-close count as an early churn flag, not a sales win.
Customers who close quickly stay far longer than customers who had to be worked hard to convert
— route the latter into extra onboarding/retention attention right after they convert.

## Package 3 — Predicting upsell probability
*[`04_Package3_Upsell_Classification.ipynb`](./04_Package3_Upsell_Classification.ipynb)*

Filtered to `purchased == 1` (verified: `purchased == 0` deterministically implies `upsell == 0`
for all 337 such rows — leaving them in would make `purchased` a trivial predictor). Classes are
near-balanced (53.7%/46.3%), no imbalance handling needed. CatBoost wins on ROC-AUC (**0.785**).
A simple two-threshold business rule (`calls_to_closed` + `customer_acquisition_cost` vs. their
medians) reaches 70% accuracy against a 53.7% baseline and the model's 75.5% — a good manual
heuristic sales could use without any tooling, but the model catches meaningfully more real
upsell opportunities (83% recall vs. the rule's 59%).

**Recommendation**: the same lever as Package 2 — cheap, fast conversions are the best upsell
targets. A simple "flag if calls-to-close and CAC are both below the median" rule captures most
of the signal for free; the model is worth deploying for anyone who wants to maximize how many
real opportunities get caught, not just get a rough yes/no flag.

## Package 4 — The "super customer" score
*[`05_Package4_SuperCustomer_Score.ipynb`](./05_Package4_SuperCustomer_Score.ipynb)*

The strictest package: only genuinely *early*-funnel features are legitimate here (no
`calls_to_closed`, CAC, or `closed` — those don't exist yet when the brief wants this score
computed). A tuned CatBoost classifier using `ad_budget`, lead counts, and an engineered
`budget_tier` categorical reaches ROC-AUC **0.776**. `budget_tier` alone accounts for ~75% of the
model's importance — dwarfing the raw numeric features.

**The profile that matters most for this report**: super customers (referred someone, upsold,
and stayed longer than the median tenure) are **27% of all customers but generate 53.6% of total
profit** — and they're *cheaper* to acquire (~₪1,003 average CAC) than everyone else (~₪1,510).

**Recommendation**: Northbound doesn't need to wait a year to guess who's a future super
customer. The `budget_tier` of the campaign that brought someone in, combined with an early read
on how cheaply they're converting, is already a meaningful signal — visible from day one, not
after the fact.

## Package 5 — The follow-up paradox
*[`06_Package5_Followup_Dropout.ipynb`](./06_Package5_Followup_Dropout.ipynb)*

Testing the sales manager's claim: *"after the 3rd follow-up, we're just wasting time."*
Descriptive only — no model. Two structural findings, both verified with zero exceptions across
all 3,490 rows: the funnel monotonically shrinks at every stage, and every recorded close
requires completing **all five** follow-up rounds (`followup_5 == closed + not_closed` exactly).

Dropout by stage is not the smoothly-worsening curve the manager's claim implies — it's
**lowest** right after the 3rd follow-up (10.4%, the stickiest point in the whole funnel) and
spikes at the final stage (29.2%). Investigated that spike further: it's uniform across every
budget tier and campaign (std only 7.2%, no meaningful correlation to anything else recorded) —
the quantitative ceiling of what this data can explain; a real fix needs operational data (call
quality, timing, script) this dataset doesn't capture.

**Recommendation**: don't cut follow-ups short. Stopping after round 3 would forfeit 100% of
this dataset's closed deals. If there's a real problem, it's an operational one at round 5, not
a "stop trying" one at round 3.

## Package 6 — Budget optimization
*[`07_Package6_Budget_Optimization.ipynb`](./07_Package6_Budget_Optimization.ipynb)*

The clearest illustration of the report's central theme. `ad_budget` vs. `cumulative_profit` is
not a smooth diminishing-returns curve — it's a **step function**. Expected profit per campaign
jumps roughly 6–10x between the ₪500–1,500 tier and the ₪2,000–5,000 tier, then drops back down
for every budget from ₪6,000 to ₪20,000, despite costing more to run. Profit-per-shekel peaks
sharply at exactly ₪2,000.

A full-funnel CatBoost regressor (RMSE 5,327 vs. a 10,976 baseline) combined with a typical
funnel profile and purchase rate per budget level powers a simulator comparing allocation
strategies for Northbound's ₪50,000/month:

| Strategy | Expected total profit |
|---|---|
| 2×₪20k + 1×₪10k | ₪13,155 |
| 10×₪5k | ₪238,168 |
| **25×₪2k** | **₪600,108** |
| 100×₪500 | ₪75,529 |

**Recommendation**: allocate the ₪50,000 as roughly **25 campaigns of ₪2,000 each** instead of a
handful of large campaigns or a spray of tiny ones — worth ~46x more expected profit than the
most concentrated option, for the identical spend. Neither concentrating nor maximally spreading
wins; hitting the sweet-spot campaign size and replicating it does. Worth a real pilot before
committing the full budget, given the model's RMSE implies real variance around these averages.

## What to tell the founder, in priority order

1. **Reallocate the ad budget** into ~25 campaigns of ₪2,000 rather than a few large ones — the
   single largest lever found in this project (Package 6).
2. **Stop treating "closed fast" as just a sales metric** — it's the strongest predictor of
   lifetime value, upsell likelihood, and profit found across three independent models. Build it
   into how leads get scored and prioritized (Packages 2, 3, 6).
3. **Don't shorten the follow-up sequence.** The sales team's instinct is backwards here —
   dropout is lowest right where they think it's wasted, and every recorded sale needed all five
   rounds (Package 5).
4. **Watch `budget_tier` and early conversion cost as a super-customer signal** from day one,
   rather than waiting for tenure/upsell/referral data to accumulate (Package 4).

## Live app

https://funneliq-api-production-15ca.up.railway.app — sign in and try all four live
prediction/simulation panels. See [`README.md`](./README.md) for endpoint details, architecture,
and local setup.

## Full decision record

[`FunnelIQ_Decisions_Explained.ipynb`](./FunnelIQ_Decisions_Explained.ipynb) and
[`funneliq_leakage_decisions.md`](./funneliq_leakage_decisions.md) cover every architecture and
leakage decision behind this project in detail, including the ones that turned out to matter most
(the `purchased == 1` filters, the strict early-only feature cut in Package 4, and the modeling
artifact conventions followed throughout).
