"""Regression tests for DB-layer bugs found during code review."""
from uuid import UUID

import pytest
from sqlmodel import Session, select

from app.db.counterparties import get_or_create_counterparty
from app.db.expense_types import create_expense_type
from app.models.counterparty import Counterparty
from app.models.expense_type import ExpenseType
from app.models.user import User
from app.schemas.expense_type import ExpenseTypeCreate
from app.utils.ids import scope_user_id


class TestExpenseTypeFlushNotCommit:
    """Bug #1 regression: create_expense_type must flush, not commit."""

    def test_create_expense_type_is_rollback_safe(self, session: Session, test_user: User) -> None:
        """create_expense_type must not commit; caller must be able to roll back."""
        data = ExpenseTypeCreate(id="travel", name="Travel", receipt_required=False)
        create_expense_type(session=session, user_id=test_user.id, data=data)

        session.rollback()

        scoped_id = scope_user_id(user_id=test_user.id, public_id="travel")
        result = session.exec(select(ExpenseType).where(ExpenseType.id == scoped_id)).first()
        assert result is None, "expense type must not survive a rollback (premature commit bug)"

    def test_update_expense_type_is_rollback_safe(self, session: Session, test_user: User) -> None:
        """update_expense_type must not commit; caller must be able to roll back."""
        from app.db.expense_types import update_expense_type
        from app.schemas.expense_type import ExpenseTypeUpdate

        scoped_id = scope_user_id(user_id=test_user.id, public_id="food")
        et = ExpenseType(id=scoped_id, user_id=test_user.id, name="Food", receipt_required=True)
        session.add(et)
        session.commit()

        update_expense_type(session=session, expense_type=et, data=ExpenseTypeUpdate(name="Updated"))
        session.rollback()

        session.expire_all()
        refreshed = session.get(ExpenseType, scoped_id)
        assert refreshed is not None
        assert refreshed.name == "Food", "name change must not survive rollback (premature commit bug)"


class TestGetOrCreateCounterpartyRaceCondition:
    """Bug #3 regression: IntegrityError on concurrent insert must not produce 500."""

    def test_recovers_from_integrity_error_via_inn(
        self,
        session: Session,
        test_user: User,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Simulate race: both requests pass the initial SELECTs, then second fails on INSERT."""
        scoped_id = scope_user_id(user_id=test_user.id, public_id="raced-store")
        preexisting = Counterparty(
            id=scoped_id,
            user_id=test_user.id,
            name="Raced Store",
            type="STORE",
            inn="9998887770",
        )
        session.add(preexisting)
        session.commit()

        # Mock the first 3 exec() calls (INN lookup, name lookup, while-loop ID check)
        # to return nothing — simulating the window before the concurrent request committed.
        original_exec = session.__class__.exec
        call_count = 0

        def mocked_exec(self: Session, statement: object, **kwargs: object) -> object:
            nonlocal call_count
            call_count += 1
            if call_count <= 3:

                class _Empty:
                    def first(self) -> None:
                        return None

                return _Empty()
            return original_exec(self, statement, **kwargs)

        monkeypatch.setattr(session.__class__, "exec", mocked_exec)

        # get_or_create will try to INSERT, hit IntegrityError, then recover via INN lookup.
        result = get_or_create_counterparty(
            session=session,
            user_id=test_user.id,
            name="Raced Store",
            inn="9998887770",
        )
        assert result.id == scoped_id

    def test_recovers_from_integrity_error_via_name(
        self,
        session: Session,
        test_user: User,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Same race condition, but counterparty has no INN — recovery via name lookup."""
        scoped_id = scope_user_id(user_id=test_user.id, public_id="no-inn-store")
        preexisting = Counterparty(
            id=scoped_id,
            user_id=test_user.id,
            name="No INN Store",
            type="STORE",
            inn=None,
        )
        session.add(preexisting)
        session.commit()

        original_exec = session.__class__.exec
        call_count = 0

        def mocked_exec(self: Session, statement: object, **kwargs: object) -> object:
            nonlocal call_count
            call_count += 1
            if call_count <= 2:

                class _Empty:
                    def first(self) -> None:
                        return None

                return _Empty()
            return original_exec(self, statement, **kwargs)

        monkeypatch.setattr(session.__class__, "exec", mocked_exec)

        result = get_or_create_counterparty(
            session=session,
            user_id=test_user.id,
            name="No INN Store",
        )
        assert result.id == scoped_id
