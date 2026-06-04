"""add per-user receipt fiscal uniqueness

Revision ID: o6p7q8r9s0t1
Revises: n5o6p7q8r9s0
Create Date: 2026-06-04 15:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "o6p7q8r9s0t1"
down_revision: str | None = "n5o6p7q8r9s0"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    duplicate_fiscal_rows = (
        op.get_bind()
        .execute(
            sa.text(
                """
                SELECT user_id, fn, fd, fpd, COUNT(*) AS duplicate_count
                FROM receipts
                WHERE user_id IS NOT NULL
                  AND fn IS NOT NULL
                  AND fd IS NOT NULL
                  AND fpd IS NOT NULL
                GROUP BY user_id, fn, fd, fpd
                HAVING COUNT(*) > 1
                """
            )
        )
        .fetchall()
    )
    if duplicate_fiscal_rows:
        values = ", ".join(
            f"{row.user_id}:{row.fn}/{row.fd}/{row.fpd} ({row.duplicate_count})"
            for row in duplicate_fiscal_rows
        )
        raise RuntimeError(
            "Cannot create per-user receipt fiscal uniqueness constraint; duplicates exist: "
            f"{values}"
        )

    if op.get_bind().dialect.name == "sqlite":
        with op.batch_alter_table("receipts", recreate="always") as batch_op:
            batch_op.create_unique_constraint(
                "uq_receipt_user_fiscal",
                ["user_id", "fn", "fd", "fpd"],
            )
    else:
        op.create_unique_constraint(
            "uq_receipt_user_fiscal",
            "receipts",
            ["user_id", "fn", "fd", "fpd"],
        )


def downgrade() -> None:
    if op.get_bind().dialect.name == "sqlite":
        with op.batch_alter_table("receipts", recreate="always") as batch_op:
            batch_op.drop_constraint("uq_receipt_user_fiscal", type_="unique")
    else:
        op.drop_constraint("uq_receipt_user_fiscal", "receipts", type_="unique")
