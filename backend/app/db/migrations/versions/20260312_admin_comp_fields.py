"""add comp fields to users table

Revision ID: b7e2c4a91d03
Revises: af5cb326762b
Create Date: 2026-03-12

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "b7e2c4a91d03"
down_revision: Union[str, None] = "af5cb326762b"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("comp_expires_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "users",
        sa.Column("comp_reason", sa.String(length=200), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("users", "comp_reason")
    op.drop_column("users", "comp_expires_at")
