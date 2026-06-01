"""make counterparty inn unique

Revision ID: f7a8b9c0d1e2
Revises: e6f9g2h3i4j5
Create Date: 2026-06-01 15:30:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "f7a8b9c0d1e2"
down_revision: str | None = "e6f9g2h3i4j5"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    duplicate_inns = (
        op.get_bind()
        .execute(
            sa.text(
                """
            SELECT inn, COUNT(*) AS duplicate_count
            FROM counterparties
            WHERE inn IS NOT NULL
            GROUP BY inn
            HAVING COUNT(*) > 1
            """
            )
        )
        .fetchall()
    )
    if duplicate_inns:
        values = ", ".join(f"{row.inn} ({row.duplicate_count})" for row in duplicate_inns)
        raise RuntimeError(f"Cannot create unique INN index; duplicate INNs exist: {values}")

    op.drop_index("ix_counterparties_inn", table_name="counterparties")
    op.create_index("ix_counterparties_inn", "counterparties", ["inn"], unique=True)


def downgrade() -> None:
    op.drop_index("ix_counterparties_inn", table_name="counterparties")
    op.create_index("ix_counterparties_inn", "counterparties", ["inn"])
