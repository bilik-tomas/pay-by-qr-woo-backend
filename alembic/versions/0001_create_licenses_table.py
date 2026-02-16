"""create licenses table

Revision ID: 0001_create_licenses_table
Revises:
Create Date: 2026-02-16 11:20:00
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0001_create_licenses_table"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "licenses",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("license_key", sa.String(length=128), nullable=False),
        sa.Column("domain", sa.String(length=255), nullable=False, server_default=""),
        sa.Column("plugin_instance_id", sa.String(length=128), nullable=False, server_default=""),
        sa.Column("status", sa.String(length=16), nullable=False, server_default="active"),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("note", sa.String(length=255), nullable=False, server_default=""),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_licenses_license_key", "licenses", ["license_key"], unique=True)
    op.create_index("ix_licenses_status", "licenses", ["status"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_licenses_status", table_name="licenses")
    op.drop_index("ix_licenses_license_key", table_name="licenses")
    op.drop_table("licenses")
