"""add QA records with citations

Revision ID: e5f6a7b8c9d0
Revises: d4e5f6a7b8c9
Create Date: 2026-10-24 00:00:00.000000
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "e5f6a7b8c9d0"
down_revision: Union[str, None] = "d4e5f6a7b8c9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "qa_records",
        sa.Column(
            "user_id",
            sa.BigInteger().with_variant(sa.Integer(), "sqlite"),
            nullable=False,
        ),
        sa.Column(
            "course_id",
            sa.BigInteger().with_variant(sa.Integer(), "sqlite"),
            nullable=True,
        ),
        sa.Column(
            "knowledge_base_id",
            sa.BigInteger().with_variant(sa.Integer(), "sqlite"),
            nullable=True,
        ),
        sa.Column("scope", sa.String(length=16), nullable=False),
        sa.Column("question", sa.String(length=2000), nullable=False),
        sa.Column("answer", sa.Text(), nullable=False),
        sa.Column("references_json", sa.JSON(), nullable=False),
        sa.Column("hit", sa.Boolean(), nullable=False),
        sa.Column("intent", sa.String(length=32), nullable=True),
        sa.Column("scope_note", sa.String(length=500), nullable=True),
        sa.Column("latency_ms", sa.Integer(), nullable=False),
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
            ["course_id"],
            ["courses.id"],
            name=op.f("fk_qa_records_course_id_courses"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["knowledge_base_id"],
            ["knowledge_bases.id"],
            name=op.f("fk_qa_records_knowledge_base_id_knowledge_bases"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name=op.f("fk_qa_records_user_id_users"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_qa_records")),
    )
    op.create_index(op.f("ix_qa_records_user_id"), "qa_records", ["user_id"], unique=False)
    op.create_index(op.f("ix_qa_records_course_id"), "qa_records", ["course_id"], unique=False)
    op.create_index(
        op.f("ix_qa_records_knowledge_base_id"),
        "qa_records",
        ["knowledge_base_id"],
        unique=False,
    )
    op.create_index(op.f("ix_qa_records_status"), "qa_records", ["status"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_qa_records_status"), table_name="qa_records")
    op.drop_index(op.f("ix_qa_records_knowledge_base_id"), table_name="qa_records")
    op.drop_index(op.f("ix_qa_records_course_id"), table_name="qa_records")
    op.drop_index(op.f("ix_qa_records_user_id"), table_name="qa_records")
    op.drop_table("qa_records")
