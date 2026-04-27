"""add unique constraint on users.email

Revision ID: 55e0dc5c8b44
Revises: a4d3745501b5
Create Date: 2026-04-27 16:53:59.674486

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import sqlmodel


# revision identifiers, used by Alembic.
revision: str = "55e0dc5c8b44"
down_revision: Union[str, Sequence[str], None] = "a4d3745501b5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add UNIQUE constraint on users.email."""
    op.create_index(op.f("ix_users_email"), "users", ["email"], unique=True)


def downgrade() -> None:
    """Remove UNIQUE constraint."""
    op.drop_index(op.f("ix_users_email"), table_name="users")

