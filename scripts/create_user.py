"""Provision a FunnelIQ team account.

FunnelIQ is an internal tool (per the project brief) -- there is no public
sign-up flow. New team members are added by an admin running this script,
which uses the service_role key (local only, never shipped) to create a
pre-confirmed user via Supabase's admin API.

Usage:
    python scripts/create_user.py teammate@northbound.example
    (prompts for a password; use --password to pass it non-interactively)
"""

import argparse
import getpass
import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from supabase import create_client

PROJECT_ROOT = Path(__file__).resolve().parent.parent


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("email")
    parser.add_argument("--password", help="Omit to be prompted (not echoed)")
    args = parser.parse_args()

    load_dotenv(PROJECT_ROOT / ".env")
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
    if not url or not key or key.startswith("paste-from-dashboard"):
        sys.exit("SUPABASE_URL / SUPABASE_SERVICE_ROLE_KEY missing or not set in .env")

    password = args.password or getpass.getpass(f"Password for {args.email}: ")
    if len(password) < 6:
        sys.exit("Supabase requires passwords of at least 6 characters")

    client = create_client(url, key)
    result = client.auth.admin.create_user({
        "email": args.email,
        "password": password,
        "email_confirm": True,  # pre-confirmed -- no verification email needed
    })
    print(f"Created user {result.user.email} (id: {result.user.id})")


if __name__ == "__main__":
    main()
