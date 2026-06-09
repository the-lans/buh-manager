"""add zero_balance to accounts

Revision ID: p7q8r9s0t1u2
Revises: o6p7q8r9s0t1
Create Date: 2026-06-09 10:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy import inspect

from alembic import op

revision: str = "p7q8r9s0t1u2"
down_revision: str | None = "e995f32038a8"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_TABLE = "accounts"
_COLUMN = "zero_balance"


def upgrade() -> None:
    existing_columns = {c["name"] for c in inspect(op.get_bind()).get_columns(_TABLE)}
    if _COLUMN in existing_columns:
        return

    op.add_column(
        _TABLE,
        sa.Column(
            _COLUMN,
            sa.Numeric(14, 2),
            nullable=False,
            server_default="0",
        ),
    )


def downgrade() -> None:
    bind = op.get_bind()
    existing_columns = {c["name"] for c in inspect(bind).get_columns(_TABLE)}
    if _COLUMN not in existing_columns:
        return

    if bind.dialect.name == "sqlite":
        with op.batch_alter_table(_TABLE) as batch_op:
            batch_op.drop_column(_COLUMN)
    else:
        op.drop_column(_TABLE, _COLUMN)
