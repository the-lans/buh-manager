"""add inn and kpp to counterparties

Revision ID: d1e2f3a4b5c6
Revises: c4f7a2b9e3d1
Create Date: 2026-06-01 12:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "d1e2f3a4b5c6"
down_revision: str | None = "c4f7a2b9e3d1"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("counterparties", sa.Column("inn", sa.String(length=12), nullable=True))
    op.add_column("counterparties", sa.Column("kpp", sa.String(length=9), nullable=True))
    op.create_unique_constraint("uq_counterparties_inn", "counterparties", ["inn"])


def downgrade() -> None:
    op.drop_constraint("uq_counterparties_inn", "counterparties", type_="unique")
    op.drop_column("counterparties", "kpp")
    op.drop_column("counterparties", "inn")
