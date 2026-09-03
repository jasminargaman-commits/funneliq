# FunnelIQ

Marketing-intelligence tool for Northbound Media's funnel data — first of three final projects. Full brief: [`FunnelIQ_Assignment.html`](./FunnelIQ_Assignment.html).

**Status: design phase.** Architecture and leakage decisions are locked; repo/Supabase/Railway setup and the six work packages are not yet built.

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

## Local setup

_Not yet defined — no repo, environment, or dependency list exists yet. This section will cover cloning, installing dependencies, and required environment variables once the GitHub/Supabase/Railway pillars are set up._

## Live URL

_Not yet deployed._
