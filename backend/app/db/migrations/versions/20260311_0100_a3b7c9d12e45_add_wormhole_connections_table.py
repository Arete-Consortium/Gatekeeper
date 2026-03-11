"""add_wormhole_connections_table

Revision ID: a3b7c9d12e45
Revises: d97abf453c56
Create Date: 2026-03-11 01:00:00.000000+00:00

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a3b7c9d12e45"
down_revision: str | None = "d97abf453c56"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "wormhole_connections",
        sa.Column("id", sa.String(length=20), nullable=False),
        sa.Column("from_system", sa.String(length=100), nullable=False),
        sa.Column("from_system_id", sa.Integer(), nullable=False),
        sa.Column("to_system", sa.String(length=100), nullable=False),
        sa.Column("to_system_id", sa.Integer(), nullable=False),
        sa.Column("wormhole_type", sa.String(length=20), nullable=False),
        sa.Column("mass_status", sa.String(length=20), nullable=False),
        sa.Column("life_status", sa.String(length=20), nullable=False),
        sa.Column("bidirectional", sa.Boolean(), nullable=False),
        sa.Column("max_lifetime_hours", sa.Float(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_by", sa.String(length=100), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("from_sig", sa.String(length=20), nullable=False),
        sa.Column("to_sig", sa.String(length=20), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_wormhole_connections_from", "wormhole_connections", ["from_system"], unique=False
    )
    op.create_index(
        "ix_wormhole_connections_to", "wormhole_connections", ["to_system"], unique=False
    )
    op.create_index(
        "ix_wormhole_connections_expires", "wormhole_connections", ["expires_at"], unique=False
    )


def downgrade() -> None:
    op.drop_index("ix_wormhole_connections_expires", table_name="wormhole_connections")
    op.drop_index("ix_wormhole_connections_to", table_name="wormhole_connections")
    op.drop_index("ix_wormhole_connections_from", table_name="wormhole_connections")
    op.drop_table("wormhole_connections")
