"""per-user file_hash uniqueness and sort indexes

Revision ID: h9i0j1k2l3m4
Revises: g8h9i0j1k2l3
Create Date: 2026-06-01 22:00:00.000000

Changes:
- documents.file_hash: drop global UNIQUE, add composite UNIQUE(file_hash, user_id)
  so two different users can upload the same file independently
- documents.uploaded_at: add index for ORDER BY performance
- receipts.paid_at: add index for ORDER BY performance
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "h9i0j1k2l3m4"
down_revision: str | None = "g8h9i0j1k2l3"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    bind = op.get_bind()
    dialect = bind.dialect.name

    if dialect == "sqlite":
        # SQLite cannot ALTER constraints; use batch mode to recreate the table
        with op.batch_alter_table("documents", recreate="always") as batch_op:
            # Remove the column-level unique on file_hash
            batch_op.alter_column(
                "file_hash",
                existing_type=sa.String(),
                existing_nullable=False,
                unique=False,
            )
            # Add composite unique
            batch_op.create_unique_constraint(
                "uq_document_file_hash_user", ["file_hash", "user_id"]
            )
            # Add index for ORDER BY uploaded_at DESC
            batch_op.create_index("ix_documents_uploaded_at", ["uploaded_at"])
    else:
        # PostgreSQL: drop named constraint, add new one
        op.drop_constraint("documents_file_hash_key", "documents", type_="unique")
        op.create_unique_constraint(
            "uq_document_file_hash_user", "documents", ["file_hash", "user_id"]
        )
        op.create_index("ix_documents_uploaded_at", "documents", ["uploaded_at"])

    # Add index on receipts.paid_at (same for all dialects)
    op.create_index("ix_receipts_paid_at", "receipts", ["paid_at"])


def downgrade() -> None:
    bind = op.get_bind()
    dialect = bind.dialect.name

    op.drop_index("ix_receipts_paid_at", table_name="receipts")

    if dialect == "sqlite":
        with op.batch_alter_table("documents", recreate="always") as batch_op:
            batch_op.drop_constraint("uq_document_file_hash_user", type_="unique")
            batch_op.drop_index("ix_documents_uploaded_at")
            batch_op.alter_column(
                "file_hash",
                existing_type=sa.String(),
                existing_nullable=False,
                unique=True,
            )
    else:
        op.drop_index("ix_documents_uploaded_at", table_name="documents")
        op.drop_constraint("uq_document_file_hash_user", "documents", type_="unique")
        op.create_unique_constraint("documents_file_hash_key", "documents", ["file_hash"])
