"""add app_constants table

Revision ID: q8r9s0t1u2v3
Revises: p7q8r9s0t1u2
Create Date: 2026-06-09 10:10:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy import inspect

from alembic import op

revision: str = "q8r9s0t1u2v3"
down_revision: str | None = "p7q8r9s0t1u2"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_TABLE = "app_constants"
_USER_ID_INDEX = "ix_app_constants_user_id"


def upgrade() -> None:
    inspector = inspect(op.get_bind())
    if _TABLE not in inspector.get_table_names():
        op.create_table(
            _TABLE,
            sa.Column("id", sa.Uuid(), nullable=False),
            sa.Column("user_id", sa.Uuid(), nullable=False),
            sa.Column("key", sa.String(), nullable=False),
            sa.Column("value", sa.String(), nullable=False),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("user_id", "key", name="uq_app_constant_user_key"),
        )

    existing_indexes = {idx["name"] for idx in inspect(op.get_bind()).get_indexes(_TABLE)}
    if _USER_ID_INDEX not in existing_indexes:
        op.create_index(_USER_ID_INDEX, _TABLE, ["user_id"], unique=False)


def downgrade() -> None:
    inspector = inspect(op.get_bind())
    if _TABLE not in inspector.get_table_names():
        return

    existing_indexes = {idx["name"] for idx in inspector.get_indexes(_TABLE)}
    if _USER_ID_INDEX in existing_indexes:
        op.drop_index(_USER_ID_INDEX, table_name=_TABLE)
    op.drop_table(_TABLE)
