#!/usr/bin/env python3
"""PRD acceptance smoke checks against a running API."""

from __future__ import annotations

import json
import sys
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import date, timedelta
from typing import Any

import httpx

BASE = "http://127.0.0.1:8000/api/v1"
PASSWORD = "Password123!"
TODAY = date.today()
CHECK_IN = (TODAY + timedelta(days=14)).isoformat()
CHECK_OUT = (TODAY + timedelta(days=16)).isoformat()
NEAR_IN = (TODAY + timedelta(days=1)).isoformat()
NEAR_OUT = (TODAY + timedelta(days=2)).isoformat()

results: list[tuple[str, str, str]] = []


def ok(cid: str, note: str = "") -> None:
    results.append((cid, "PASS", note))


def fail(cid: str, note: str) -> None:
    results.append((cid, "FAIL", note))


def skip(cid: str, note: str) -> None:
    results.append((cid, "SKIP", note))


def login(client: httpx.Client, email: str) -> str:
    r = client.post(f"{BASE}/auth/login", json={"email": email, "password": PASSWORD})
    r.raise_for_status()
    return r.json()["access_token"]


def auth_headers(token: str, **extra: str) -> dict[str, str]:
    headers = {"Authorization": f"Bearer {token}"}
    headers.update(extra)
    return headers


def main() -> int:
    with httpx.Client(timeout=30.0) as client:
        # AUTH
        bad1 = client.post(
            f"{BASE}/auth/login",
            json={"email": "nosuch@hbms.example", "password": PASSWORD},
        )
        bad2 = client.post(
            f"{BASE}/auth/login",
            json={"email": "customer@hbms.example", "password": "WrongPass123!"},
        )
        if bad1.status_code == 401 and bad2.status_code == 401 and bad1.json() == bad2.json():
            ok("AUTH-3", "generic failed-login error")
        else:
            fail("AUTH-3", f"{bad1.status_code}/{bad2.status_code} bodies differ or unexpected")

        tokens = {}
        for role, email in [
            ("customer", "customer@hbms.example"),
            ("receptionist", "receptionist@hbms.example"),
            ("org_admin", "org.admin@hbms.example"),
            ("product_admin", "product.admin@hbms.example"),
        ]:
            try:
                tokens[role] = login(client, email)
            except Exception as exc:  # noqa: BLE001
                fail("AUTH-3", f"login failed for {email}: {exc}")
                print_report()
                return 1

        me = client.get(f"{BASE}/auth/me", headers=auth_headers(tokens["customer"]))
        if me.status_code == 200 and me.json().get("role") == "CUSTOMER":
            ok("AUTH-4", "session carries role")
        else:
            fail("AUTH-4", me.text)

        # Customer hitting staff endpoint
        staff_hit = client.get(
            f"{BASE}/bookings/cancellation-requests",
            headers=auth_headers(tokens["customer"]),
        )
        # may also be list bookings staff filters; try organizations create
        org_create = client.post(
            f"{BASE}/organizations",
            headers=auth_headers(tokens["customer"]),
            json={"name": f"Hack Org {uuid.uuid4().hex[:6]}"},
        )
        if org_create.status_code == 403:
            ok("AUTH-5", "customer create org -> 403")
        else:
            fail("AUTH-5", f"expected 403 got {org_create.status_code}: {org_create.text}")

        # weak password register
        weak = client.post(
            f"{BASE}/auth/register",
            json={
                "name": "Weak User",
                "email": f"weak-{uuid.uuid4().hex[:8]}@example.com",
                "password": "short",
            },
        )
        if weak.status_code in {400, 422}:
            ok("AUTH-2", "password policy rejects weak password")
        else:
            fail("AUTH-2", f"expected validation fail got {weak.status_code}")

        # SEARCH
        search = client.get(
            f"{BASE}/search/rooms",
            params={"check_in": CHECK_IN, "check_out": CHECK_OUT, "guests": 2, "city": "Mumbai"},
            headers=auth_headers(tokens["customer"]),
        )
        if search.status_code != 200:
            fail("SEARCH-1", search.text)
            print_report()
            return 1
        rooms = search.json()
        if rooms and all(
            r.get("is_active")
            and r.get("availability_status") == "AVAILABLE"
            and r.get("capacity", 0) >= 2
            and r.get("hotel_name")
            for r in rooms
        ):
            ok("SEARCH-1", f"{len(rooms)} rooms; hotel_name present")
            ok("SEARCH-4", "listings include hotel + room attributes")
        else:
            fail("SEARCH-1/4", f"unexpected rooms payload: {json.dumps(rooms)[:400]}")

        past = client.get(
            f"{BASE}/search/rooms",
            params={
                "check_in": (TODAY - timedelta(days=2)).isoformat(),
                "check_out": (TODAY - timedelta(days=1)).isoformat(),
                "guests": 1,
            },
            headers=auth_headers(tokens["customer"]),
        )
        if past.status_code == 400:
            ok("SEARCH-2", "past check-in rejected")
        else:
            fail("SEARCH-2", f"got {past.status_code}")

        # optional filters
        filtered = client.get(
            f"{BASE}/search/rooms",
            params={"check_in": CHECK_IN, "check_out": CHECK_OUT, "guests": 1, "city": "Mumbai"},
            headers=auth_headers(tokens["customer"]),
        )
        if filtered.status_code == 200:
            ok("SEARCH-5", "city filter accepted")
        else:
            fail("SEARCH-5", filtered.text)

        if not rooms:
            fail("BOOK-*", "no rooms to book")
            print_report()
            return 1

        room = rooms[0]
        key = str(uuid.uuid4())
        booking_body = {
            "room_id": room["_id"],
            "check_in_date": CHECK_IN,
            "check_out_date": CHECK_OUT,
            "guest_count": 2,
        }
        b1 = client.post(
            f"{BASE}/bookings",
            headers=auth_headers(tokens["customer"], **{"Idempotency-Key": key}),
            json=booking_body,
        )
        b2 = client.post(
            f"{BASE}/bookings",
            headers=auth_headers(tokens["customer"], **{"Idempotency-Key": key}),
            json=booking_body,
        )
        if b1.status_code == 201 and b2.status_code in {200, 201} and b1.json()["_id"] == b2.json()["_id"]:
            ok("BOOK-6", "idempotency returns same booking")
        else:
            fail("BOOK-6", f"{b1.status_code}/{b2.status_code}")

        booking = b1.json()
        required = [
            "_id",
            "customer_id",
            "organization_id",
            "hotel_id",
            "room_id",
            "check_in_date",
            "check_out_date",
            "guest_count",
            "booking_date",
            "total_amount",
            "status",
            "booking_ref",
            "cancellation_deadline_at",
            "nightly_rate_snapshot",
        ]
        missing = [f for f in required if f not in booking]
        if not missing and booking["status"] == "CONFIRMED":
            ok("BOOK-1", "required booking fields present")
            ok("BOOK-8", booking["booking_ref"])
            ok("CANCEL-1", booking["cancellation_deadline_at"])
            ok("ORG-5", f"org={booking['organization_id']}")
        else:
            fail("BOOK-1", f"missing {missing}")

        # capacity validation
        over = client.post(
            f"{BASE}/bookings",
            headers=auth_headers(tokens["customer"], **{"Idempotency-Key": str(uuid.uuid4())}),
            json={**booking_body, "guest_count": 99, "check_in_date": (TODAY + timedelta(days=20)).isoformat(), "check_out_date": (TODAY + timedelta(days=21)).isoformat()},
        )
        if over.status_code in {400, 422}:
            ok("BOOK-3", "guest capacity enforced")
        else:
            fail("BOOK-3", f"got {over.status_code}: {over.text[:200]}")

        # overlap conflict with second customer-like attempt same dates same room
        # use same customer different key -> should 409
        conflict = client.post(
            f"{BASE}/bookings",
            headers=auth_headers(tokens["customer"], **{"Idempotency-Key": str(uuid.uuid4())}),
            json=booking_body,
        )
        if conflict.status_code == 409:
            ok("BOOK-4", "overlap -> 409")
        else:
            fail("BOOK-4", f"got {conflict.status_code}: {conflict.text[:200]}")

        # concurrent race on a different near-term room if available
        near_search = client.get(
            f"{BASE}/search/rooms",
            params={"check_in": NEAR_IN, "check_out": NEAR_OUT, "guests": 1},
            headers=auth_headers(tokens["customer"]),
        )
        near_rooms = near_search.json() if near_search.status_code == 200 else []
        if len(near_rooms) >= 1:
            race_room = near_rooms[0]["_id"]
            race_body = {
                "room_id": race_room,
                "check_in_date": NEAR_IN,
                "check_out_date": NEAR_OUT,
                "guest_count": 1,
            }

            def race_book(_: int) -> httpx.Response:
                return client.post(
                    f"{BASE}/bookings",
                    headers=auth_headers(tokens["customer"], **{"Idempotency-Key": str(uuid.uuid4())}),
                    json=race_body,
                )

            with ThreadPoolExecutor(max_workers=2) as pool:
                raced = list(pool.map(race_book, range(2)))
            codes = sorted(r.status_code for r in raced)
            if codes in ([201, 409], [409, 201]) or codes == [201, 201] and raced[0].json()["_id"] == raced[1].json()["_id"]:
                # 201+201 same id would be weird; prefer 201+409
                if codes == [201, 409]:
                    ok("BOOK-5", "concurrent -> one 201 one 409")
                else:
                    fail("BOOK-5", f"unexpected concurrent codes {codes}")
            elif codes == [201, 201]:
                fail("BOOK-5", "two confirmed bookings created")
            else:
                fail("BOOK-5", f"codes={codes} bodies={[r.text[:120] for r in raced]}")
        else:
            skip("BOOK-5", "no near-term room for race")

        # direct cancel before deadline (far booking)
        cancel = client.post(
            f"{BASE}/bookings/{booking['_id']}/cancel",
            headers=auth_headers(tokens["customer"]),
        )
        if cancel.status_code == 200 and cancel.json().get("status") == "CANCELLED":
            ok("CANCEL-3", "direct cancel before deadline")
            ok("CANCEL-6", "booking cancelled")
        else:
            fail("CANCEL-3", f"{cancel.status_code} {cancel.text[:200]}")

        # re-search should include room again
        again = client.get(
            f"{BASE}/search/rooms",
            params={"check_in": CHECK_IN, "check_out": CHECK_OUT, "guests": 2, "city": "Mumbai"},
            headers=auth_headers(tokens["customer"]),
        )
        if again.status_code == 200 and any(r["_id"] == room["_id"] for r in again.json()):
            ok("CANCEL-6b", "cancelled dates freed in search")
        else:
            fail("CANCEL-6b", "room still unavailable after cancel")

        # late cancellation request path: book near-term then try cancel / request
        if near_rooms:
            late_body = {
                "room_id": near_rooms[0]["_id"],
                "check_in_date": NEAR_IN,
                "check_out_date": NEAR_OUT,
                "guest_count": 1,
            }
            late = client.post(
                f"{BASE}/bookings",
                headers=auth_headers(tokens["customer"], **{"Idempotency-Key": str(uuid.uuid4())}),
                json=late_body,
            )
            if late.status_code == 201:
                late_id = late.json()["_id"]
                direct = client.post(
                    f"{BASE}/bookings/{late_id}/cancel",
                    headers=auth_headers(tokens["customer"]),
                )
                req = client.post(
                    f"{BASE}/bookings/{late_id}/cancellation-requests",
                    headers=auth_headers(tokens["customer"]),
                    json={"reason": "Plans changed within 24h window"},
                )
                if direct.status_code in {400, 403, 409} and req.status_code in {200, 201}:
                    ok("CANCEL-4", f"direct={direct.status_code} request={req.status_code}")
                    ok("CANCEL-5", "cancellation request entity created")
                elif direct.status_code == 200:
                    # near-in tomorrow might still be before end-of-day-before deadline
                    # deadline = end of day before check-in = TODAY 23:59:59, so TODAY can still cancel
                    skip("CANCEL-4", "near booking still within direct-cancel window (end-of-day-before rule)")
                else:
                    fail("CANCEL-4", f"direct={direct.status_code} req={req.status_code} {req.text[:160]}")
            else:
                skip("CANCEL-4", f"could not create late booking: {late.status_code}")

        # staff rooms
        orgs = client.get(f"{BASE}/organizations", headers=auth_headers(tokens["org_admin"]))
        if orgs.status_code == 200 and orgs.json():
            org_id = orgs.json()[0]["_id"]
            hotels = client.get(
                f"{BASE}/organizations/{org_id}/hotels",
                headers=auth_headers(tokens["org_admin"]),
            )
            if hotels.status_code == 200 and hotels.json():
                hotel_id = hotels.json()[0]["_id"]
                rooms_list = client.get(
                    f"{BASE}/hotels/{hotel_id}/rooms",
                    headers=auth_headers(tokens["org_admin"]),
                )
                if rooms_list.status_code == 200:
                    ok("ROOM-1", f"list rooms ({len(rooms_list.json())})")
                else:
                    fail("ROOM-1", rooms_list.text[:200])
                ok("ORG-2", "org admin lists hotels")
            else:
                fail("ORG-2", hotels.text[:200])
        else:
            fail("ORG-2", orgs.text[:200])

        # product admin create org
        new_org = client.post(
            f"{BASE}/organizations",
            headers=auth_headers(tokens["product_admin"]),
            json={"name": f"Smoke Org {uuid.uuid4().hex[:6]}"},
        )
        if new_org.status_code in {200, 201}:
            ok("ORG-1", "product admin created organization")
        else:
            fail("ORG-1", f"{new_org.status_code} {new_org.text[:200]}")

        # staff bookings dashboard
        staff_bookings = client.get(
            f"{BASE}/bookings",
            headers=auth_headers(tokens["receptionist"]),
        )
        if staff_bookings.status_code == 200:
            ok("DASH-3/4", f"receptionist bookings {len(staff_bookings.json())}")
        else:
            fail("DASH-3/4", staff_bookings.text[:200])

        customer_bookings = client.get(
            f"{BASE}/bookings",
            headers=auth_headers(tokens["customer"]),
        )
        if customer_bookings.status_code == 200:
            ok("DASH-1", f"customer bookings {len(customer_bookings.json())}")
        else:
            fail("DASH-1", customer_bookings.text[:200])

        # AUTH-7 rate limit - soft check
        limited = False
        for _ in range(25):
            r = client.post(
                f"{BASE}/auth/login",
                json={"email": "customer@hbms.example", "password": "nope"},
            )
            if r.status_code == 429:
                limited = True
                break
        if limited:
            ok("AUTH-7", "rate limited")
        else:
            fail("AUTH-7", "no 429 after 25 failed logins")

        # known gaps that need code inspection / not API-visible easily
        skip("AUTH-1", "case-insensitive uniqueness — verify via duplicate register if needed")
        skip("AUTH-6", "cross-user booking 404 — needs second customer")
        skip("HOTEL-1", "hotel create UI/API — exercise in browser if present")
        skip("HOTEL-2", "inactive hotel exclusion — needs inactive hotel seed")
        skip("ROOM-2", "unique room number — needs duplicate create")
        skip("ROOM-3", "is_active vs availability_status modeled — code review")
        skip("ROOM-4", "inactive room booking blocked — needs inactive room")
        skip("ROOM-5", "deactivate keeps bookings — needs setup")
        skip("ROOM-6", "decimal price + currency — schema level")
        skip("SEARCH-3", "half-open range — needs adjacent stays setup")
        skip("BOOK-2", "price snapshot — needs price change after book")
        skip("BOOK-7", "confirmation UI fields — browser")
        skip("CANCEL-2", "timezone end-of-day deadline — code review")
        skip("CANCEL-7", "staff cancel / double cancel — partial")
        skip("DASH-2", "COMPLETED job on startup — observed in logs")
        skip("DASH-5", "pagination — check API params")
        skip("ORG-3", "cross-org 404 — needs foreign ids")
        skip("ORG-4", "receptionist hotel isolation — needs multi-hotel")
        skip("ORG-6", "per-hotel room numbers — schema")
        skip("ORG-7", "schema supports multi-tenant — architecture")
        skip("ORG-8", "automated isolation suite — not present")

    print_report()
    fails = sum(1 for _, s, _ in results if s == "FAIL")
    return 1 if fails else 0


def print_report() -> None:
    print("\n=== PRD API SMOKE REPORT ===")
    for cid, status, note in results:
        print(f"{status:4}  {cid:12}  {note}")
    counts: dict[str, int] = {}
    for _, status, _ in results:
        counts[status] = counts.get(status, 0) + 1
    print("---")
    print(counts)


if __name__ == "__main__":
    sys.exit(main())
