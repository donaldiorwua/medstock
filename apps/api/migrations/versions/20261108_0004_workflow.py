"""workflow: requests, lines, shipments, shipment lines, receipt lines, discrepancies

Revision ID: 0004
Revises: 0003
Create Date: 2026-11-08

Created before the stock ledger because ledger rows link back to shipment lines and
discrepancies.
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0004"
down_revision: str | None = "0003"
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
        "resupply_requests",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("facility_id", sa.Uuid(), nullable=False),
        sa.Column("supplier_facility_id", sa.Uuid(), nullable=False),
        sa.Column(
            "status",
            _enum(
                "status",
                "draft",
                "submitted",
                "approved",
                "partially_approved",
                "rejected",
                "dispatched",
                "received",
                "discrepancy_open",
                "closed",
                "cancelled",
            ),
            nullable=False,
        ),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("note", sa.String(500), nullable=True),
        sa.Column("created_by_id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("reviewed_by_id", sa.Uuid(), nullable=True),
        sa.Column("review_note", sa.String(500), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("facility_id <> supplier_facility_id", name="requester_not_supplier"),
        sa.CheckConstraint("version >= 1", name="version_positive"),
        sa.ForeignKeyConstraint(["facility_id"], ["facilities.id"]),
        sa.ForeignKeyConstraint(["supplier_facility_id"], ["facilities.id"]),
        sa.ForeignKeyConstraint(["created_by_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["reviewed_by_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_resupply_requests_facility_id_status", "resupply_requests", ["facility_id", "status"]
    )
    op.create_index(
        "ix_resupply_requests_status_created_at", "resupply_requests", ["status", "created_at"]
    )

    op.create_table(
        "resupply_request_lines",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("request_id", sa.Uuid(), nullable=False),
        sa.Column("item_id", sa.Uuid(), nullable=False),
        sa.Column("qty_requested", sa.Integer(), nullable=False),
        sa.Column("qty_approved", sa.Integer(), nullable=True),
        sa.Column(
            "status",
            _enum(
                "status",
                "pending",
                "approved",
                "partially_approved",
                "rejected",
                "dispatched",
                "received",
                "short_received",
            ),
            nullable=False,
        ),
        sa.Column("review_note", sa.String(500), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("qty_requested >= 1", name="qty_requested_positive"),
        sa.CheckConstraint("qty_approved IS NULL OR qty_approved >= 0", name="qty_approved_nonneg"),
        sa.CheckConstraint(
            "qty_approved IS NULL OR qty_approved <= qty_requested",
            name="approved_within_requested",
        ),
        sa.ForeignKeyConstraint(["request_id"], ["resupply_requests.id"]),
        sa.ForeignKeyConstraint(["item_id"], ["items.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("request_id", "item_id", name="uq_resupply_request_lines_request_item"),
    )
    op.create_index(
        "ix_resupply_request_lines_request_id", "resupply_request_lines", ["request_id"]
    )

    op.create_table(
        "shipments",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("request_id", sa.Uuid(), nullable=False),
        sa.Column("from_facility_id", sa.Uuid(), nullable=False),
        sa.Column("to_facility_id", sa.Uuid(), nullable=False),
        sa.Column(
            "status",
            _enum("status", "in_transit", "received", "received_with_discrepancy"),
            nullable=False,
        ),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("dispatched_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("dispatched_by_id", sa.Uuid(), nullable=False),
        sa.Column("received_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("received_by_id", sa.Uuid(), nullable=True),
        sa.Column("note", sa.String(500), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("from_facility_id <> to_facility_id", name="distinct_facilities"),
        sa.CheckConstraint("version >= 1", name="version_positive"),
        sa.ForeignKeyConstraint(["request_id"], ["resupply_requests.id"]),
        sa.ForeignKeyConstraint(["from_facility_id"], ["facilities.id"]),
        sa.ForeignKeyConstraint(["to_facility_id"], ["facilities.id"]),
        sa.ForeignKeyConstraint(["dispatched_by_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["received_by_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("request_id"),
    )
    op.create_index("ix_shipments_to_facility_id_status", "shipments", ["to_facility_id", "status"])

    op.create_table(
        "shipment_lines",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("shipment_id", sa.Uuid(), nullable=False),
        sa.Column("request_line_id", sa.Uuid(), nullable=False),
        sa.Column("batch_id", sa.Uuid(), nullable=False),
        sa.Column("qty_dispatched", sa.Integer(), nullable=False),
        sa.CheckConstraint("qty_dispatched >= 1", name="qty_dispatched_positive"),
        sa.ForeignKeyConstraint(["shipment_id"], ["shipments.id"]),
        sa.ForeignKeyConstraint(["request_line_id"], ["resupply_request_lines.id"]),
        sa.ForeignKeyConstraint(["batch_id"], ["batches.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "shipment_id", "request_line_id", "batch_id", name="uq_shipment_lines_line_batch"
        ),
        sa.UniqueConstraint("id", "qty_dispatched", name="uq_shipment_lines_id_qty_dispatched"),
    )
    op.create_index("ix_shipment_lines_shipment_id", "shipment_lines", ["shipment_id"])

    op.create_table(
        "receipt_lines",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("shipment_line_id", sa.Uuid(), nullable=False),
        sa.Column("qty_dispatched", sa.Integer(), nullable=False),
        sa.Column("qty_received", sa.Integer(), nullable=False),
        sa.Column("received_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("received_by_id", sa.Uuid(), nullable=False),
        sa.CheckConstraint("qty_received >= 0", name="qty_received_nonneg"),
        sa.CheckConstraint("qty_received <= qty_dispatched", name="received_within_dispatched"),
        sa.ForeignKeyConstraint(
            ["shipment_line_id", "qty_dispatched"],
            ["shipment_lines.id", "shipment_lines.qty_dispatched"],
            name="fk_receipt_lines_shipment_line_qty",
        ),
        sa.ForeignKeyConstraint(["received_by_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("shipment_line_id"),
    )

    op.create_table(
        "discrepancies",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("receipt_line_id", sa.Uuid(), nullable=False),
        sa.Column("qty_missing", sa.Integer(), nullable=False),
        sa.Column("status", _enum("status", "open", "resolved"), nullable=False),
        sa.Column(
            "resolution",
            _enum("resolution", "written_off", "recovered_to_phc", "recovered_to_store"),
            nullable=True,
        ),
        sa.Column("resolution_note", sa.String(500), nullable=True),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("resolved_by_id", sa.Uuid(), nullable=True),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("qty_missing >= 1", name="qty_missing_positive"),
        sa.CheckConstraint("version >= 1", name="version_positive"),
        sa.CheckConstraint(
            "(status = 'open' AND resolution IS NULL AND resolved_at IS NULL "
            "AND resolved_by_id IS NULL) OR "
            "(status = 'resolved' AND resolution IS NOT NULL AND resolved_at IS NOT NULL "
            "AND resolved_by_id IS NOT NULL)",
            name="state_consistent",
        ),
        sa.ForeignKeyConstraint(["receipt_line_id"], ["receipt_lines.id"]),
        sa.ForeignKeyConstraint(["resolved_by_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("receipt_line_id"),
    )
    op.create_index("ix_discrepancies_status", "discrepancies", ["status"])


def downgrade() -> None:
    op.drop_table("discrepancies")
    op.drop_table("receipt_lines")
    op.drop_table("shipment_lines")
    op.drop_table("shipments")
    op.drop_table("resupply_request_lines")
    op.drop_table("resupply_requests")
