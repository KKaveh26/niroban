"""Import scanner output into Niroban API.

This script logs into Supabase Auth using email/password, obtains an access token,
and imports opportunities plus a scan log into the protected Niroban backend.
The password is requested interactively and is not stored.
"""

from __future__ import annotations

import getpass
import json
import os
import sys
from pathlib import Path
from typing import Any

import httpx
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

NIROBAN_API_URL = os.getenv("NIROBAN_API_URL", "https://niroban-production.up.railway.app").rstrip("/")
SUPABASE_URL = os.getenv("VITE_SUPABASE_URL", "").rstrip("/")
SUPABASE_ANON_KEY = os.getenv("VITE_SUPABASE_ANON_KEY", "")
NIROBAN_EMAIL = os.getenv("NIROBAN_EMAIL", "")
SCAN_LOG_PATH = BASE_DIR / "output" / "setad_scan_log.json"


def require_env() -> None:
    missing = []
    for key, value in {
        "NIROBAN_API_URL": NIROBAN_API_URL,
        "VITE_SUPABASE_URL": SUPABASE_URL,
        "VITE_SUPABASE_ANON_KEY": SUPABASE_ANON_KEY,
        "NIROBAN_EMAIL": NIROBAN_EMAIL,
    }.items():
        if not value:
            missing.append(key)
    if missing:
        raise SystemExit(f"Missing environment variables in scanner/.env: {', '.join(missing)}")


def login() -> str:
    password = getpass.getpass(f"Supabase password for {NIROBAN_EMAIL}: ")
    url = f"{SUPABASE_URL}/auth/v1/token?grant_type=password"
    payload = {"email": NIROBAN_EMAIL, "password": password}
    headers = {"apikey": SUPABASE_ANON_KEY, "Content-Type": "application/json"}
    with httpx.Client(timeout=30) as client:
        response = client.post(url, headers=headers, json=payload)
    if response.status_code >= 400:
        raise SystemExit(f"Login failed: {response.status_code} {response.text}")
    token = response.json().get("access_token")
    if not token:
        raise SystemExit("Login response did not include access_token.")
    return token


def post_json(path: str, token: str, payload: dict[str, Any]) -> dict[str, Any]:
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    with httpx.Client(timeout=30) as client:
        response = client.post(f"{NIROBAN_API_URL}{path}", headers=headers, json=payload)
    if response.status_code >= 400:
        raise RuntimeError(f"POST {path} failed: {response.status_code} {response.text}")
    return response.json()


def main() -> int:
    require_env()
    if len(sys.argv) < 2:
        opportunities_file = BASE_DIR / "output" / "setad_opportunities.json"
    else:
        opportunities_file = Path(sys.argv[1])
        if not opportunities_file.is_absolute():
            opportunities_file = BASE_DIR / opportunities_file

    if not opportunities_file.exists():
        raise SystemExit(f"Opportunities file not found: {opportunities_file}")

    opportunities = json.loads(opportunities_file.read_text(encoding="utf-8"))
    if not isinstance(opportunities, list):
        raise SystemExit("Opportunities JSON must be a list.")

    token = login()
    imported = 0
    failed = 0
    for item in opportunities:
        try:
            post_json("/opportunities", token, item)
            imported += 1
        except Exception as exc:
            failed += 1
            print(f"Failed opportunity: {exc}")

    if SCAN_LOG_PATH.exists():
        try:
            scan_log = json.loads(SCAN_LOG_PATH.read_text(encoding="utf-8"))
            post_json("/scan-logs", token, scan_log)
            print("Scan log imported.")
        except Exception as exc:
            print(f"Scan log import failed: {exc}")

    print(f"Imported opportunities: {imported}")
    print(f"Failed opportunities: {failed}")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
