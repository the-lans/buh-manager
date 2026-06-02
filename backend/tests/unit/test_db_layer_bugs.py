"""Regression tests for DB-layer bugs identified in code review."""

import pytest
from sqlmodel import Session, select

from app.db.counterparties import get_or_create_counterparty
from app.db.expense_types import create_expense_type, update_expense_type
from app.models.counterparty import Counterparty
from app.models.expense_type import ExpenseType
from app.models.user import User
from app.schemas.expense_type import ExpenseTypeCreate, ExpenseTypeUpdate
from app.utils.ids import scope_user_id


class _EmptyResult:
    """Session.exec() stub that returns no rows."""

    def first(self) -> None:
        return None


def _patch_exec_skip_first(
    *,
    session: Session,
    skip_calls: int,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Patch Session.exec() to return empty results for the first `skip_calls` invocations.

    Simulates the race-condition window where SELECT queries ran before a
    concurrent transaction committed its INSERT.
    """
    original_exec = session.__class__.exec
    call_count = 0

    def _mocked(self: Session, statement: object, **kwargs: object) -> object:
        nonlocal call_count
        call_count += 1
        if call_count <= skip_calls:
            return _EmptyResult()
        return original_exec(self, statement, **kwargs)

    monkeypatch.setattr(session.__class__, "exec", _mocked)


# ── Bug #1: expense_type DB functions must flush, not commit ──────────────────


def test_create_expense_type_is_rollback_safe(session: Session, test_user: User) -> None:
    data = ExpenseTypeCreate(id="travel", name="Travel", receipt_required=False)
    create_expense_type(session=session, user_id=test_user.id, data=data)

    session.rollback()

    scoped_id = scope_user_id(user_id=test_user.id, public_id="travel")
    result = session.exec(select(ExpenseType).where(ExpenseType.id == scoped_id)).first()
    assert result is None, "create_expense_type must not commit; data must be rollback-able"


def test_update_expense_type_is_rollback_safe(session: Session, test_user: User) -> None:
    scoped_id = scope_user_id(user_id=test_user.id, public_id="food")
    et = ExpenseType(id=scoped_id, user_id=test_user.id, name="Food", receipt_required=True)
    session.add(et)
    session.commit()

    update_expense_type(session=session, expense_type=et, data=ExpenseTypeUpdate(name="Updated"))
    session.rollback()

    session.expire_all()
    refreshed = session.get(ExpenseType, scoped_id)
    assert refreshed is not None
    assert (
        refreshed.name == "Food"
    ), "update_expense_type must not commit; change must be rollback-able"


# ── Bug #3: get_or_create_counterparty must recover from race IntegrityError ──

# skip_calls controls how many initial SELECT stubs to inject before INSERT:
#   3 — INN lookup + name lookup + while-loop check (inn present)
#   2 — name lookup + while-loop check (no INN)
_RACE_RECOVERY_CASES = [
    pytest.param("9998887770", 3, id="recovery-via-inn"),
    pytest.param(None, 2, id="recovery-via-name"),
]


@pytest.mark.parametrize(("inn", "skip_calls"), _RACE_RECOVERY_CASES)
def test_get_or_create_counterparty_recovers_from_race(
    session: Session,
    test_user: User,
    monkeypatch: pytest.MonkeyPatch,
    inn: str | None,
    skip_calls: int,
) -> None:
    """IntegrityError on concurrent INSERT must not propagate as 500.

    Simulates the race: both requests pass the initial SELECTs (mocked empty),
    then the losing request hits IntegrityError on INSERT and must recover by
    returning the record the winning request already committed.
    """
    scoped_id = scope_user_id(user_id=test_user.id, public_id="race-store")
    preexisting = Counterparty(
        id=scoped_id,
        user_id=test_user.id,
        name="Race Store",
        type="STORE",
        inn=inn,
    )
    session.add(preexisting)
    session.commit()

    _patch_exec_skip_first(session=session, skip_calls=skip_calls, monkeypatch=monkeypatch)

    result = get_or_create_counterparty(
        session=session,
        user_id=test_user.id,
        name="Race Store",
        inn=inn,
    )
    assert result.id == scoped_id
