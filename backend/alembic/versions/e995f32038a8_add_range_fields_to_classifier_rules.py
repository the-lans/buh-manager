"""add_range_fields_to_classifier_rules

Revision ID: e995f32038a8
Revises: c0ce34e1d510
Create Date: 2026-06-06 14:50:03.092886

"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy import inspect

from alembic import op

revision: str = "e995f32038a8"
down_revision: str | None = "c0ce34e1d510"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    existing = {c["name"] for c in inspect(op.get_bind()).get_columns("classifier_rules")}
    with op.batch_alter_table("classifier_rules") as batch_op:
        if "cond_day_month_to" not in existing:
            batch_op.add_column(sa.Column("cond_day_month_to", sa.Integer(), nullable=True))
        if "cond_amount_to" not in existing:
            batch_op.add_column(
                sa.Column("cond_amount_to", sa.Numeric(precision=14, scale=2), nullable=True)
            )


def downgrade() -> None:
    existing = {c["name"] for c in inspect(op.get_bind()).get_columns("classifier_rules")}
    with op.batch_alter_table("classifier_rules") as batch_op:
        if "cond_amount_to" in existing:
            batch_op.drop_column("cond_amount_to")
        if "cond_day_month_to" in existing:
            batch_op.drop_column("cond_day_month_to")
