-- FunnelIQ — database schema
-- Run this in the Supabase SQL editor (or via the CLI) once, before loading data.
-- One table holds the dataset; the app reads from it at runtime for insight panels.
-- Models are trained OFFLINE from the CSV/table — nothing here trains anything.

-- ----------------------------------------------------------------------------
-- 1. The dataset table
-- ----------------------------------------------------------------------------
-- Columns are loaded AS-IS from funnel_marketing_data.csv (no transforms) so the
-- load script stays simple and repeatable. Cleaning for MODELING happens offline,
-- per package — the table is the raw source of truth the app surfaces.

create table if not exists funnel_records (
  id                          bigint generated always as identity primary key,

  -- Tier 1: funnel inputs
  ad_budget                   integer  not null,
  num_leads                   integer  not null,
  leads_answered              integer  not null,
  leads_not_answered          integer  not null,

  -- Tier 2: funnel process
  followup_1                  integer  not null,
  followup_2                  integer  not null,
  followup_3                  integer  not null,
  followup_4                  integer  not null,
  followup_5                  integer  not null,
  not_closed                  integer  not null,
  closed                      integer  not null,
  calls_to_closed             integer  not null,
  calls_to_not_closed         integer  not null,

  -- Tier 3: acquisition facts
  customer_acquisition_cost   integer  not null,
  purchased                   smallint not null,   -- 0 / 1

  -- Tier 4: lifetime outcomes (nullable ones are the ~1% missing targets)
  ltv_months                  numeric,             -- 4 nulls in source
  upsell                      smallint not null,   -- 0 / 1
  cumulative_profit           numeric,             -- 29 nulls in source
  referred                    text     not null    -- 'Yes' / 'No'
);

-- ----------------------------------------------------------------------------
-- 2. Row Level Security — the rules carved into the vault
-- ----------------------------------------------------------------------------
-- Without this, anyone with the public anon key could read every row.
-- With it, Postgres itself enforces that only a logged-in user sees the data —
-- even if the app code forgets to check. This is the whole point of the auth exercise.

alter table funnel_records enable row level security;

-- Any authenticated (logged-in) user may READ all rows.
create policy "authenticated can read funnel records"
  on funnel_records
  for select
  to authenticated
  using (true);

-- Note: no INSERT/UPDATE/DELETE policy is defined for normal users on purpose.
-- The one-time data load runs from your machine with the SERVICE key, which
-- bypasses RLS — so it doesn't need a policy, and regular app users can't write.
