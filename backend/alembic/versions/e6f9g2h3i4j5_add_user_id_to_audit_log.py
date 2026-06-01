"""add user_id to audit_log

Revision ID: e6f9g2h3i4j5
Revises: d5e8f1a2b3c4
Create Date: 2026-06-01 12:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "e6f9g2h3i4j5"
down_revision: str | None = "d5e8f1a2b3c4"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("audit_log", sa.Column("user_id", sa.Uuid(), nullable=True))
    op.create_index("ix_audit_log_user_id", "audit_log", ["user_id"])
    op.create_foreign_key(
        "fk_audit_log_user_id",
        "audit_log",
        "users",
        ["user_id"],
        ["id"],
    )


def downgrade() -> None:
    op.drop_constraint("fk_audit_log_user_id", "audit_log", type_="foreignkey")
    op.drop_index("ix_audit_log_user_id", table_name="audit_log")
    op.drop_column("audit_log", "user_id")
