"""drop tx counterparty_id, require expense_type_id

Revision ID: n5o6p7q8r9s0
Revises: m4n5o6p7q8r9
Create Date: 2026-06-03 00:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "n5o6p7q8r9s0"
down_revision: str | None = "m4n5o6p7q8r9"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("transactions") as batch_op:
        batch_op.drop_column("counterparty_id")

    # Make expense_type_id NOT NULL — delete orphan rows that have no expense type
    op.execute("DELETE FROM transactions WHERE expense_type_id IS NULL")
    with op.batch_alter_table("transactions") as batch_op:
        batch_op.alter_column(
            "expense_type_id",
            existing_type=sa.String(),
            nullable=False,
        )
        batch_op.create_index("ix_transactions_expense_type_id", ["expense_type_id"])


def downgrade() -> None:
    with op.batch_alter_table("transactions") as batch_op:
        batch_op.drop_index("ix_transactions_expense_type_id")
        batch_op.alter_column(
            "expense_type_id",
            existing_type=sa.String(),
            nullable=True,
        )
        batch_op.add_column(sa.Column("counterparty_id", sa.String(), nullable=True))
