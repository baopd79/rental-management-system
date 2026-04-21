"""add partial unique indexes

Revision ID: 3644b0dd524b
Revises: b5e047e8f3c4
Create Date: 2026-04-21 22:28:45.390677

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '3644b0dd524b'
down_revision: Union[str, Sequence[str], None] = 'b5e047e8f3c4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_index(
        "idx_unique_room_name_per_property",
        "rooms",
        ["property_id", "display_name"],
        unique=True,
        postgresql_where=sa.text("is_archived = FALSE"),
    )
    op.create_index(
        "idx_unique_tenant_phone_per_landlord",
        "tenants",
        ["landlord_id", "phone"],
        unique=True,
        postgresql_where=sa.text("is_archived = FALSE"),
    )
    op.create_index(
        "idx_unique_tenant_email_per_landlord",
        "tenants",
        ["landlord_id", "email"],
        unique=True,
        postgresql_where=sa.text("is_archived = FALSE AND email IS NOT NULL"),
    )
    op.create_index(
        "idx_one_active_lease_per_room",
        "leases",
        ["room_id"],
        unique=True,
        postgresql_where=sa.text("terminated_at IS NULL"),
    )
    op.create_index(
        "idx_unique_invoice_per_lease_month",
        "invoices",
        ["lease_id", "billing_month"],
        unique=True,
        postgresql_where=sa.text("voided_at IS NULL"),
    )
    op.create_index(
        "idx_unique_invoice_number_per_landlord",
        "invoices",
        ["landlord_id", "invoice_number"],
        unique=True,
        postgresql_where=sa.text("voided_at IS NULL"),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(
        "idx_unique_invoice_number_per_landlord",
        table_name="invoices",
    )
    op.drop_index(
        "idx_unique_invoice_per_lease_month",
        table_name="invoices",
    )
    op.drop_index(
        "idx_one_active_lease_per_room",
        table_name="leases",
    )
    op.drop_index(
        "idx_unique_tenant_email_per_landlord",
        table_name="tenants",
    )
    op.drop_index(
        "idx_unique_tenant_phone_per_landlord",
        table_name="tenants",
    )
    op.drop_index(
        "idx_unique_room_name_per_property",
        table_name="rooms",
    )
