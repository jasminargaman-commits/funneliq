# FunnelIQ — Feature Leakage Decisions

A per-package record of which columns are legitimate features and which are leakage.
This is the `REPORT.md` section the brief explicitly asks for: *"If you include a feature
that looks like an outcome, write down why it's legitimately available at prediction time."*

---

## The one test

> **"Is this value already known at the moment I make the prediction?"**
> If **no** — it fills in only *later* — it is leakage. Exclude it.

Plus one rule that catches most FunnelIQ traps:

> **An outcome cannot predict another outcome.**
> `ltv_months`, `upsell`, `cumulative_profit`, and `referred` are all "how it ended."
> Using one to predict another is leakage, even when the correlation looks amazing.

---

## Column reference — when does each value become known?

| Tier | Meaning | Columns |
|---|---|---|
| **1. Funnel inputs** | Known before / at the start of the campaign | `ad_budget`, `num_leads`, `leads_answered`, `leads_not_answered` |
| **2. Funnel process** | Known during the sales process, before the customer outcome resolves | `followup_1`…`followup_5`, `calls_to_closed`, `calls_to_not_closed`, `closed`, `not_closed` |
| **3. Acquisition facts** | Known at the point of acquisition / conversion | `customer_acquisition_cost`, `purchased` |
| **4. Lifetime outcomes** | Only known *after* the relationship plays out | `upsell`, `ltv_months`, `cumulative_profit`, `referred` |

The rule of thumb: **Tier 4 columns are outcomes.** In any *prediction* package, at most one of
them is the target and the rest are off-limits.

---

## Per-package decisions

### Package 2 — Regression · target = `ltv_months`
**Assumed prediction moment:** at / just after acquisition ("we just got this customer — how long will they stay?").

- **Allowed:** Tier 1, Tier 2, Tier 3.
- **Leakage — exclude:** `upsell`, `cumulative_profit`, `referred` (sibling lifetime outcomes).
- **The brief's direct question — "Should `cumulative_profit` be a feature?"** → **No.**
  Profit accrues over the customer's whole lifetime, so it isn't known at the moment you're
  predicting lifetime. It's also mechanically tied to tenure (longer stay → more profit), so it
  would inflate the model spectacularly and teach it nothing usable. Textbook leakage.

### Package 3 — Classification · target = `upsell`
**Assumed prediction moment:** after purchase, to decide who to target with an upsell offer.

- **Allowed:** Tier 1, Tier 2, Tier 3 — **computed only on the `purchased == 1` subset.**
- **Leakage — exclude:** `ltv_months`, `cumulative_profit`, `referred` (Tier 4 siblings).
- **Decided — `purchased`: filter the dataset to `purchased == 1` before training, then drop `purchased`
  as a feature.** Verified against the real CSV: of 3,500 rows, 337 have `purchased == 0`, and **every
  single one** of them has `upsell == 0` — a customer can't buy "additional" services without an initial
  purchase, so `upsell` is deterministically 0 whenever `purchased == 0`. Left unfiltered, `purchased`
  becomes a trivial near-perfect predictor of `upsell == 0`: every metric (accuracy, F1, ROC-AUC) would
  look inflated while the model learns nothing about what actually drives upselling among real buyers.
  Among the 3,163 `purchased == 1` rows the target is well balanced (1,697 no-upsell vs. 1,466 upsell),
  so the filtered task is the meaningful one to model.

### Package 4 — Classification · target = `referred` (the "super customer" score)
**Prediction moment (from the brief):** **early** — *"given a new customer's early funnel data,
output a 0–100 likelihood."* This is the strictest package.

- **Allowed:** Tier 1 (early funnel). An engineered budget-tier feature (Low / Mid / High) from
  `ad_budget` is fine — it's derived from an allowed input.
- **Leakage — exclude:** `ltv_months`, `cumulative_profit`, `upsell`, and of course `referred`.
- **The trap to name out loud:** the super-customer *profile* is defined as
  `referred = Yes` **and** `upsell = 1` **and** long tenure. Those last two describe the very thing
  you're trying to anticipate early — so `upsell` and `ltv_months` are **definition, not features.**
  Using them would score customers on traits you only learn later, defeating "spot them earlier."
- **Conditional (⚠️):** full-funnel signals (`closed`, `calls_*`, `customer_acquisition_cost`) sit
  *after* "early." Decide per feature how early "early" is, and justify each one you keep.

### Package 6 — Regression · target = `cumulative_profit` (budget optimizer)
**This is NOT classic leakage — it's an availability-at-inference constraint.** The brief says the
simulator *"only knows each campaign's budget."*

- **Leakage — exclude regardless:** `ltv_months`, `upsell`, `referred` (Tier 4 siblings).
- **The real constraint:** funnel features (`num_leads`, `closed`, …) are legitimately correlated with
  profit and fine to **train** on — but at **simulation** time you'll only have `ad_budget`. Two valid designs:
  - **(a) Budget-only model** — train on `ad_budget` (and derived tier) alone. Simplest, no imputation.
  - **(b) Full-funnel model + imputation** — train on funnel features, then at sim time fill them in
    from a "typical funnel profile per budget level" (the brief's suggestion). More realistic, more work.
  - Pick one and write down why.

### Packages 1 & 5 — analysis, not prediction
`Package 1` (EDA / cleaning) and `Package 5` (the follow-up dropout analysis) are **descriptive**, not
predictive models with a held-out target. The leakage rule does **not** bite the same way — e.g. Package 5
legitimately *uses* `closed` to study which follow-up stage matters, because you're describing what
happened, not forecasting it. Don't over-apply the rule here.

---

## Summary matrix (cheat sheet)

Legend: ✅ allowed feature · ❌ leakage / exclude · ⚠️ conditional (see package notes) ·
🔒 used to filter rows, then dropped (not a model feature) · **T** = target

| Column | P2 `ltv_months` | P3 `upsell` | P4 `referred` (early) | P6 `cumulative_profit` |
|---|:--:|:--:|:--:|:--:|
| `ad_budget` | ✅ | ✅ | ✅ | ✅ (only sim input) |
| `num_leads` | ✅ | ✅ | ✅ | ⚠️ train / derive at sim |
| `leads_answered` | ✅ | ✅ | ✅ | ⚠️ |
| `leads_not_answered` | ✅ | ✅ | ✅ | ⚠️ |
| `followup_1…5` | ✅ | ✅ | ⚠️ | ⚠️ |
| `calls_to_closed` | ✅ | ✅ | ⚠️ | ⚠️ |
| `calls_to_not_closed` | ✅ | ✅ | ⚠️ | ⚠️ |
| `closed` | ✅ | ✅ | ⚠️ | ⚠️ |
| `not_closed` | ✅ | ✅ | ⚠️ | ⚠️ |
| `customer_acquisition_cost` | ✅ | ✅ | ⚠️ | ⚠️ |
| `purchased` | ✅ | 🔒 filter (not a feature) | ⚠️ | ⚠️ |
| `ltv_months` | **T** | ❌ | ❌ | ❌ |
| `upsell` | ❌ | **T** | ❌ | ❌ |
| `cumulative_profit` | ❌ | ❌ | ❌ | **T** |
| `referred` | ❌ | ❌ | **T** | ❌ |

---

## Assumptions & caveats (read before trusting the table)

1. **Row granularity is ambiguous.** The brief calls a row a "customer/campaign record," yet the columns
   mix campaign-level fields (`ad_budget`, `num_leads`) with customer-level outcomes (`ltv_months`,
   `referred`). This table assumes **one row = one acquired customer** and its originating funnel.
   Verify against the actual CSV once loaded — if a row is really a whole campaign, some calls shift.
2. **"Prediction moment" is a modeling choice.** P2/P3 assume acquisition-time; P4 assumes early-funnel
   (per the brief's wording). Change the moment and the ⚠️ cells move.
3. **Every ⚠️ needs a real decision + one written sentence.** That sentence is the deliverable the brief
   rewards — don't leave ambiguity in the code.
4. **`purchased` is not degenerate — confirmed against the real CSV** (3,163 `purchased==1` /
   337 `purchased==0`), which is exactly why it needs the Package 3 filter above rather than being
   dropped as useless.
5. **`num_leads` is an exact linear identity, not just a correlation:** verified `num_leads ==
   leads_answered + leads_not_answered` for all 3,500 rows, zero mismatches. Keeping all three as
   features anywhere is redundant (perfect multicollinearity) — fine for the tree-based models in this
   project (XGBoost/LightGBM/CatBoost split on one or the other), but worth a one-line note in
   `REPORT.md`'s feature-importance discussion so a reader doesn't mistake a low importance on one of
   the three for it not mattering.
6. **This document is your leakage section of `REPORT.md`.** Update the ⚠️ rows as you inspect the data.
