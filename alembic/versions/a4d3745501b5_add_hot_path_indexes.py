"""add hot-path indexes

Revision ID: a4d3745501b5
Revises: 25bfdb8601ff
Create Date: 2026-04-22 02:26:21.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "a4d3745501b5"
down_revision: Union[str, Sequence[str], None] = "25bfdb8601ff"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_index(
        "idx_readings_service_room_date",
        "meter_readings",
        ["service_id", "room_id", sa.text("reading_date DESC")],
    )
    op.create_index(
        "idx_readings_service_shared_date",
        "meter_readings",
        ["service_id", sa.text("reading_date DESC")],
        postgresql_where=sa.text("room_id IS NULL"),
    )
    op.create_index(
        "idx_line_items_invoice",
        "invoice_line_items",
        ["invoice_id", "sort_order"],
    )
    # Invoice line items reference meter readings through two separate FKs.
    # Separate partial indexes help `start_id = ? OR end_id = ?` lookups better
    # than a composite index on both columns.
    op.create_index(
        "idx_line_items_meter_reading_start",
        "invoice_line_items",
        ["meter_reading_start_id"],
        postgresql_where=sa.text("meter_reading_start_id IS NOT NULL"),
    )
    op.create_index(
        "idx_line_items_meter_reading_end",
        "invoice_line_items",
        ["meter_reading_end_id"],
        postgresql_where=sa.text("meter_reading_end_id IS NOT NULL"),
    )
    op.create_index(
        "idx_payments_invoice",
        "payments",
        ["invoice_id", sa.text("paid_at DESC")],
    )
    op.create_index(
        "idx_audit_entity",
        "audit_logs",
        ["entity_type", "entity_id"],
    )
    op.create_index(
        "idx_audit_actor",
        "audit_logs",
        ["actor_id"],
    )
    op.create_index(
        "idx_audit_time",
        "audit_logs",
        [sa.text("created_at DESC")],
    )
    op.create_index(
        "idx_notif_recipient",
        "notifications",
        ["recipient_id", "is_read", sa.text("created_at DESC")],
    )
    op.create_index(
        "idx_occupants_active",
        "occupants",
        ["tenant_id"],
        postgresql_where=sa.text("moved_out_date IS NULL"),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(
        "idx_occupants_active",
        table_name="occupants",
    )
    op.drop_index(
        "idx_notif_recipient",
        table_name="notifications",
    )
    op.drop_index(
        "idx_audit_time",
        table_name="audit_logs",
    )
    op.drop_index(
        "idx_audit_actor",
        table_name="audit_logs",
    )
    op.drop_index(
        "idx_audit_entity",
        table_name="audit_logs",
    )
    op.drop_index(
        "idx_payments_invoice",
        table_name="payments",
    )
    op.drop_index(
        "idx_line_items_meter_reading_end",
        table_name="invoice_line_items",
    )
    op.drop_index(
        "idx_line_items_meter_reading_start",
        table_name="invoice_line_items",
    )
    op.drop_index(
        "idx_line_items_invoice",
        table_name="invoice_line_items",
    )
    op.drop_index(
        "idx_readings_service_shared_date",
        table_name="meter_readings",
    )
    op.drop_index(
        "idx_readings_service_room_date",
        table_name="meter_readings",
    )
