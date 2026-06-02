"""add description to expense_types

Revision ID: k2l3m4n5o6p7
Revises: b023617c4b7a
Create Date: 2026-06-02 12:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "k2l3m4n5o6p7"
down_revision: str | None = "i0j1k2l3m4n5"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("expense_types", sa.Column("description", sa.String(), nullable=True))


def downgrade() -> None:
    op.drop_column("expense_types", "description")
