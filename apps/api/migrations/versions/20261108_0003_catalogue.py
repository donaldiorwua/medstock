"""catalogue: items, batches, stock_thresholds

Revision ID: 0003
Revises: 0002
Create Date: 2026-11-08
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0003"
down_revision: str | None = "0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "items",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("code", sa.String(40), nullable=False),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("base_unit", sa.String(32), nullable=False),
        sa.Column("description", sa.String(500), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("code = lower(code)", name="code_lowercase"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("code"),
    )
    op.create_table(
        "batches",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("item_id", sa.Uuid(), nullable=False),
        sa.Column("batch_number", sa.String(64), nullable=False),
        sa.Column("batch_number_key", sa.String(64), nullable=False),
        sa.Column("expiry_date", sa.Date(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("batch_number_key = lower(batch_number)", name="batch_key_matches"),
        sa.ForeignKeyConstraint(["item_id"], ["items.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("item_id", "batch_number_key", name="uq_batches_item_batch_number"),
    )
    op.create_index("ix_batches_item_id_expiry_date", "batches", ["item_id", "expiry_date"])
    op.create_table(
        "stock_thresholds",
        sa.Column("facility_id", sa.Uuid(), nullable=False),
        sa.Column("item_id", sa.Uuid(), nullable=False),
        sa.Column("reorder_level", sa.Integer(), nullable=False),
        sa.Column("critical_level", sa.Integer(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_by_id", sa.Uuid(), nullable=False),
        sa.CheckConstraint("critical_level >= 0", name="critical_nonneg"),
        sa.CheckConstraint("reorder_level >= critical_level", name="reorder_not_below_critical"),
        sa.ForeignKeyConstraint(["facility_id"], ["facilities.id"]),
        sa.ForeignKeyConstraint(["item_id"], ["items.id"]),
        sa.ForeignKeyConstraint(["updated_by_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("facility_id", "item_id"),
    )
    op.create_index("ix_stock_thresholds_item_id", "stock_thresholds", ["item_id"])


def downgrade() -> None:
    op.drop_table("stock_thresholds")
    op.drop_table("batches")
    op.drop_table("items")
