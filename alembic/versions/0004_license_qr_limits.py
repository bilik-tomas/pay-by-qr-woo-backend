"""add per-license qr limits

Revision ID: 0004_license_qr_limits
Revises: 0003_admin_users
Create Date: 2026-02-16 23:40:00
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0004_license_qr_limits"
down_revision: Union[str, None] = "0003_admin_users"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "licenses",
        sa.Column("daily_qr_limit", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column(
        "licenses",
        sa.Column("monthly_qr_limit", sa.Integer(), nullable=False, server_default="0"),
    )


def downgrade() -> None:
    op.drop_column("licenses", "monthly_qr_limit")
    op.drop_column("licenses", "daily_qr_limit")
