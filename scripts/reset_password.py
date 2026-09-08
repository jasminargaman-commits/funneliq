"""Reset an existing FunnelIQ user's password (admin-only, no email round-trip).

For internal/test accounts (e.g. test@northbound.example) that don't have a
real inbox, Supabase's dashboard "send password reset email" flow can't
reach them. This uses the service_role key (local only, never shipped) to
set the password directly via Supabase's admin API instead.

Usage:
    python scripts/reset_password.py test@northbound.example
    (prompts for a new password; use --password to pass it non-interactively)
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

    client = create_client(url, key)

    target = None
    page = 1
    while True:
        result = client.auth.admin.list_users(page=page, per_page=200)
        users = result if isinstance(result, list) else getattr(result, "users", [])
        if not users:
            break
        for u in users:
            if u.email == args.email:
                target = u
                break
        if target or len(users) < 200:
            break
        page += 1

    if not target:
        sys.exit(f"No user found with email {args.email}")

    password = args.password or getpass.getpass(f"New password for {args.email}: ")
    if len(password) < 6:
        sys.exit("Supabase requires passwords of at least 6 characters")

    client.auth.admin.update_user_by_id(target.id, {"password": password})
    print(f"Password updated for {args.email} (id: {target.id})")


if __name__ == "__main__":
    main()
