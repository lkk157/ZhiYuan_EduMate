"""add per-user material view tracking

Revision ID: f6a7b8c9d0e1
Revises: e5f6a7b8c9d0
Create Date: 2026-10-24 12:00:00.000000
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "f6a7b8c9d0e1"
down_revision: Union[str, None] = "e5f6a7b8c9d0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "material_views",
        sa.Column(
            "user_id",
            sa.BigInteger().with_variant(sa.Integer(), "sqlite"),
            nullable=False,
        ),
        sa.Column(
            "material_id",
            sa.BigInteger().with_variant(sa.Integer(), "sqlite"),
            nullable=False,
        ),
        sa.Column("viewed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "id",
            sa.BigInteger().with_variant(sa.Integer(), "sqlite"),
            autoincrement=True,
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["material_id"],
            ["materials.id"],
            name=op.f("fk_material_views_material_id_materials"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name=op.f("fk_material_views_user_id_users"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_material_views")),
        sa.UniqueConstraint(
            "user_id",
            "material_id",
            name="uq_material_view_user_material",
        ),
    )
    op.create_index(
        op.f("ix_material_views_user_id"), "material_views", ["user_id"], unique=False
    )
    op.create_index(
        op.f("ix_material_views_material_id"),
        "material_views",
        ["material_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_material_views_viewed_at"),
        "material_views",
        ["viewed_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_material_views_viewed_at"), table_name="material_views")
    op.drop_index(op.f("ix_material_views_material_id"), table_name="material_views")
    op.drop_index(op.f("ix_material_views_user_id"), table_name="material_views")
    op.drop_table("material_views")
