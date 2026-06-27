from decimal import Decimal
from uuid import UUID

import pytest
from httpx import AsyncClient
from sqlmodel import Session

from app.constants import ReconciledStatus, TransactionType
from app.models.account import Account
from app.models.expense_type import ExpenseType
from app.models.transaction import Transaction as TxModel
from app.models.user import User
from app.utils.ids import scope_user_id

SUMMARY_URL = "/api/v1/transactions/expense-type-summary"
TRANSACTIONS_URL = "/api/v1/transactions"


def _tx(
    account_id: str,
    *,
    amount: float,
    tx_type: str,
    expense_type_id: str,
    occurred_at: str = "2026-06-15T12:00:00",
) -> dict[str, str | float]:
    return {
        "account_id": account_id,
        "occurred_at": occurred_at,
        "amount": amount,
        "type": tx_type,
        "expense_type_id": expense_type_id,
    }


def _add_expense_type(
    session: Session,
    *,
    user_id: UUID,
    public_id: str,
    name: str = "Тест",
) -> str:
    scoped = scope_user_id(user_id=user_id, public_id=public_id)
    session.add(ExpenseType(id=scoped, user_id=user_id, name=name, receipt_required=False))
    session.commit()
    return public_id


# ── GET /transactions/expense-type-summary ────────────────────────────────────


@pytest.mark.asyncio
async def test_summary_returns_empty_when_no_transactions(
    client: AsyncClient,
    auth_headers: dict[str, str],
) -> None:
    resp = await client.get(SUMMARY_URL, headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["unmatched_count"] == 0
    assert data["expenses"] == []
    assert data["income"] == []
    assert data["turnover"] == []


@pytest.mark.asyncio
async def test_summary_aggregates_expense_and_income_separately(
    client: AsyncClient,
    auth_headers: dict[str, str],
    test_account: Account,
    test_expense_type_id: str,
) -> None:
    # Two EXPENSE transactions
    for amount in [-300.0, -200.0]:
        r = await client.post(
            TRANSACTIONS_URL,
            json=_tx(str(test_account.id), amount=amount, tx_type="EXPENSE", expense_type_id=test_expense_type_id),
            headers=auth_headers,
        )
        assert r.status_code == 201

    # One INCOME transaction
    r = await client.post(
        TRANSACTIONS_URL,
        json=_tx(str(test_account.id), amount=1000.0, tx_type="INCOME", expense_type_id=test_expense_type_id),
        headers=auth_headers,
    )
    assert r.status_code == 201

    resp = await client.get(SUMMARY_URL, headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()

    assert len(data["expenses"]) == 1
    assert data["expenses"][0]["expense_type_id"] == test_expense_type_id
    assert data["expenses"][0]["count"] == 2
    assert Decimal(data["expenses"][0]["total"]) == Decimal("-500")

    assert len(data["income"]) == 1
    assert data["income"][0]["expense_type_id"] == test_expense_type_id
    assert data["income"][0]["count"] == 1
    assert Decimal(data["income"][0]["total"]) == Decimal("1000")

    assert len(data["turnover"]) == 1
    assert data["turnover"][0]["count"] == 3
    assert Decimal(data["turnover"][0]["total"]) == Decimal("500")  # -300 - 200 + 1000


@pytest.mark.asyncio
async def test_summary_groups_by_expense_type_id(
    client: AsyncClient,
    auth_headers: dict[str, str],
    test_account: Account,
    test_expense_type_id: str,
    session: Session,
    test_user: User,
) -> None:
    second_et = _add_expense_type(session, user_id=test_user.id, public_id="transport", name="Транспорт")

    for et_id, amount in [(test_expense_type_id, -100.0), (second_et, -200.0)]:
        r = await client.post(
            TRANSACTIONS_URL,
            json=_tx(str(test_account.id), amount=amount, tx_type="EXPENSE", expense_type_id=et_id),
            headers=auth_headers,
        )
        assert r.status_code == 201

    resp = await client.get(SUMMARY_URL, headers=auth_headers)
    data = resp.json()

    et_ids = {row["expense_type_id"] for row in data["expenses"]}
    assert et_ids == {test_expense_type_id, second_et}
    totals = {row["expense_type_id"]: Decimal(row["total"]) for row in data["expenses"]}
    assert totals[test_expense_type_id] == Decimal("-100")
    assert totals[second_et] == Decimal("-200")


@pytest.mark.parametrize(
    "occurred_at, in_range",
    [
        ("2026-06-15T12:00:00", True),   # mid-June — inside
        ("2026-05-01T12:00:00", False),  # May — before range
        ("2026-07-01T12:00:00", False),  # July — after range
    ],
)
@pytest.mark.asyncio
async def test_summary_date_range_filter(
    client: AsyncClient,
    auth_headers: dict[str, str],
    test_account: Account,
    test_expense_type_id: str,
    occurred_at: str,
    in_range: bool,
) -> None:
    r = await client.post(
        TRANSACTIONS_URL,
        json=_tx(str(test_account.id), amount=-500.0, tx_type="EXPENSE", expense_type_id=test_expense_type_id, occurred_at=occurred_at),
        headers=auth_headers,
    )
    assert r.status_code == 201

    resp = await client.get(
        SUMMARY_URL,
        params={"start_date": "2026-06-01T00:00:00", "end_date": "2026-06-30T23:59:59"},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.json()

    if in_range:
        assert len(data["expenses"]) == 1
        assert data["expenses"][0]["count"] == 1
    else:
        assert data["expenses"] == []


@pytest.mark.asyncio
async def test_summary_unmatched_count_reflects_all_unmatched_in_range(
    client: AsyncClient,
    auth_headers: dict[str, str],
    test_account: Account,
    test_expense_type_id: str,
) -> None:
    # 2 transactions in June (start as UNMATCHED)
    for _ in range(2):
        r = await client.post(
            TRANSACTIONS_URL,
            json=_tx(str(test_account.id), amount=-100.0, tx_type="EXPENSE", expense_type_id=test_expense_type_id),
            headers=auth_headers,
        )
        assert r.status_code == 201

    # 1 transaction in May (outside June range)
    r = await client.post(
        TRANSACTIONS_URL,
        json=_tx(str(test_account.id), amount=-100.0, tx_type="EXPENSE", expense_type_id=test_expense_type_id, occurred_at="2026-05-15T12:00:00"),
        headers=auth_headers,
    )
    assert r.status_code == 201

    resp = await client.get(
        SUMMARY_URL,
        params={"start_date": "2026-06-01T00:00:00", "end_date": "2026-06-30T23:59:59"},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["unmatched_count"] == 2


@pytest.mark.asyncio
async def test_summary_only_shows_expense_types_with_transactions(
    client: AsyncClient,
    auth_headers: dict[str, str],
    test_account: Account,
    test_expense_type_id: str,
    session: Session,
    test_user: User,
) -> None:
    """Expense types that exist in the DB but have no transactions do not appear in the summary."""
    # Create a second expense type with NO transactions
    _add_expense_type(session, user_id=test_user.id, public_id="empty-et", name="Без транзакций")

    # Only first expense type has a transaction
    r = await client.post(
        TRANSACTIONS_URL,
        json=_tx(str(test_account.id), amount=-100.0, tx_type="EXPENSE", expense_type_id=test_expense_type_id),
        headers=auth_headers,
    )
    assert r.status_code == 201

    resp = await client.get(SUMMARY_URL, headers=auth_headers)
    data = resp.json()

    et_ids = {row["expense_type_id"] for row in data["expenses"]}
    assert test_expense_type_id in et_ids
    assert "empty-et" not in et_ids  # no transactions → not in summary


@pytest.mark.asyncio
async def test_summary_user_isolation(
    client: AsyncClient,
    auth_headers: dict[str, str],
    second_auth_headers: dict[str, str],
    test_account: Account,
    test_expense_type_id: str,
) -> None:
    r = await client.post(
        TRANSACTIONS_URL,
        json=_tx(str(test_account.id), amount=-100.0, tx_type="EXPENSE", expense_type_id=test_expense_type_id),
        headers=auth_headers,
    )
    assert r.status_code == 201

    # Second user should see empty summary
    resp = await client.get(SUMMARY_URL, headers=second_auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["expenses"] == []
    assert data["unmatched_count"] == 0


@pytest.mark.asyncio
async def test_summary_requires_authentication(
    client: AsyncClient,
) -> None:
    resp = await client.get(SUMMARY_URL)
    assert resp.status_code == 401


@pytest.mark.parametrize(
    "bad_param",
    [
        {"start_date": "not-a-date"},
        {"end_date": "31-06-2026"},
        {"start_date": "2026/06/01"},
    ],
)
@pytest.mark.asyncio
async def test_summary_invalid_date_format_returns_422(
    client: AsyncClient,
    auth_headers: dict[str, str],
    bad_param: dict[str, str],
) -> None:
    """Malformed date parameters must be rejected with 422 Unprocessable Entity."""
    resp = await client.get(SUMMARY_URL, params=bad_param, headers=auth_headers)
    assert resp.status_code == 422


# ── Corner cases ─────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_summary_transfer_appears_in_turnover_only(
    client: AsyncClient,
    auth_headers: dict[str, str],
    test_account: Account,
    test_expense_type_id: str,
) -> None:
    """TRANSFER transactions must appear in turnover but not in expenses or income."""
    r = await client.post(
        TRANSACTIONS_URL,
        json=_tx(
            str(test_account.id),
            amount=500.0,
            tx_type=TransactionType.TRANSFER,
            expense_type_id=test_expense_type_id,
        ),
        headers=auth_headers,
    )
    assert r.status_code == 201

    resp = await client.get(SUMMARY_URL, headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()

    assert data["expenses"] == []
    assert data["income"] == []
    assert len(data["turnover"]) == 1
    assert data["turnover"][0]["count"] == 1
    assert Decimal(data["turnover"][0]["total"]) == Decimal("500")


@pytest.mark.asyncio
async def test_summary_turnover_is_superset_of_all_types(
    client: AsyncClient,
    auth_headers: dict[str, str],
    test_account: Account,
    test_expense_type_id: str,
) -> None:
    """turnover.count == sum of counts across expenses + income + transfer for the same expense_type."""
    for tx_type, amount in [
        (TransactionType.EXPENSE, -300.0),
        (TransactionType.INCOME, 500.0),
        (TransactionType.TRANSFER, 200.0),
    ]:
        r = await client.post(
            TRANSACTIONS_URL,
            json=_tx(str(test_account.id), amount=amount, tx_type=tx_type, expense_type_id=test_expense_type_id),
            headers=auth_headers,
        )
        assert r.status_code == 201

    resp = await client.get(SUMMARY_URL, headers=auth_headers)
    data = resp.json()

    assert data["expenses"][0]["count"] == 1
    assert data["income"][0]["count"] == 1
    assert data["turnover"][0]["count"] == 3
    assert Decimal(data["turnover"][0]["total"]) == Decimal("-300") + Decimal("500") + Decimal("200")


@pytest.mark.parametrize(
    "params, expected_expense_count",
    [
        ({"start_date": "2026-06-01T00:00:00"}, 1),  # open end: only June tx included
        ({"end_date": "2026-05-31T23:59:59"}, 1),    # open start: only May tx included
    ],
)
@pytest.mark.asyncio
async def test_summary_one_sided_date_range(
    client: AsyncClient,
    auth_headers: dict[str, str],
    test_account: Account,
    test_expense_type_id: str,
    params: dict[str, str],
    expected_expense_count: int,
) -> None:
    """A range with only start_date or only end_date is treated as open-ended."""
    for occurred_at in ("2026-05-15T12:00:00", "2026-06-15T12:00:00"):
        r = await client.post(
            TRANSACTIONS_URL,
            json=_tx(
                str(test_account.id),
                amount=-100.0,
                tx_type=TransactionType.EXPENSE,
                expense_type_id=test_expense_type_id,
                occurred_at=occurred_at,
            ),
            headers=auth_headers,
        )
        assert r.status_code == 201

    resp = await client.get(SUMMARY_URL, params=params, headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()

    total_tx_count = sum(row["count"] for row in data["expenses"])
    assert total_tx_count == expected_expense_count


@pytest.mark.parametrize(
    "bad_status",
    [ReconciledStatus.MATCHED, ReconciledStatus.IGNORED_BY_USER],
)
@pytest.mark.asyncio
async def test_summary_unmatched_count_excludes_non_unmatched_status(
    client: AsyncClient,
    auth_headers: dict[str, str],
    test_account: Account,
    test_expense_type_id: str,
    session: Session,
    bad_status: ReconciledStatus,
) -> None:
    """Transactions with MATCHED or IGNORED_BY_USER status must not be counted in unmatched_count."""
    r = await client.post(
        TRANSACTIONS_URL,
        json=_tx(str(test_account.id), amount=-100.0, tx_type=TransactionType.EXPENSE, expense_type_id=test_expense_type_id),
        headers=auth_headers,
    )
    assert r.status_code == 201
    tx_id = r.json()["id"]

    session.expire_all()
    tx = session.get(TxModel, UUID(tx_id))
    assert tx is not None
    tx.reconciled_status = bad_status
    session.add(tx)
    session.commit()

    resp = await client.get(SUMMARY_URL, headers=auth_headers)
    assert resp.json()["unmatched_count"] == 0


@pytest.mark.asyncio
async def test_summary_unmatched_count_with_mixed_statuses(
    client: AsyncClient,
    auth_headers: dict[str, str],
    test_account: Account,
    test_expense_type_id: str,
    session: Session,
) -> None:
    """Only UNMATCHED transactions contribute to unmatched_count."""
    created_ids: list[str] = []
    for _ in range(3):
        r = await client.post(
            TRANSACTIONS_URL,
            json=_tx(str(test_account.id), amount=-100.0, tx_type=TransactionType.EXPENSE, expense_type_id=test_expense_type_id),
            headers=auth_headers,
        )
        assert r.status_code == 201
        created_ids.append(r.json()["id"])

    # Mark first as MATCHED, second as IGNORED_BY_USER; third stays UNMATCHED
    session.expire_all()
    for tx_id, status in zip(
        created_ids[:2],
        [ReconciledStatus.MATCHED, ReconciledStatus.IGNORED_BY_USER],
        strict=True,
    ):
        tx = session.get(TxModel, UUID(tx_id))
        assert tx is not None
        tx.reconciled_status = status
        session.add(tx)
    session.commit()

    resp = await client.get(SUMMARY_URL, headers=auth_headers)
    assert resp.json()["unmatched_count"] == 1


@pytest.mark.asyncio
async def test_summary_decimal_precision(
    client: AsyncClient,
    auth_headers: dict[str, str],
    test_account: Account,
    test_expense_type_id: str,
) -> None:
    """Fractional amounts must be summed without floating-point precision loss."""
    amounts = ["-100.01", "-200.02", "-50.03"]
    for amount in amounts:
        r = await client.post(
            TRANSACTIONS_URL,
            json={
                "account_id": str(test_account.id),
                "occurred_at": "2026-06-15T12:00:00",
                "amount": amount,
                "type": TransactionType.EXPENSE,
                "expense_type_id": test_expense_type_id,
            },
            headers=auth_headers,
        )
        assert r.status_code == 201

    resp = await client.get(SUMMARY_URL, headers=auth_headers)
    data = resp.json()

    expected = sum(Decimal(a) for a in amounts)
    assert Decimal(data["expenses"][0]["total"]) == expected
    assert data["expenses"][0]["count"] == len(amounts)


@pytest.mark.parametrize(
    "tx_type, amount, section",
    [
        (TransactionType.EXPENSE, -100.0, "expenses"),
        (TransactionType.INCOME, 100.0, "income"),
        (TransactionType.TRANSFER, 100.0, "turnover"),
    ],
)
@pytest.mark.asyncio
async def test_summary_expense_type_id_returned_as_public_id(
    client: AsyncClient,
    auth_headers: dict[str, str],
    test_account: Account,
    test_expense_type_id: str,
    tx_type: str,
    amount: float,
    section: str,
) -> None:
    """All response sections must use the unscoped public ID, not the internal 'user_id:slug' form."""
    r = await client.post(
        TRANSACTIONS_URL,
        json=_tx(str(test_account.id), amount=amount, tx_type=tx_type, expense_type_id=test_expense_type_id),
        headers=auth_headers,
    )
    assert r.status_code == 201

    resp = await client.get(SUMMARY_URL, headers=auth_headers)
    data = resp.json()

    rows = data[section]
    assert len(rows) == 1
    returned_id = rows[0]["expense_type_id"]
    assert returned_id == test_expense_type_id
    assert ":" not in returned_id  # internal scoped form is 'user_id:slug'


# ── GET /transactions?expense_type_id= ───────────────────────────────────────


@pytest.mark.asyncio
async def test_list_transactions_filter_by_expense_type_id(
    client: AsyncClient,
    auth_headers: dict[str, str],
    test_account: Account,
    test_expense_type_id: str,
    session: Session,
    test_user: User,
) -> None:
    second_et = _add_expense_type(session, user_id=test_user.id, public_id="transport", name="Транспорт")

    r1 = await client.post(
        TRANSACTIONS_URL,
        json=_tx(str(test_account.id), amount=-100.0, tx_type="EXPENSE", expense_type_id=test_expense_type_id),
        headers=auth_headers,
    )
    assert r1.status_code == 201

    r2 = await client.post(
        TRANSACTIONS_URL,
        json=_tx(str(test_account.id), amount=-200.0, tx_type="EXPENSE", expense_type_id=second_et),
        headers=auth_headers,
    )
    assert r2.status_code == 201

    resp = await client.get(
        TRANSACTIONS_URL,
        params={"expense_type_id": test_expense_type_id},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    txs = resp.json()
    assert len(txs) == 1
    assert txs[0]["expense_type_id"] == test_expense_type_id
    assert float(txs[0]["amount"]) == -100.0


@pytest.mark.parametrize(
    "filter_type, expected_amount",
    [
        (TransactionType.EXPENSE, -100.0),
        (TransactionType.INCOME, 200.0),
    ],
)
@pytest.mark.asyncio
async def test_list_transactions_expense_type_combined_with_type_filter(
    client: AsyncClient,
    auth_headers: dict[str, str],
    test_account: Account,
    test_expense_type_id: str,
    filter_type: str,
    expected_amount: float,
) -> None:
    """Combining expense_type_id and type filters narrows down to the matching subset only."""
    for tx_type, amount in [
        (TransactionType.EXPENSE, -100.0),
        (TransactionType.INCOME, 200.0),
    ]:
        r = await client.post(
            TRANSACTIONS_URL,
            json=_tx(
                str(test_account.id),
                amount=amount,
                tx_type=tx_type,
                expense_type_id=test_expense_type_id,
            ),
            headers=auth_headers,
        )
        assert r.status_code == 201

    resp = await client.get(
        TRANSACTIONS_URL,
        params={"expense_type_id": test_expense_type_id, "type": filter_type},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    txs = resp.json()
    assert len(txs) == 1
    assert txs[0]["type"] == filter_type
    assert float(txs[0]["amount"]) == expected_amount


@pytest.mark.asyncio
async def test_list_transactions_unknown_expense_type_returns_empty(
    client: AsyncClient,
    auth_headers: dict[str, str],
    test_account: Account,
    test_expense_type_id: str,
) -> None:
    r = await client.post(
        TRANSACTIONS_URL,
        json=_tx(str(test_account.id), amount=-100.0, tx_type="EXPENSE", expense_type_id=test_expense_type_id),
        headers=auth_headers,
    )
    assert r.status_code == 201

    resp = await client.get(
        TRANSACTIONS_URL,
        params={"expense_type_id": "nonexistent-type"},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    assert resp.json() == []
