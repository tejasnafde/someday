#!/usr/bin/env python3
"""
Someday API smoke test.

Usage:
    python3 smoke_test.py <access_token>

Runs every endpoint in dependency order, extracts IDs from responses,
and prints a pass/fail summary. Paste the full output back to Claude
if anything fails.
"""

import base64
import json
import sys
import time

import httpx

# ── Config ────────────────────────────────────────────────────────────────────

TOKEN = sys.argv[1] if len(sys.argv) > 1 else ""
BASE  = "http://localhost:8000"

if not TOKEN:
    print("Usage: python3 smoke_test.py <access_token>")
    sys.exit(1)

# ── Token expiry check ────────────────────────────────────────────────────────

def _decode_jwt_payload(token: str) -> dict:
    try:
        part = token.split(".")[1]
        part += "=" * (-len(part) % 4)
        return json.loads(base64.urlsafe_b64decode(part))
    except Exception:
        return {}

_payload = _decode_jwt_payload(TOKEN)
_exp = _payload.get("exp", 0)
_now = int(time.time())

if _exp and _exp < _now:
    ago = _now - _exp
    print(f"\033[0;31m✗ Token expired {ago}s ago ({ago//60} mins). Get a fresh magic link.\033[0m")
    print(f"  sub:   {_payload.get('sub')}")
    print(f"  email: {_payload.get('email')}")
    sys.exit(1)

_ttl = _exp - _now if _exp else "?"
print(f"\033[0;32m✓ Token valid - expires in {_ttl}s\033[0m")

HEADERS = {
    "Authorization": f"Bearer {TOKEN}",
    "Content-Type":  "application/json",
}

# ── Helpers ───────────────────────────────────────────────────────────────────

GRN  = "\033[0;32m"
RED  = "\033[0;31m"
BLU  = "\033[1;34m"
YEL  = "\033[0;33m"
DIM  = "\033[2m"
RST  = "\033[0m"
BOLD = "\033[1m"

results: list[dict] = []

def req(
    label:  str,
    method: str,
    path:   str,
    *,
    expect: int = 200,
    body:   dict | None = None,
    note:   str = "",
) -> dict:
    """Make a request, print result, return parsed JSON (or {})."""
    url = f"{BASE}{path}"
    print(f"\n{BLU}{BOLD}▶ {label}{RST}")
    if note:
        print(f"  {DIM}{note}{RST}")

    try:
        r = httpx.request(
            method, url, headers=HEADERS,
            json=body, timeout=10.0,
        )
        status = r.status_code
        try:
            data = r.json()
        except Exception:
            data = {"_raw": r.text}

        ok = status == expect
        icon = f"{GRN}✓" if ok else f"{RED}✗"
        exp  = "" if ok else f" (expected {expect})"
        print(f"  {icon} {status}{exp}{RST}")
        print("  " + json.dumps(data, indent=2, default=str).replace("\n", "\n  "))

        results.append({"label": label, "status": status, "ok": ok})
        return data

    except httpx.ConnectError:
        print(f"  {RED}✗ CONNECTION REFUSED - is the server running?{RST}")
        results.append({"label": label, "status": 0, "ok": False})
        return {}
    except Exception as exc:
        print(f"  {RED}✗ ERROR: {exc}{RST}")
        results.append({"label": label, "status": 0, "ok": False})
        return {}


# ── Smoke tests ───────────────────────────────────────────────────────────────

print(f"\n{'='*60}")
print(f"  Someday API Smoke Test")
print(f"  {BASE}")
print(f"{'='*60}")

# 1. Health check (no auth needed)
req("GET /health", "GET", "/health",
    note="No auth - should always return 200")

# 2. Upsert user from JWT
me = req("POST /auth/verify", "POST", "/auth/verify", expect=200,
    note="Upserts user row from JWT payload")

user_id = (me.get("user") or {}).get("id", "")
print(f"\n  {YEL}→ user_id = {user_id}{RST}")

if not user_id:
    print(f"\n{RED}Auth failed - aborting. Check token and server logs.{RST}")
    sys.exit(1)

# 3. Get current user + circles
req("GET /auth/me", "GET", "/auth/me",
    note="Returns user profile + circle list")

# 4. Create a circle
circle = req("POST /circles", "POST", "/circles", expect=201,
    body={"name": "Smoke Test Circle", "emoji": None},
    note="Create a new circle - caller becomes owner + member")

circle_id = circle.get("id", "")
print(f"\n  {YEL}→ circle_id = {circle_id}{RST}")

# 5. List my circles
req("GET /circles", "GET", "/circles",
    note="Should include the circle we just created")

# 6. Get circle detail
req("GET /circles/:id", "GET", f"/circles/{circle_id}",
    note="Should include members list")

# 7. Rename the circle
req("PATCH /circles/:id", "PATCH", f"/circles/{circle_id}",
    body={"name": "Renamed Smoke Circle"},
    note="Owner-only rename")

# 8. Unfurl a URL
unfurl = req("POST /unfurl", "POST", "/unfurl",
    body={"url": "https://www.youtube.com/watch?v=Way9Dexny3w"},
    note="Fetch OG metadata - expects title + site")

# 9. Create intent with URL (triggers server-side unfurl)
intent1 = req("POST /circles/:id/intents", "POST", f"/circles/{circle_id}/intents",
    expect=201,
    body={
        "title": "Dune: Part Two",
        "url":   "https://www.youtube.com/watch?v=Way9Dexny3w",
        "note":  "IMAX if possible",
        "category": "watch",
        "tags": ["film", "sci-fi"],
    },
    note="Creates intent + server-side unfurl of the URL")

intent1_id = intent1.get("id", "")
print(f"\n  {YEL}→ intent1_id = {intent1_id}{RST}")

# 10. Create a second intent (no URL)
intent2 = req("POST /circles/:id/intents (no URL)", "POST", f"/circles/{circle_id}/intents",
    expect=201,
    body={
        "title": "Busan Olle Korean BBQ",
        "category": "eat",
        "tags": ["korean", "dinner"],
    })

intent2_id = intent2.get("id", "")
print(f"\n  {YEL}→ intent2_id = {intent2_id}{RST}")

# 11. List intents (all)
req("GET /circles/:id/intents", "GET", f"/circles/{circle_id}/intents",
    note="Should return both intents")

# 12. List intents (filtered by category)
req("GET /circles/:id/intents?category=watch", "GET",
    f"/circles/{circle_id}/intents?category=watch",
    note="Should return only the film intent")

# 13. Update intent task_status
req("PATCH /intents/:id (task_status)", "PATCH", f"/intents/{intent1_id}",
    body={"task_status": "interested"},
    note="Move intent to 'interested' status")

# 14. React to intent (toggle interested)
req("POST /intents/:id/react", "POST", f"/intents/{intent1_id}/react",
    note="Toggle 'interested' reaction - should add it (reaction_count → 1)")

# 15. React again (toggle off)
req("POST /intents/:id/react (toggle off)", "POST", f"/intents/{intent1_id}/react",
    note="Second call removes the reaction (reaction_count → 0)")

# 16. React one more time (back on, for shortlist test)
req("POST /intents/:id/react (toggle back on)", "POST", f"/intents/{intent1_id}/react",
    note="Third call adds it back")

# 17. Boost an intent
req("POST /intents/:id/boost", "POST", f"/intents/{intent1_id}/boost",
    note="Add boost signal - affects smart-pick score")

# 18. Get intent detail
req("GET /intents/:id", "GET", f"/intents/{intent1_id}",
    note="Should show reaction_count=1, boosted_by_me=true")

# 19. Shortlist (needs ≥2 members - will be empty with 1 user, that's expected)
req("GET /circles/:id/intents?shortlist=true", "GET",
    f"/circles/{circle_id}/intents?shortlist=true",
    note="Shortlist requires ≥2 members interested - empty with 1 user is correct")

# 20. Smart pick (same constraint - will 404 with 1 user)
req("GET /circles/:id/payoff/smart", "GET",
    f"/circles/{circle_id}/payoff/smart", expect=404,
    note="Expected 404 with 1 user - needs ≥2 interested members")

# 21. Spin (same constraint)
req("GET /circles/:id/payoff/spin", "GET",
    f"/circles/{circle_id}/payoff/spin", expect=404,
    note="Expected 404 with 1 user - shortlist is empty")

# 22. Get invite link (circle detail has it)
circle_detail = req("GET /circles/:id (check invite_token)", "GET",
    f"/circles/{circle_id}",
    note="invite_token should be present for share link")

invite_token = circle_detail.get("invite_token", "")
print(f"\n  {YEL}→ invite_token = {invite_token}{RST}")
print(f"  {YEL}→ share link   = {BASE}/circles/join/{invite_token}{RST}")

# 23. Soft delete intent2
req("DELETE /intents/:id", "DELETE", f"/intents/{intent2_id}",
    note="Soft delete - sets status=0, never hard-deletes")

# 24. Verify intent2 gone from list
req("GET /circles/:id/intents (after delete)", "GET",
    f"/circles/{circle_id}/intents",
    note="Should only return intent1 now")

# ── Summary ───────────────────────────────────────────────────────────────────

passed = sum(1 for r in results if r["ok"])
failed = sum(1 for r in results if not r["ok"])
total  = len(results)

print(f"\n{'='*60}")
print(f"  RESULTS: {GRN}{passed} passed{RST}  {RED if failed else ''}{failed} failed{RST}  / {total} total")
print(f"{'='*60}")

if failed:
    print(f"\n{RED}Failed tests:{RST}")
    for r in results:
        if not r["ok"]:
            print(f"  ✗ {r['label']} → HTTP {r['status']}")

print()
