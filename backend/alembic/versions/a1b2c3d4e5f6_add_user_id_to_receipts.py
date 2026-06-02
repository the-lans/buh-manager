"""add user_id to receipts

Revision ID: a1b2c3d4e5f6
Revises: b023617c4b7a
Create Date: 2026-05-03 12:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a1b2c3d4e5f6"
down_revision: str | None = "b023617c4b7a"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_cols = {col["name"] for col in inspector.get_columns("receipts")}
    if "user_id" not in existing_cols:
        op.add_column("receipts", sa.Column("user_id", sa.Uuid(), nullable=True))
    existing_indexes = {idx["name"] for idx in inspector.get_indexes("receipts")}
    if "ix_receipts_user_id" not in existing_indexes:
        op.create_index("ix_receipts_user_id", "receipts", ["user_id"])
    # SQLite does not support ALTER TABLE ADD CONSTRAINT; skip for SQLite.


def downgrade() -> None:
    op.drop_index("ix_receipts_user_id", table_name="receipts")
    op.drop_column("receipts", "user_id")
