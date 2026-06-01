"""add inn and kpp to counterparties

Revision ID: d5e8f1a2b3c4
Revises: c4f7a2b9e3d1
Create Date: 2026-06-01 10:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "d5e8f1a2b3c4"
down_revision: str | None = "c4f7a2b9e3d1"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("counterparties", sa.Column("inn", sa.String(12), nullable=True))
    op.add_column("counterparties", sa.Column("kpp", sa.String(9), nullable=True))
    op.create_index("ix_counterparties_inn", "counterparties", ["inn"], unique=True)


def downgrade() -> None:
    op.drop_index("ix_counterparties_inn", table_name="counterparties")
    op.drop_column("counterparties", "kpp")
    op.drop_column("counterparties", "inn")
