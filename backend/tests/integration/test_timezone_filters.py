"""Integration tests: timezone-aware date filtering.

Backend stores naive UTC in the DB.  normalize_to_utc converts:
  • Naive (no Z) → assumed Moscow (UTC+3) → UTC
  • Aware UTC (with Z / +00:00) → strip tzinfo → UTC

A frontend browser in ANY timezone sends UTC ISO strings (with Z).
This suite verifies that both representations of the same calendar instant
produce identical filter results, and that midnight-Moscow boundary cases
fall into the correct calendar month.

All occurred_at values below are in Moscow wall-clock time (naive); the API
normalises them to UTC before storage.  Filter parameters are expressed both
as naive Moscow strings AND as equivalent UTC-with-Z strings; both must
produce the same outcome.
"""

import pytest
from httpx import AsyncClient
from sqlmodel import Session

from app.models.account import Account

SUMMARY_URL = "/api/v1/transactions/expense-type-summary"
TRANSACTIONS_URL = "/api/v1/transactions"


def _tx(account_id: str, *, expense_type_id: str, occurred_at: str) -> dict[str, object]:
    return {
        "account_id": account_id,
        "occurred_at": occurred_at,
        "amount": -100.0,
        "type": "EXPENSE",
        "expense_type_id": expense_type_id,
    }


# ── Moscow midnight crosses the calendar-day boundary ─────────────────────────
#
# "2026-06-01T00:00:00" Moscow  =  "2026-05-31T21:00:00Z" UTC
#
# June filter (Moscow):  start=2026-06-01T00:00:00  end=2026-06-30T23:59:59
# June filter (UTC):     start=2026-05-31T21:00:00Z end=2026-06-30T20:59:59Z
# May filter (Moscow):   start=2026-05-01T00:00:00  end=2026-05-31T23:59:59
# May filter (UTC):      start=2026-04-30T21:00:00Z end=2026-05-31T20:59:59Z

@pytest.mark.parametrize("start_date,end_date,expected_in_result", [
    # UTC-aware June range  → INCLUDED
    ("2026-05-31T21:00:00Z",   "2026-06-30T20:59:59Z",   True),
    # Naive Moscow June range → INCLUDED (same instant, different format)
    ("2026-06-01T00:00:00",    "2026-06-30T23:59:59",     True),
    # UTC-aware May range   → EXCLUDED (transaction is in June Moscow-time)
    ("2026-04-30T21:00:00Z",   "2026-05-31T20:59:59Z",   False),
    # Naive Moscow May range → EXCLUDED
    ("2026-05-01T00:00:00",    "2026-05-31T23:59:59",     False),
])
@pytest.mark.asyncio
async def test_moscow_midnight_appears_in_june_not_may(
    client: AsyncClient,
    auth_headers: dict[str, str],
    test_account: Account,
    test_expense_type_id: str,
    start_date: str,
    end_date: str,
    expected_in_result: bool,
) -> None:
    """Transaction at Moscow midnight June 1 (= UTC 21:00 May 31) must appear in June, not May."""
    r = await client.post(
        TRANSACTIONS_URL,
        json=_tx(
            str(test_account.id),
            expense_type_id=test_expense_type_id,
            occurred_at="2026-06-01T00:00:00",  # Moscow midnight June 1
        ),
        headers=auth_headers,
    )
    assert r.status_code == 201

    resp = await client.get(
        SUMMARY_URL,
        params={"start_date": start_date, "end_date": end_date},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    expenses = resp.json()["expenses"]
    in_result = any(item["expense_type_id"] == test_expense_type_id for item in expenses)
    assert in_result == expected_in_result


# ── Last second of Moscow-May ─────────────────────────────────────────────────
#
# "2026-05-31T23:59:59" Moscow  =  "2026-05-31T20:59:59Z" UTC

@pytest.mark.parametrize("start_date,end_date,expected_in_result", [
    # UTC-aware May range, exact end boundary → INCLUDED
    ("2026-04-30T21:00:00Z",   "2026-05-31T20:59:59Z",   True),
    # Naive Moscow May range → INCLUDED
    ("2026-05-01T00:00:00",    "2026-05-31T23:59:59",     True),
    # UTC-aware June range (starts at Moscow midnight June 1) → EXCLUDED
    ("2026-05-31T21:00:00Z",   "2026-06-30T20:59:59Z",   False),
    # Naive Moscow June range → EXCLUDED
    ("2026-06-01T00:00:00",    "2026-06-30T23:59:59",     False),
])
@pytest.mark.asyncio
async def test_last_second_of_moscow_may_appears_in_may_not_june(
    client: AsyncClient,
    auth_headers: dict[str, str],
    test_account: Account,
    test_expense_type_id: str,
    start_date: str,
    end_date: str,
    expected_in_result: bool,
) -> None:
    """Transaction at 23:59:59 Moscow-May (= 20:59:59 UTC) must appear in May, not June."""
    r = await client.post(
        TRANSACTIONS_URL,
        json=_tx(
            str(test_account.id),
            expense_type_id=test_expense_type_id,
            occurred_at="2026-05-31T23:59:59",  # last second of Moscow-May
        ),
        headers=auth_headers,
    )
    assert r.status_code == 201

    resp = await client.get(
        SUMMARY_URL,
        params={"start_date": start_date, "end_date": end_date},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    expenses = resp.json()["expenses"]
    in_result = any(item["expense_type_id"] == test_expense_type_id for item in expenses)
    assert in_result == expected_in_result


# ── Naive Moscow filter == UTC-aware filter for the same instant ───────────────

@pytest.mark.parametrize("naive_start,utc_start,naive_end,utc_end", [
    # June 2026 expressed both ways
    (
        "2026-06-01T00:00:00", "2026-05-31T21:00:00Z",
        "2026-06-30T23:59:59", "2026-06-30T20:59:59Z",
    ),
    # January 2026 year boundary
    (
        "2026-01-01T00:00:00", "2025-12-31T21:00:00Z",
        "2026-01-31T23:59:59", "2026-01-31T20:59:59Z",
    ),
])
@pytest.mark.asyncio
async def test_naive_and_utc_aware_filters_are_equivalent(
    client: AsyncClient,
    auth_headers: dict[str, str],
    test_account: Account,
    test_expense_type_id: str,
    naive_start: str,
    utc_start: str,
    naive_end: str,
    utc_end: str,
) -> None:
    """Naive Moscow filter and its UTC-aware equivalent must return the same transaction count."""
    # Transaction in the middle of the range — always in both
    r = await client.post(
        TRANSACTIONS_URL,
        json=_tx(
            str(test_account.id),
            expense_type_id=test_expense_type_id,
            occurred_at=naive_start[:10] + "T12:00:00",  # noon of first day (Moscow)
        ),
        headers=auth_headers,
    )
    assert r.status_code == 201

    resp_naive = await client.get(
        SUMMARY_URL,
        params={"start_date": naive_start, "end_date": naive_end},
        headers=auth_headers,
    )
    resp_utc = await client.get(
        SUMMARY_URL,
        params={"start_date": utc_start, "end_date": utc_end},
        headers=auth_headers,
    )
    assert resp_naive.status_code == resp_utc.status_code == 200
    assert resp_naive.json()["expenses"] == resp_utc.json()["expenses"]
    assert resp_naive.json()["unmatched_count"] == resp_utc.json()["unmatched_count"]


# ── Year boundary: Moscow midnight Jan 1 ──────────────────────────────────────
#
# "2026-01-01T00:00:00" Moscow  =  "2025-12-31T21:00:00Z" UTC
#
# January 2026 range (Moscow): start=2026-01-01T00:00:00  end=2026-01-31T23:59:59
# January 2026 range (UTC):    start=2025-12-31T21:00:00Z end=2026-01-31T20:59:59Z
# December 2025 range (Moscow): start=2025-12-01T00:00:00  end=2025-12-31T23:59:59
# December 2025 range (UTC):    start=2025-11-30T21:00:00Z end=2025-12-31T20:59:59Z

@pytest.mark.parametrize("start_date,end_date,expected_in_result", [
    # UTC-aware January range → INCLUDED
    ("2025-12-31T21:00:00Z",  "2026-01-31T20:59:59Z",   True),
    # Naive Moscow January range → INCLUDED
    ("2026-01-01T00:00:00",   "2026-01-31T23:59:59",     True),
    # UTC-aware December range → EXCLUDED
    ("2025-11-30T21:00:00Z",  "2025-12-31T20:59:59Z",   False),
    # Naive Moscow December range → EXCLUDED
    ("2025-12-01T00:00:00",   "2025-12-31T23:59:59",     False),
])
@pytest.mark.asyncio
async def test_year_boundary_moscow_midnight_jan1(
    client: AsyncClient,
    auth_headers: dict[str, str],
    test_account: Account,
    test_expense_type_id: str,
    start_date: str,
    end_date: str,
    expected_in_result: bool,
) -> None:
    """Transaction at Moscow midnight Jan 1 (= UTC 21:00 Dec 31) must appear in Jan, not Dec."""
    r = await client.post(
        TRANSACTIONS_URL,
        json=_tx(
            str(test_account.id),
            expense_type_id=test_expense_type_id,
            occurred_at="2026-01-01T00:00:00",  # Moscow midnight Jan 1 2026
        ),
        headers=auth_headers,
    )
    assert r.status_code == 201

    resp = await client.get(
        SUMMARY_URL,
        params={"start_date": start_date, "end_date": end_date},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    expenses = resp.json()["expenses"]
    in_result = any(item["expense_type_id"] == test_expense_type_id for item in expenses)
    assert in_result == expected_in_result


# ── UTC-aware occurred_at (frontend sends Z-suffix) ───────────────────────────

@pytest.mark.asyncio
async def test_transaction_created_with_utc_aware_occurred_at(
    client: AsyncClient,
    auth_headers: dict[str, str],
    test_account: Account,
    test_expense_type_id: str,
) -> None:
    """Frontend can send UTC-aware occurred_at (with Z); backend normalises identically to naive Moscow."""
    # UTC midnight June 1 = Moscow 03:00 June 1 → same storage as naive "2026-06-01T03:00:00"
    r = await client.post(
        TRANSACTIONS_URL,
        json=_tx(
            str(test_account.id),
            expense_type_id=test_expense_type_id,
            occurred_at="2026-06-01T00:00:00Z",  # UTC midnight (NOT Moscow midnight)
        ),
        headers=auth_headers,
    )
    assert r.status_code == 201

    # UTC midnight June 1 = Moscow 03:00 June 1 → inside June both ways
    resp = await client.get(
        SUMMARY_URL,
        params={"start_date": "2026-05-31T21:00:00Z", "end_date": "2026-06-30T20:59:59Z"},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    expenses = resp.json()["expenses"]
    assert any(item["expense_type_id"] == test_expense_type_id for item in expenses)


# ── GET /transactions list endpoint uses the same date filters ─────────────────

@pytest.mark.parametrize("occurred_at_moscow,start_date,end_date,expect_tx", [
    # Moscow midnight June 1 — UTC-aware June filter includes it
    ("2026-06-01T00:00:00", "2026-05-31T21:00:00Z", "2026-06-30T20:59:59Z", True),
    # Moscow midnight June 1 — UTC-aware May filter excludes it
    ("2026-06-01T00:00:00", "2026-04-30T21:00:00Z", "2026-05-31T20:59:59Z", False),
])
@pytest.mark.asyncio
async def test_transactions_list_date_filter_timezone(
    client: AsyncClient,
    auth_headers: dict[str, str],
    test_account: Account,
    test_expense_type_id: str,
    occurred_at_moscow: str,
    start_date: str,
    end_date: str,
    expect_tx: bool,
) -> None:
    """GET /transactions date filters respect the same UTC normalization as the summary endpoint."""
    r = await client.post(
        TRANSACTIONS_URL,
        json=_tx(
            str(test_account.id),
            expense_type_id=test_expense_type_id,
            occurred_at=occurred_at_moscow,
        ),
        headers=auth_headers,
    )
    assert r.status_code == 201
    tx_id = r.json()["id"]

    resp = await client.get(
        TRANSACTIONS_URL,
        params={"start_date": start_date, "end_date": end_date},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    ids = [tx["id"] for tx in resp.json()]
    assert (tx_id in ids) == expect_tx
