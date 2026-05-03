"""add user_id to receipts

Revision ID: a1b2c3d4e5f6
Revises: b023617c4b7a
Create Date: 2026-05-03 12:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


# revision identifiers, used by Alembic.
revision: str = "a1b2c3d4e5f6"
down_revision: Union[str, None] = "b023617c4b7a"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "receipts",
        sa.Column("user_id", sa.Uuid(), nullable=True),
    )
    op.create_index("ix_receipts_user_id", "receipts", ["user_id"])
    op.create_foreign_key(
        "fk_receipts_user_id",
        "receipts",
        "users",
        ["user_id"],
        ["id"],
    )


def downgrade() -> None:
    op.drop_constraint("fk_receipts_user_id", "receipts", type_="foreignkey")
    op.drop_index("ix_receipts_user_id", table_name="receipts")
    op.drop_column("receipts", "user_id")
