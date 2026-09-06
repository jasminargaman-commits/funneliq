# FunnelIQ

Marketing-intelligence tool for Northbound Media's funnel data — first of three final projects. Full brief: [`FunnelIQ_Assignment.html`](./FunnelIQ_Assignment.html).

**Status: early scaffolding.** Architecture and leakage decisions are locked, this repo is live on GitHub, a Supabase project is provisioned with `schema.sql` applied and real data loaded (3,490 rows, deduped), a minimal Railway skeleton is deployed and auto-deploying on every push to `main`, a working Supabase Auth login screen is live, and Package 2 (LTV regression) is trained, compared, and **live in the app** — sign in and get a real prediction. Packages 3–6 are not yet built.

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
decision above) with a `_meta.json` sidecar documenting what's in each one. **Package 2 (LTV
regression)**: XGBoost, LightGBM, and CatBoost compared via 5-fold CV; CatBoost won (RMSE 2.87
months vs. a 12.4-month naive baseline, R² 0.946) and is saved as `models/ltv_regressor.pkl`. All
three models agree `calls_to_closed` is a top driver of customer lifetime — see
[`03_Package2_LTV_Regression.ipynb`](./03_Package2_LTV_Regression.ipynb) for the full comparison
and reasoning. **Live in the app**: `POST /predict/ltv` (see below).

## Live URL

https://funneliq-api-production-15ca.up.railway.app — a login screen (Supabase Auth, email+password), a dashboard that reads live from `funnel_records` as the signed-in user, and a Package 2 LTV prediction form; `/health` for the health check. Deployed via Railway (`app/main.py` + `static/index.html`).

`POST /predict/ltv` takes a customer's early funnel data (the 15 features listed in `models/ltv_regressor_meta.json`) and returns `{"predicted_ltv_months": ..., "model": "CatBoost"}`. Requires a valid Supabase session — the endpoint calls Supabase's own `/auth/v1/user` to verify the caller's bearer token server-side before predicting; a request with no token or an invalid one gets a 401, never a prediction. Data reads still happen entirely in the browser using the anon key and the user's own session (RLS enforces access there), but a prediction request goes through the API, which is why it needs its own auth check.

Connected to this GitHub repo; auto-deploy on push to `main` is verified working.

Tested end-to-end in a real browser (both locally and against this live URL): sign-in, wrong-password error, live RLS-gated data read, sign-out (confirmed a reload afterward doesn't silently restore the session), and the LTV prediction form (matches a direct curl test exactly, and rejects both a missing and an invalid bearer token with 401).
