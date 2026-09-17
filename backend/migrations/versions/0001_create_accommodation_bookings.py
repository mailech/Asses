"""Create the accommodation_bookings table.

Revision ID: 0001
Revises:
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

from app.db.models import JsonDocument

revision: str = "0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

TABLE = "accommodation_bookings"


def upgrade() -> None:
    op.create_table(
        TABLE,
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("bill_number", sa.Integer(), nullable=False),
        sa.Column("raw_input", sa.Text(), nullable=False),
        sa.Column("parsed_request", JsonDocument, nullable=False),
        sa.Column("quote", JsonDocument, nullable=False),
        sa.Column("currency", sa.String(length=3), nullable=False),
        sa.Column("total_cents", sa.Integer(), nullable=False),
        sa.Column("nights", sa.Integer(), nullable=False),
        sa.Column("guests", sa.Integer(), nullable=False),
        sa.Column("room_count", sa.Integer(), nullable=False),
        sa.Column("meal_plan", sa.String(length=16), nullable=False),
        sa.UniqueConstraint("bill_number", name="uq_bookings_bill_number"),
    )
    op.create_index(f"ix_{TABLE}_created_at", TABLE, ["created_at"])
    op.create_index(f"ix_{TABLE}_meal_plan", TABLE, ["meal_plan"])
    # The listing pages by bill_number; its unique constraint indexes it.


def downgrade() -> None:
    op.drop_index(f"ix_{TABLE}_meal_plan", table_name=TABLE)
    op.drop_index(f"ix_{TABLE}_created_at", table_name=TABLE)
    op.drop_table(TABLE)
