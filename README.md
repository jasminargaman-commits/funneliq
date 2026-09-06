# FunnelIQ

Marketing-intelligence tool for Northbound Media's funnel data — first of three final projects. Full brief: [`FunnelIQ_Assignment.html`](./FunnelIQ_Assignment.html).

**Status: early scaffolding.** Architecture and leakage decisions are locked, this repo is live on GitHub, a Supabase project is provisioned with `schema.sql` applied and real data loaded (3,490 rows, deduped), a minimal Railway skeleton is deployed and auto-deploying on every push to `main`, a working Supabase Auth login screen is live, and Package 2 (LTV regression) is trained and compared. Packages 3–6 are not yet built, and no package's prediction is exposed through the app yet.

Repo: https://github.com/jasminargaman-commits/funneliq

## Architecture

- **Supabase** — Postgres for the dataset (`funnel_records`, see [`schema.sql`](./schema.sql)) + Supabase Auth for the login screen (`static/index.html`). Row Level Security is enabled so the database itself enforces that only signed-in users can read data — verified independently at the REST level (an unauthenticated request returns an empty array, not the data).
- **Railway API** — prediction only. Loads pre-trained `.pkl` models and serves predictions; never trains at request time.
- Models are trained **offline**, ahead of time; the deployed server only loads and serves them.
- The Supabase **service key stays local**, used only for the one-time data-load script — never shipped client-side or to Railway in a way that bypasses RLS.

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

Trained models are saved to `models/` (`*.pkl`, git-ignored as an offline artifact — see the
architecture decision above) with a small committed `_meta.json` sidecar documenting what's in
each one. **Package 2 (LTV regression)**: XGBoost, LightGBM, and CatBoost compared via 5-fold CV;
CatBoost won (RMSE 2.87 months vs. a 12.4-month naive baseline, R² 0.946) and is saved as
`models/ltv_regressor.pkl`. All three models agree `calls_to_closed` is a top driver of customer
lifetime — see [`03_Package2_LTV_Regression.ipynb`](./03_Package2_LTV_Regression.ipynb) for the
full comparison and reasoning. Not yet exposed through the app (no Railway endpoint serves it
yet).

## Live URL

https://funneliq-api-production-15ca.up.railway.app — a login screen (Supabase Auth, email+password) plus a minimal dashboard that reads live from `funnel_records` as the signed-in user; `/health` for the health check. Deployed via Railway (`app/main.py` + `static/index.html`; the API itself is prediction-only per the architecture decision and holds no Supabase keys — auth and data reads happen entirely in the browser using the anon key and the user's own session, so RLS does the enforcing). Connected to this GitHub repo; auto-deploy on push to `main` is verified working.

Tested end-to-end in a real browser (both locally and against this live URL): sign-in, wrong-password error, live RLS-gated data read, sign-out, and confirmed a reload after sign-out does not silently restore the session.
