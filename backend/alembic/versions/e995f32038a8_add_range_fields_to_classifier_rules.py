"""add_range_fields_to_classifier_rules

Revision ID: e995f32038a8
Revises: c0ce34e1d510
Create Date: 2026-06-06 14:50:03.092886

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "e995f32038a8"
down_revision: Union[str, None] = "c0ce34e1d510"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("classifier_rules") as batch_op:
        batch_op.add_column(sa.Column("cond_day_month_to", sa.Integer(), nullable=True))
        batch_op.add_column(
            sa.Column("cond_amount_to", sa.Numeric(precision=14, scale=2), nullable=True)
        )


def downgrade() -> None:
    with op.batch_alter_table("classifier_rules") as batch_op:
        batch_op.drop_column("cond_amount_to")
        batch_op.drop_column("cond_day_month_to")
