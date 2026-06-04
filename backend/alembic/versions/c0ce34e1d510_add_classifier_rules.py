"""add_classifier_rules

Revision ID: c0ce34e1d510
Revises: o6p7q8r9s0t1
Create Date: 2026-06-04 21:31:38.853830

"""
from typing import Sequence, Union

import sqlalchemy as sa
import sqlmodel
from alembic import op

revision: str = "c0ce34e1d510"
down_revision: Union[str, None] = "o6p7q8r9s0t1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "classifier_rules",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("name", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("expense_type_id", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("priority", sa.Integer(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("representation", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("cond_account_id", sa.Uuid(), nullable=True),
        sa.Column("cond_day_month", sa.Integer(), nullable=True),
        sa.Column("cond_day_month_op", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column("cond_day_week", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column("cond_amount", sa.Numeric(precision=14, scale=2), nullable=True),
        sa.Column("cond_amount_op", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column("cond_type", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column("cond_bank_category", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column("cond_description", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.ForeignKeyConstraint(["expense_type_id"], ["expense_types.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_classifier_rules_user_id"), "classifier_rules", ["user_id"], unique=False
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_classifier_rules_user_id"), table_name="classifier_rules")
    op.drop_table("classifier_rules")
