"""Load funnel_marketing_data.csv into the Supabase funnel_records table.

Repeatable: truncates the table before inserting, so running this twice never
duplicates rows. Uses the service_role key (bypasses RLS) — never run this
from anything but a trusted local/CI environment; the key must stay out of
the browser and out of git (see .env / .gitignore).

Cleaning applied here matches the decisions in 02_EDA_and_Cleaning.ipynb:
exact duplicate rows are dropped before loading. Everything else is loaded
as-is — per-package cleaning (e.g. dropping null-target rows) happens later,
offline, at model-training time, not here.
"""

import os
import sys
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv
from supabase import create_client

PROJECT_ROOT = Path(__file__).resolve().parent.parent
CSV_PATH = PROJECT_ROOT / "funnel_marketing_data.csv"
TABLE = "funnel_records"
BATCH_SIZE = 500

# Must match schema.sql's column order/names exactly.
COLUMNS = [
    "ad_budget", "num_leads", "leads_answered", "leads_not_answered",
    "followup_1", "followup_2", "followup_3", "followup_4", "followup_5",
    "not_closed", "closed", "calls_to_closed", "calls_to_not_closed",
    "customer_acquisition_cost", "purchased", "ltv_months", "upsell",
    "cumulative_profit", "referred",
]


def load_env():
    load_dotenv(PROJECT_ROOT / ".env")
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
    if not url or not key or key.startswith("paste-from-dashboard"):
        sys.exit("SUPABASE_URL / SUPABASE_SERVICE_ROLE_KEY missing or not set in .env")
    return url, key


def load_dataframe():
    if not CSV_PATH.exists():
        sys.exit(f"{CSV_PATH} not found — place funnel_marketing_data.csv in the project root")
    df = pd.read_csv(CSV_PATH)

    before = len(df)
    df = df.drop_duplicates().reset_index(drop=True)
    dropped = before - len(df)
    print(f"rows in CSV: {before} (dropped {dropped} exact duplicates)")

    missing = [c for c in COLUMNS if c not in df.columns]
    if missing:
        sys.exit(f"CSV is missing expected columns: {missing}")

    df = df[COLUMNS]
    # NaN -> None so the client sends valid JSON null (only ltv_months /
    # cumulative_profit are nullable per schema.sql).
    df = df.astype(object).where(pd.notna(df), None)
    return df.to_dict(orient="records")


def main():
    url, key = load_env()
    client = create_client(url, key)
    records = load_dataframe()

    print(f"truncating {TABLE}...")
    client.table(TABLE).delete().gte("id", 0).execute()

    print(f"inserting {len(records)} rows in batches of {BATCH_SIZE}...")
    for i in range(0, len(records), BATCH_SIZE):
        batch = records[i:i + BATCH_SIZE]
        client.table(TABLE).insert(batch).execute()
        print(f"  {min(i + BATCH_SIZE, len(records))}/{len(records)}")

    count = client.table(TABLE).select("id", count="exact").limit(1).execute()
    print(f"done. rows now in {TABLE}: {count.count}")


if __name__ == "__main__":
    main()
