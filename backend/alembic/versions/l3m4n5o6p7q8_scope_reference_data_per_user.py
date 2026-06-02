"""scope reference data per user

Revision ID: l3m4n5o6p7q8
Revises: k2l3m4n5o6p7
Create Date: 2026-06-02 14:30:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "l3m4n5o6p7q8"
down_revision: str | None = "k2l3m4n5o6p7"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    bind = op.get_bind()
    first_user_id = bind.execute(
        sa.text("SELECT id FROM users ORDER BY created_at, id LIMIT 1")
    ).scalar_one_or_none()

    if first_user_id is None:
        total_reference_rows = sum(
            bind.execute(sa.text(f"SELECT COUNT(*) FROM {table_name}")).scalar_one()
            for table_name in ("counterparties", "expense_types", "exchange_rates")
        )
        if total_reference_rows > 0:
            raise RuntimeError("Cannot backfill user_id for reference data without any users.")

    with op.batch_alter_table("counterparties") as batch_op:
        batch_op.add_column(sa.Column("user_id", sa.Uuid(), nullable=True))

    with op.batch_alter_table("expense_types") as batch_op:
        batch_op.add_column(sa.Column("user_id", sa.Uuid(), nullable=True))

    with op.batch_alter_table("exchange_rates") as batch_op:
        batch_op.add_column(sa.Column("user_id", sa.Uuid(), nullable=True))

    if first_user_id is not None:
        bind.execute(
            sa.text(
                """
                UPDATE counterparties
                SET user_id = (
                    SELECT receipts.user_id
                    FROM receipts
                    WHERE receipts.counterparty_id = counterparties.id
                      AND receipts.user_id IS NOT NULL
                    ORDER BY receipts.paid_at
                    LIMIT 1
                )
                WHERE user_id IS NULL
                """
            )
        )
        bind.execute(
            sa.text(
                """
                UPDATE counterparties
                SET user_id = (
                    SELECT accounts.user_id
                    FROM transactions
                    JOIN accounts ON accounts.id = transactions.account_id
                    WHERE transactions.counterparty_id = counterparties.id
                    ORDER BY transactions.occurred_at
                    LIMIT 1
                )
                WHERE user_id IS NULL
                """
            )
        )
        bind.execute(
            sa.text("UPDATE counterparties SET user_id = :user_id WHERE user_id IS NULL"),
            {"user_id": first_user_id},
        )

        bind.execute(
            sa.text(
                """
                UPDATE expense_types
                SET user_id = (
                    SELECT accounts.user_id
                    FROM transactions
                    JOIN accounts ON accounts.id = transactions.account_id
                    WHERE transactions.expense_type_id = expense_types.id
                    ORDER BY transactions.occurred_at
                    LIMIT 1
                )
                WHERE user_id IS NULL
                """
            )
        )
        bind.execute(
            sa.text("UPDATE expense_types SET user_id = :user_id WHERE user_id IS NULL"),
            {"user_id": first_user_id},
        )

        bind.execute(
            sa.text("UPDATE exchange_rates SET user_id = :user_id WHERE user_id IS NULL"),
            {"user_id": first_user_id},
        )

        op.execute(sa.text("PRAGMA foreign_keys=OFF"))

        counterparties = bind.execute(sa.text("SELECT id, user_id FROM counterparties")).fetchall()
        for row in counterparties:
            old_id = row.id
            if ":" in old_id:
                continue
            new_id = f"{row.user_id}:{old_id}"
            bind.execute(
                sa.text("UPDATE receipts SET counterparty_id = :new_id WHERE counterparty_id = :old_id"),
                {"new_id": new_id, "old_id": old_id},
            )
            bind.execute(
                sa.text(
                    "UPDATE transactions SET counterparty_id = :new_id WHERE counterparty_id = :old_id"
                ),
                {"new_id": new_id, "old_id": old_id},
            )
            bind.execute(
                sa.text("UPDATE counterparties SET id = :new_id WHERE id = :old_id"),
                {"new_id": new_id, "old_id": old_id},
            )

        expense_types = bind.execute(sa.text("SELECT id, user_id FROM expense_types")).fetchall()
        for row in expense_types:
            old_id = row.id
            if ":" in old_id:
                continue
            new_id = f"{row.user_id}:{old_id}"
            bind.execute(
                sa.text(
                    "UPDATE transactions SET expense_type_id = :new_id WHERE expense_type_id = :old_id"
                ),
                {"new_id": new_id, "old_id": old_id},
            )
            bind.execute(
                sa.text("UPDATE expense_types SET id = :new_id WHERE id = :old_id"),
                {"new_id": new_id, "old_id": old_id},
            )

        op.execute(sa.text("PRAGMA foreign_keys=ON"))

    with op.batch_alter_table("counterparties") as batch_op:
        batch_op.alter_column("user_id", existing_type=sa.Uuid(), nullable=False)
        batch_op.create_index("ix_counterparties_user_id", ["user_id"], unique=False)
        batch_op.drop_index("ix_counterparties_inn")
        batch_op.create_unique_constraint("uq_counterparty_user_inn", ["user_id", "inn"])

    with op.batch_alter_table("expense_types") as batch_op:
        batch_op.alter_column("user_id", existing_type=sa.Uuid(), nullable=False)
        batch_op.create_index("ix_expense_types_user_id", ["user_id"], unique=False)
        batch_op.create_unique_constraint("uq_expense_type_user_id_id", ["user_id", "id"])

    with op.batch_alter_table("exchange_rates") as batch_op:
        batch_op.alter_column("user_id", existing_type=sa.Uuid(), nullable=False)
        batch_op.create_index("ix_exchange_rates_user_id", ["user_id"], unique=False)


def downgrade() -> None:
    with op.batch_alter_table("exchange_rates") as batch_op:
        batch_op.drop_index("ix_exchange_rates_user_id")
        batch_op.drop_column("user_id")

    with op.batch_alter_table("expense_types") as batch_op:
        batch_op.drop_constraint("uq_expense_type_user_id_id", type_="unique")
        batch_op.drop_index("ix_expense_types_user_id")
        batch_op.drop_column("user_id")

    with op.batch_alter_table("counterparties") as batch_op:
        batch_op.drop_constraint("uq_counterparty_user_inn", type_="unique")
        batch_op.drop_index("ix_counterparties_user_id")
        batch_op.create_index("ix_counterparties_inn", ["inn"], unique=True)
        batch_op.drop_column("user_id")
