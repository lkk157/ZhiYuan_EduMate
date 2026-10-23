"""add personal knowledge bases and material scope

Revision ID: d4e5f6a7b8c9
Revises: c3d4e5f6a7b8
Create Date: 2026-10-23 22:00:00.000000
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "d4e5f6a7b8c9"
down_revision: Union[str, None] = "c3d4e5f6a7b8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "knowledge_bases",
        sa.Column(
            "owner_id",
            sa.BigInteger().with_variant(sa.Integer(), "sqlite"),
            nullable=False,
        ),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("description", sa.String(length=500), nullable=True),
        sa.Column("rag_group_id", sa.Integer(), nullable=True),
        sa.Column("is_default", sa.Boolean(), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column(
            "id",
            sa.BigInteger().with_variant(sa.Integer(), "sqlite"),
            autoincrement=True,
            nullable=False,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["owner_id"],
            ["users.id"],
            name=op.f("fk_knowledge_bases_owner_id_users"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_knowledge_bases")),
    )
    op.create_index(
        op.f("ix_knowledge_bases_owner_id"), "knowledge_bases", ["owner_id"], unique=False
    )
    op.create_index(
        op.f("ix_knowledge_bases_status"), "knowledge_bases", ["status"], unique=False
    )

    with op.batch_alter_table("materials") as batch_op:
        batch_op.add_column(
            sa.Column(
                "scope",
                sa.String(length=16),
                nullable=False,
                server_default="course",
            )
        )
        batch_op.add_column(
            sa.Column(
                "knowledge_base_id",
                sa.BigInteger().with_variant(sa.Integer(), "sqlite"),
                nullable=True,
            )
        )
        batch_op.add_column(
            sa.Column(
                "owner_id",
                sa.BigInteger().with_variant(sa.Integer(), "sqlite"),
                nullable=True,
            )
        )
        batch_op.alter_column(
            "course_id",
            existing_type=sa.BigInteger().with_variant(sa.Integer(), "sqlite"),
            nullable=True,
        )
        batch_op.create_foreign_key(
            op.f("fk_materials_knowledge_base_id_knowledge_bases"),
            "knowledge_bases",
            ["knowledge_base_id"],
            ["id"],
            ondelete="SET NULL",
        )
        batch_op.create_foreign_key(
            op.f("fk_materials_owner_id_users"),
            "users",
            ["owner_id"],
            ["id"],
            ondelete="SET NULL",
        )
        batch_op.create_index(op.f("ix_materials_scope"), ["scope"], unique=False)
        batch_op.create_index(
            op.f("ix_materials_knowledge_base_id"), ["knowledge_base_id"], unique=False
        )
        batch_op.create_index(op.f("ix_materials_owner_id"), ["owner_id"], unique=False)

    op.execute("UPDATE materials SET owner_id = uploader_id WHERE owner_id IS NULL")


def downgrade() -> None:
    op.execute("DELETE FROM materials WHERE course_id IS NULL")
    with op.batch_alter_table("materials") as batch_op:
        batch_op.drop_index(op.f("ix_materials_owner_id"))
        batch_op.drop_index(op.f("ix_materials_knowledge_base_id"))
        batch_op.drop_index(op.f("ix_materials_scope"))
        batch_op.drop_constraint(
            op.f("fk_materials_owner_id_users"), type_="foreignkey"
        )
        batch_op.drop_constraint(
            op.f("fk_materials_knowledge_base_id_knowledge_bases"), type_="foreignkey"
        )
        batch_op.alter_column(
            "course_id",
            existing_type=sa.BigInteger().with_variant(sa.Integer(), "sqlite"),
            nullable=False,
        )
        batch_op.drop_column("owner_id")
        batch_op.drop_column("knowledge_base_id")
        batch_op.drop_column("scope")

    op.drop_index(op.f("ix_knowledge_bases_status"), table_name="knowledge_bases")
    op.drop_index(op.f("ix_knowledge_bases_owner_id"), table_name="knowledge_bases")
    op.drop_table("knowledge_bases")
