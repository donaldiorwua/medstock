"""stock ledger: stock_balances, stock_movements

Revision ID: 0005
Revises: 0004
Create Date: 2026-11-08
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0005"
down_revision: str | None = "0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _enum(name: str, *values: str) -> sa.Enum:
    return sa.Enum(
        *values,
        name=name,
        native_enum=False,
        create_constraint=True,
        length=max(len(v) for v in values),
    )


def upgrade() -> None:
    op.create_table(
        "stock_balances",
        sa.Column("facility_id", sa.Uuid(), nullable=False),
        sa.Column("batch_id", sa.Uuid(), nullable=False),
        sa.Column("qty_available", sa.Integer(), nullable=False),
        sa.Column("qty_quarantined", sa.Integer(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("qty_available >= 0", name="qty_available_nonneg"),
        sa.CheckConstraint("qty_quarantined >= 0", name="qty_quarantined_nonneg"),
        sa.ForeignKeyConstraint(["facility_id"], ["facilities.id"]),
        sa.ForeignKeyConstraint(["batch_id"], ["batches.id"]),
        sa.PrimaryKeyConstraint("facility_id", "batch_id"),
    )
    op.create_index("ix_stock_balances_batch_id", "stock_balances", ["batch_id"])

    op.create_table(
        "stock_movements",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("posting_id", sa.Uuid(), nullable=False),
        sa.Column("facility_id", sa.Uuid(), nullable=False),
        sa.Column("batch_id", sa.Uuid(), nullable=False),
        sa.Column(
            "movement_type",
            _enum(
                "movement_type",
                "opening",
                "receipt",
                "issue",
                "adjustment",
                "quarantine",
                "release",
                "expiry_writeoff",
                "reversal",
                "dispatch",
                "shipment_receipt",
                "discrepancy_write_off",
                "discrepancy_recovery_to_phc",
                "discrepancy_recovery_to_store",
            ),
            nullable=False,
        ),
        sa.Column("bucket", _enum("bucket", "available", "quarantined"), nullable=False),
        sa.Column("quantity_delta", sa.Integer(), nullable=False),
        sa.Column("balance_after", sa.Integer(), nullable=False),
        sa.Column("occurred_on", sa.Date(), nullable=False),
        sa.Column(
            "reason",
            _enum(
                "reason",
                "count_correction",
                "damage",
                "loss",
                "found",
                "entry_error",
                "other",
            ),
            nullable=True,
        ),
        sa.Column("note", sa.String(500), nullable=True),
        sa.Column("reference", sa.String(120), nullable=True),
        sa.Column("source", sa.String(120), nullable=True),
        sa.Column("signed_off_by", sa.String(120), nullable=True),
        sa.Column("needs_review", sa.Boolean(), nullable=False),
        sa.Column("reverses_movement_id", sa.Uuid(), nullable=True),
        sa.Column("shipment_line_id", sa.Uuid(), nullable=True),
        sa.Column("discrepancy_id", sa.Uuid(), nullable=True),
        sa.Column("created_by_id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("quantity_delta <> 0", name="delta_nonzero"),
        sa.CheckConstraint("balance_after >= 0", name="balance_after_nonneg"),
        sa.CheckConstraint(
            "movement_type <> 'adjustment' OR reason IS NOT NULL", name="adjustment_has_reason"
        ),
        sa.CheckConstraint(
            "movement_type <> 'opening' OR signed_off_by IS NOT NULL", name="opening_signed_off"
        ),
        sa.CheckConstraint(
            "movement_type <> 'reversal' OR reverses_movement_id IS NOT NULL",
            name="reversal_has_target",
        ),
        sa.CheckConstraint(
            "movement_type = 'reversal' OR reverses_movement_id IS NULL",
            name="only_reversals_have_target",
        ),
        sa.ForeignKeyConstraint(["facility_id"], ["facilities.id"]),
        sa.ForeignKeyConstraint(["batch_id"], ["batches.id"]),
        sa.ForeignKeyConstraint(["reverses_movement_id"], ["stock_movements.id"]),
        sa.ForeignKeyConstraint(["shipment_line_id"], ["shipment_lines.id"]),
        sa.ForeignKeyConstraint(["discrepancy_id"], ["discrepancies.id"]),
        sa.ForeignKeyConstraint(["created_by_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("reverses_movement_id"),
    )
    op.create_index(
        "ix_stock_movements_facility_id_created_at",
        "stock_movements",
        ["facility_id", "created_at"],
    )
    op.create_index("ix_stock_movements_batch_id", "stock_movements", ["batch_id"])
    op.create_index("ix_stock_movements_posting_id", "stock_movements", ["posting_id"])
    op.create_index(
        "uq_stock_movements_opening",
        "stock_movements",
        ["facility_id", "batch_id"],
        unique=True,
        sqlite_where=sa.text("movement_type = 'opening'"),
        postgresql_where=sa.text("movement_type = 'opening'"),
    )


def downgrade() -> None:
    op.drop_table("stock_movements")
    op.drop_table("stock_balances")
