"""add payload to counterparties and documents

Revision ID: j1k2l3m4n5o6
Revises: i0j1k2l3m4n5
Create Date: 2026-06-02 10:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "j1k2l3m4n5o6"
down_revision: str | None = "i0j1k2l3m4n5"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("counterparties", sa.Column("payload", sa.JSON(), nullable=True))
    op.add_column("documents", sa.Column("payload", sa.JSON(), nullable=True))


def downgrade() -> None:
    op.drop_column("documents", "payload")
    op.drop_column("counterparties", "payload")
