"""add_jumpbridge_connections_table

Revision ID: b4c8d0e23f56
Revises: a3b7c9d12e45
Create Date: 2026-03-11 02:00:00.000000+00:00

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "b4c8d0e23f56"
down_revision: str | None = "a3b7c9d12e45"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "jumpbridge_connections",
        sa.Column("id", sa.String(length=20), nullable=False),
        sa.Column("from_system", sa.String(length=100), nullable=False),
        sa.Column("from_system_id", sa.Integer(), nullable=False),
        sa.Column("to_system", sa.String(length=100), nullable=False),
        sa.Column("to_system_id", sa.Integer(), nullable=False),
        sa.Column("owner_alliance", sa.String(length=100), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="unknown"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_by", sa.String(length=100), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_jumpbridge_connections_from", "jumpbridge_connections", ["from_system"], unique=False
    )
    op.create_index(
        "ix_jumpbridge_connections_to", "jumpbridge_connections", ["to_system"], unique=False
    )
    op.create_index(
        "ix_jumpbridge_connections_status", "jumpbridge_connections", ["status"], unique=False
    )


def downgrade() -> None:
    op.drop_index("ix_jumpbridge_connections_status", table_name="jumpbridge_connections")
    op.drop_index("ix_jumpbridge_connections_to", table_name="jumpbridge_connections")
    op.drop_index("ix_jumpbridge_connections_from", table_name="jumpbridge_connections")
    op.drop_table("jumpbridge_connections")
