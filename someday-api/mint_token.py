#!/usr/bin/env python3
"""Mint a Supabase access token for a test user via the admin API.

Usage: python3 mint_token.py [email]    (default test1@someday.dev)
Prints the access_token to stdout.
"""

import sys

import httpx

from config.settings import settings


def mint(email: str) -> str:
    service_key = settings.SUPABASE_SERVICE_ROLE_KEY
    base = settings.SUPABASE_URL

    # Ensure the user exists and is confirmed (422 email_exists is fine)
    httpx.post(
        f"{base}/auth/v1/admin/users",
        headers={"apikey": service_key, "Authorization": f"Bearer {service_key}"},
        json={"email": email, "email_confirm": True},
        timeout=15,
    )

    link = httpx.post(
        f"{base}/auth/v1/admin/generate_link",
        headers={"apikey": service_key, "Authorization": f"Bearer {service_key}"},
        json={"type": "magiclink", "email": email},
        timeout=15,
    )
    link.raise_for_status()
    token_hash = link.json()["hashed_token"]

    session = httpx.post(
        f"{base}/auth/v1/verify",
        headers={"apikey": settings.SUPABASE_ANON_KEY},
        json={"type": "magiclink", "token_hash": token_hash},
        timeout=15,
    )
    session.raise_for_status()
    return session.json()["access_token"]


if __name__ == "__main__":
    email = sys.argv[1] if len(sys.argv) > 1 else "test1@someday.dev"
    print(mint(email))
