"""make receipt document_id unique

Revision ID: i0j1k2l3m4n5
Revises: h9i0j1k2l3m4
Create Date: 2026-06-01 23:30:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "i0j1k2l3m4n5"
down_revision: str | None = "h9i0j1k2l3m4"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    duplicate_documents = (
        op.get_bind()
        .execute(
            sa.text(
                """
            SELECT document_id, COUNT(*) AS duplicate_count
            FROM receipts
            WHERE document_id IS NOT NULL
            GROUP BY document_id
            HAVING COUNT(*) > 1
            """
            )
        )
        .fetchall()
    )
    if duplicate_documents:
        values = ", ".join(
            f"{row.document_id} ({row.duplicate_count})" for row in duplicate_documents
        )
        raise RuntimeError(
            f"Cannot create unique receipt document_id constraint; duplicates exist: {values}"
        )

    if op.get_bind().dialect.name == "sqlite":
        with op.batch_alter_table("receipts", recreate="always") as batch_op:
            batch_op.create_unique_constraint("uq_receipt_document_id", ["document_id"])
    else:
        op.create_unique_constraint("uq_receipt_document_id", "receipts", ["document_id"])


def downgrade() -> None:
    if op.get_bind().dialect.name == "sqlite":
        with op.batch_alter_table("receipts", recreate="always") as batch_op:
            batch_op.drop_constraint("uq_receipt_document_id", type_="unique")
    else:
        op.drop_constraint("uq_receipt_document_id", "receipts", type_="unique")
