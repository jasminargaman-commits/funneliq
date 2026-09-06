# FunnelIQ

Marketing-intelligence tool for Northbound Media's funnel data — first of three final projects. Full brief: [`FunnelIQ_Assignment.html`](./FunnelIQ_Assignment.html).

**Status: all six work packages complete.** Architecture and leakage decisions are locked, this repo is live on GitHub, a Supabase project is provisioned with `schema.sql` applied and real data loaded (3,490 rows, deduped), a minimal Railway skeleton is deployed and auto-deploying on every push to `main`, a working Supabase Auth login screen is live, Packages 2 (LTV regression), 3 (upsell classification), 4 (super-customer score), and 6 (budget optimization) are trained, compared, and **live in the app**, and Package 5 (follow-up dropout analysis) is done with its findings surfaced as a dashboard panel. Remaining: `REPORT.md`, GitHub Actions CI, and the optional demo recording.

Repo: https://github.com/jasminargaman-commits/funneliq

## Architecture

- **Supabase** — Postgres for the dataset (`funnel_records`, see [`schema.sql`](./schema.sql)) + Supabase Auth for the login screen (`static/index.html`). Row Level Security is enabled so the database itself enforces that only signed-in users can read data — verified independently at the REST level (an unauthenticated request returns an empty array, not the data).
- **Railway API** — prediction only. Loads pre-trained `.pkl` models and serves predictions; never trains at request time. Prediction endpoints verify the caller's Supabase session token server-side (via Supabase's own `/auth/v1/user`, using only the anon key) before responding — a stranger can't get predictions without signing in.
- Models are trained **offline**, ahead of time; the deployed server only loads and serves them. Small `.pkl` files (this project's models are all well under 1MB) are committed directly since Railway builds straight from this repo and needs them present — see the modeling artifact convention in `FunnelIQ_Decisions_Explained.ipynb`.
- The Supabase **service key stays local**, used only for the one-time data-load script and account provisioning — never shipped client-side or to Railway. Railway only ever holds the public `SUPABASE_URL` / `SUPABASE_ANON_KEY`.

## Decisions & analysis notebooks

- [`FunnelIQ_Decisions_Explained.ipynb`](./FunnelIQ_Decisions_Explained.ipynb) — walks through every architecture and leakage decision with reasoning, and reproduces the verification checks (nulls, duplicates, correlations, the `purchased`/`upsell` relationship) against the real dataset.
- [`02_EDA_and_Cleaning.ipynb`](./02_EDA_and_Cleaning.ipynb) — the Package 1 deliverable: missing-value handling, duplicate handling, correlation analysis against `cumulative_profit`, the `ad_budget` → `num_leads` relationship, and conversion rate by budget tier.
- [`03_Package2_LTV_Regression.ipynb`](./03_Package2_LTV_Regression.ipynb) — the Package 2 deliverable: XGBoost/LightGBM/CatBoost compared via 5-fold CV on `ltv_months`, feature-importance agreement across the three, and the trained model saved to `models/` for later serving.
- [`04_Package3_Upsell_Classification.ipynb`](./04_Package3_Upsell_Classification.ipynb) — the Package 3 deliverable: same three models compared via 5-fold stratified CV on `upsell` (filtered to `purchased==1`), class-balance check, a simple business rule vs. the model, and the trained classifier saved to `models/`.
- [`05_Package4_SuperCustomer_Score.ipynb`](./05_Package4_SuperCustomer_Score.ipynb) — the Package 4 deliverable: a tuned CatBoost classifier on `referred` using only genuinely early-funnel features plus an engineered `budget_tier` categorical, a manual hyperparameter search, and the super-customer profit/CAC profile.
- [`06_Package5_Followup_Dropout.ipynb`](./06_Package5_Followup_Dropout.ipynb) — the Package 5 deliverable: dropout rate at each follow-up stage, the funnel's structural identity (`followup_5 == closed + not_closed`, zero exceptions), and a recommendation testing the sales manager's "wasted effort past round 3" claim against the data.
- [`07_Package6_Budget_Optimization.ipynb`](./07_Package6_Budget_Optimization.ipynb) — the Package 6 deliverable: a full-funnel profit model + a typical-funnel-profile-per-budget-level lookup, revealing that `ad_budget` vs. profit is a step function (not a smooth curve) with a sharp sweet spot at ₪2,000, and a simulator comparing the brief's four allocation strategies.
- [`funneliq_leakage_decisions.md`](./funneliq_leakage_decisions.md) — the leakage section for `REPORT.md`: per-package feature decisions and why.

## Dataset

`funnel_marketing_data.csv` — 3,500 rows, one row per customer/campaign record. See the notebooks above for the full column reference and data-quality findings.

**Not committed to the repo** (excluded via `.gitignore` as a data dump, per project guidelines) — place a local copy in the project root before running the notebooks or the load script. The canonical copy now lives in Supabase (`funnel_records`, 3,490 rows — 10 exact duplicates dropped by [`scripts/load_data.py`](./scripts/load_data.py)).

## Local setup

1. Clone the repo, place a local copy of `funnel_marketing_data.csv` in the project root (see [Dataset](#dataset)).
2. `python3 -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt`
   - **macOS only:** XGBoost and LightGBM need the OpenMP runtime, which isn't a Python package — `brew install libomp` before the pip install above, or `import xgboost` will fail with a `libomp.dylib` load error.
3. Register the venv as its own Jupyter kernel so notebooks actually use these pinned versions instead of silently falling back to some other Python: `python -m ipykernel install --user --name funneliq-venv --display-name "FunnelIQ (.venv)"`. Select **"FunnelIQ (.venv)"** as the kernel when opening any notebook in this repo.
4. Create a `.env` (never committed — see `.gitignore`) with:
   ```
   SUPABASE_URL=https://rvyxujlbqiiiydguehve.supabase.co
   SUPABASE_ANON_KEY=<Project Settings → API → anon/public key>
   SUPABASE_SERVICE_ROLE_KEY=<Project Settings → API → service_role key — local use only, never ship this>
   ```
5. Supabase project (`funneliq`, `eu-central-1`) is already provisioned with `schema.sql` applied and data loaded — no need to re-run `scripts/load_data.py` unless the CSV changes (it's safe to re-run: truncates then reloads, so it never duplicates rows).
6. FunnelIQ is an internal tool — there's no public sign-up. Provision a team account with `python scripts/create_user.py you@example.com` (uses the service_role key locally to create a pre-confirmed user).

## Modeling

Trained models are saved to `models/` (small `.pkl` files, committed — see the architecture
decision above) with a `_meta.json` sidecar documenting what's in each one.

- **Package 2 (LTV regression)**: XGBoost, LightGBM, and CatBoost compared via 5-fold CV; CatBoost
  won (RMSE 2.87 months vs. a 12.4-month naive baseline, R² 0.946) and is saved as
  `models/ltv_regressor.pkl`. All three models agree `calls_to_closed` is a top driver of
  customer lifetime — see
  [`03_Package2_LTV_Regression.ipynb`](./03_Package2_LTV_Regression.ipynb). **Live**:
  `POST /predict/ltv`.
- **Package 3 (upsell classification)**: same three models, 5-fold *stratified* CV on `upsell`
  (rows filtered to `purchased==1`). Classes are near-balanced (53.7%/46.3%) so no imbalance
  handling was needed. CatBoost won again on ROC-AUC (0.785); `calls_to_closed` and
  `customer_acquisition_cost` dominate, the same top feature as Package 2. A simple business rule
  on those two features reaches 0.70 accuracy vs. the model's 0.755 and a 0.537 baseline — see
  [`04_Package3_Upsell_Classification.ipynb`](./04_Package3_Upsell_Classification.ipynb). **Live**:
  `POST /predict/upsell`.
- **Package 4 (super-customer score)**: a single tuned CatBoost classifier on `referred` (rows
  filtered to `purchased==1`), restricted to genuinely *early*-funnel features only — no
  `calls_to_closed`/CAC/`closed` here, unlike Packages 2–3, since the brief specifically wants a
  score computable before the sales process plays out. Adds an engineered `budget_tier`
  categorical (Low/Mid/High), which ends up dominating feature importance (~75%) — connecting
  back to Package 1's non-monotonic conversion-by-budget-tier finding. Manually grid-searched
  hyperparameters (worked around a `sklearn`/CatBoost `clone()` incompatibility with
  `cat_features`) for a modest lift over CatBoost's defaults (ROC-AUC 0.776 vs. 0.768). Profile:
  super customers are 27% of the base but generate 53.6% of total profit, at a *lower* average
  CAC than everyone else — see
  [`05_Package4_SuperCustomer_Score.ipynb`](./05_Package4_SuperCustomer_Score.ipynb). **Live**:
  `POST /predict/super_customer`.
- **Package 5 (follow-up dropout, descriptive — no model)**: confirms the funnel is a strict
  monotonic decline with an exact identity, `followup_5 == closed + not_closed`, holding for all
  3,490 rows with zero exceptions — meaning every recorded close required completing all five
  follow-up rounds. Aggregate dropout by stage is *not* the smoothly-increasing curve the sales
  manager's "wasted effort past round 3" claim implies: it's lowest right after round 3 (10.4%)
  and spikes at the final stage (29.2%) instead. Recommendation: don't cut follow-ups short — see
  [`06_Package5_Followup_Dropout.ipynb`](./06_Package5_Followup_Dropout.ipynb). Surfaced as a
  static chart + recommendation panel on the dashboard (no serving endpoint needed).
- **Package 6 (budget optimization)**: `ad_budget` vs. `cumulative_profit` is not a smooth
  diminishing-returns curve — it's a step function. Expected profit per campaign jumps ~6-10x
  between the ₪500-1,500 tier and the ₪2,000-5,000 tier, then drops back down for every budget
  from ₪6,000 to ₪20,000, despite costing more to run. A full-funnel CatBoost regressor (RMSE
  5,327 vs. a 10,976 baseline) combined with a typical-funnel-profile-per-budget lookup and each
  budget's empirical purchase rate powers a simulator: for the brief's four ₪50,000 allocation
  strategies, **25×₪2,000 campaigns wins by ~46x** over the worst option (₪600,108 vs. ₪13,155
  for 2×₪20k+1×₪10k) — neither concentrating nor maximally spreading wins, hitting the sweet spot
  size and replicating it does — see
  [`07_Package6_Budget_Optimization.ipynb`](./07_Package6_Budget_Optimization.ipynb). **Live**:
  `POST /simulate/budget`.

## Live URL

https://funneliq-api-production-15ca.up.railway.app — a login screen (Supabase Auth, email+password), a dashboard that reads live from `funnel_records` as the signed-in user, prediction forms for Packages 2, 3, and 4, a Package 5 dropout-analysis panel, and a Package 6 budget-strategy simulator; `/health` for the health check. Deployed via Railway (`app/main.py` + `static/index.html`).

All prediction/simulation endpoints require a valid Supabase session — each calls Supabase's own `/auth/v1/user` to verify the caller's bearer token server-side before responding; a request with no token or an invalid one gets a 401. Data reads still happen entirely in the browser using the anon key and the user's own session (RLS enforces access there), but these requests go through the API, which is why each needs its own auth check.

- `POST /predict/ltv` — the 15 features in `models/ltv_regressor_meta.json` → `{"predicted_ltv_months": ..., "model": "CatBoost"}`
- `POST /predict/upsell` — the 14 features in `models/upsell_classifier_meta.json` (a customer who has already purchased) → `{"upsell_probability": ..., "predicted_upsell": true/false, "model": "CatBoost"}`
- `POST /predict/super_customer` — the 4 early-funnel features in `models/super_customer_classifier_meta.json` (the API engineers `budget_tier` server-side) → `{"super_customer_score": 0-100, "model": "CatBoost"}`
- `POST /simulate/budget` — a list of `{ad_budget, count}` campaigns (budgets restricted to the 16 levels in `models/budget_profiles.json`) → a per-campaign breakdown plus `total_spend` and `total_expected_profit`

Connected to this GitHub repo; auto-deploy on push to `main` is verified working.

Tested end-to-end in a real browser (both locally and against this live URL): sign-in, wrong-password error, live RLS-gated data read, sign-out (confirmed a reload afterward doesn't silently restore the session), and all four prediction/simulation panels (each matches a direct curl test exactly, and each rejects a missing or invalid bearer token with 401). One real bug was caught and fixed this way: a `--green` CSS variable used by both the Package 5 recommendation border and the Package 6 winner bar was never defined in `:root`, so both silently rendered without their intended color — fixed and reverified before deploying.
