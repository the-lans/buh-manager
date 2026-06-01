"""make transaction receipt_id unique

Revision ID: g8h9i0j1k2l3
Revises: f7a8b9c0d1e2
Create Date: 2026-06-01 16:30:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "g8h9i0j1k2l3"
down_revision: str | None = "f7a8b9c0d1e2"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    duplicate_receipts = op.get_bind().execute(
        sa.text(
            """
            SELECT receipt_id, COUNT(*) AS duplicate_count
            FROM transactions
            WHERE receipt_id IS NOT NULL
            GROUP BY receipt_id
            HAVING COUNT(*) > 1
            """
        )
    ).fetchall()
    if duplicate_receipts:
        values = ", ".join(
            f"{row.receipt_id} ({row.duplicate_count})" for row in duplicate_receipts
        )
        raise RuntimeError(
            f"Cannot create unique transaction receipt_id index; duplicates exist: {values}"
        )

    op.create_index(
        "ix_transactions_receipt_id_unique",
        "transactions",
        ["receipt_id"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index("ix_transactions_receipt_id_unique", table_name="transactions")
