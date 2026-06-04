"""rescope legacy reference IDs missed by initial scoping migration

Revision ID: o6p7q8r9s0t1
Revises: n5o6p7q8r9s0
Branch Labels: None
Depends On: None

Some expense_types and counterparties may have been created or imported before
the scoping migration (l3m4n5o6p7q8) ran, leaving their IDs without the
"{user_id}:" prefix. This migration finds any such rows and scopes them,
updating FK references in dependent tables.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "o6p7q8r9s0t1"
down_revision: str | None = "n5o6p7q8r9s0"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    bind = op.get_bind()

    op.execute(sa.text("PRAGMA foreign_keys=OFF"))

    # ── Expense types ────────────────────────────────────────────────────────
    expense_types = bind.execute(
        sa.text("SELECT id, user_id FROM expense_types WHERE id NOT LIKE '%:%'")
    ).fetchall()

    for row in expense_types:
        old_id = row.id
        new_id = f"{row.user_id}:{old_id}"
        bind.execute(
            sa.text(
                "UPDATE transactions SET expense_type_id = :new_id "
                "WHERE expense_type_id = :old_id"
            ),
            {"new_id": new_id, "old_id": old_id},
        )
        bind.execute(
            sa.text("UPDATE expense_types SET id = :new_id WHERE id = :old_id"),
            {"new_id": new_id, "old_id": old_id},
        )

    # ── Counterparties ───────────────────────────────────────────────────────
    counterparties = bind.execute(
        sa.text("SELECT id, user_id FROM counterparties WHERE id NOT LIKE '%:%'")
    ).fetchall()

    for row in counterparties:
        old_id = row.id
        new_id = f"{row.user_id}:{old_id}"
        bind.execute(
            sa.text(
                "UPDATE receipts SET counterparty_id = :new_id "
                "WHERE counterparty_id = :old_id"
            ),
            {"new_id": new_id, "old_id": old_id},
        )
        bind.execute(
            sa.text("UPDATE counterparties SET id = :new_id WHERE id = :old_id"),
            {"new_id": new_id, "old_id": old_id},
        )

    op.execute(sa.text("PRAGMA foreign_keys=ON"))


def downgrade() -> None:
    # Intentionally no-op: unscoping would require knowing the original format
    # and could violate uniqueness constraints on old data.
    pass
