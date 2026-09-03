# FunnelIQ

Marketing-intelligence tool for Northbound Media's funnel data — first of three final projects. Full brief: [`FunnelIQ_Assignment.html`](./FunnelIQ_Assignment.html).

**Status: early scaffolding.** Architecture and leakage decisions are locked, this repo is live on GitHub, and a Supabase project is provisioned with `schema.sql` applied and real data loaded (3,490 rows, deduped). Login screen, Railway deploy, and the six work packages are not yet built.

Repo: https://github.com/jasminargaman-commits/funneliq

## Architecture

- **Supabase** — Postgres for the dataset (`funnel_records`, see [`schema.sql`](./schema.sql)) + Supabase Auth for the login screen. Row Level Security is enabled so the database itself enforces that only signed-in users can read data.
- **Railway API** — prediction only. Loads pre-trained `.pkl` models and serves predictions; never trains at request time.
- Models are trained **offline**, ahead of time; the deployed server only loads and serves them.
- The Supabase **service key stays local**, used only for the one-time data-load script — never shipped client-side or to Railway in a way that bypasses RLS.

## Decisions & analysis notebooks

- [`FunnelIQ_Decisions_Explained.ipynb`](./FunnelIQ_Decisions_Explained.ipynb) — walks through every architecture and leakage decision with reasoning, and reproduces the verification checks (nulls, duplicates, correlations, the `purchased`/`upsell` relationship) against the real dataset.
- [`02_EDA_and_Cleaning.ipynb`](./02_EDA_and_Cleaning.ipynb) — the Package 1 deliverable: missing-value handling, duplicate handling, correlation analysis against `cumulative_profit`, the `ad_budget` → `num_leads` relationship, and conversion rate by budget tier.
- [`funneliq_leakage_decisions.md`](./funneliq_leakage_decisions.md) — the leakage section for `REPORT.md`: per-package feature decisions and why.

## Dataset

`funnel_marketing_data.csv` — 3,500 rows, one row per customer/campaign record. See the notebooks above for the full column reference and data-quality findings.

**Not committed to the repo** (excluded via `.gitignore` as a data dump, per project guidelines) — place a local copy in the project root before running the notebooks or the load script. The canonical copy now lives in Supabase (`funnel_records`, 3,490 rows — 10 exact duplicates dropped by [`scripts/load_data.py`](./scripts/load_data.py)).

## Local setup

1. Clone the repo, place a local copy of `funnel_marketing_data.csv` in the project root (see [Dataset](#dataset)).
2. `python3 -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt`
3. Create a `.env` (never committed — see `.gitignore`) with:
   ```
   SUPABASE_URL=https://rvyxujlbqiiiydguehve.supabase.co
   SUPABASE_ANON_KEY=<Project Settings → API → anon/public key>
   SUPABASE_SERVICE_ROLE_KEY=<Project Settings → API → service_role key — local use only, never ship this>
   ```
4. Supabase project (`funneliq`, `eu-central-1`) is already provisioned with `schema.sql` applied and data loaded — no need to re-run `scripts/load_data.py` unless the CSV changes (it's safe to re-run: truncates then reloads, so it never duplicates rows).

## Live URL

_Not yet deployed._
