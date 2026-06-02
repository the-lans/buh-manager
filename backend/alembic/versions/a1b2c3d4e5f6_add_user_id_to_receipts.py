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
    op.add_column(
        "receipts",
        sa.Column("user_id", sa.Uuid(), nullable=True),
    )
    op.create_index("ix_receipts_user_id", "receipts", ["user_id"])
    # Note: SQLite does not support ALTER TABLE ADD CONSTRAINT via alembic,
    # so we skip the foreign key constraint here; it is defined at model level.


def downgrade() -> None:
    op.drop_index("ix_receipts_user_id", table_name="receipts")
    op.drop_column("receipts", "user_id")
