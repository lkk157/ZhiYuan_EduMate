"""add courses, chapters, knowledges and enrollments

Revision ID: b2c3d4e5f6a7
Revises: 8f7e6d5c4b3a
Create Date: 2026-10-23 18:00:00.000000
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "b2c3d4e5f6a7"
down_revision: Union[str, None] = "8f7e6d5c4b3a"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "courses",
        sa.Column("title", sa.String(length=100), nullable=False),
        sa.Column("description", sa.String(length=2000), nullable=True),
        sa.Column("cover_url", sa.String(length=255), nullable=True),
        sa.Column(
            "teacher_id",
            sa.BigInteger().with_variant(sa.Integer(), "sqlite"),
            nullable=False,
        ),
        sa.Column("invite_code", sa.String(length=16), nullable=False),
        sa.Column("invite_enabled", sa.Boolean(), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("review_comment", sa.String(length=500), nullable=True),
        sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "reviewed_by_id",
            sa.BigInteger().with_variant(sa.Integer(), "sqlite"),
            nullable=True,
        ),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "id",
            sa.BigInteger().with_variant(sa.Integer(), "sqlite"),
            autoincrement=True,
            nullable=False,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["teacher_id"], ["users.id"], name=op.f("fk_courses_teacher_id_users")
        ),
        sa.ForeignKeyConstraint(
            ["reviewed_by_id"],
            ["users.id"],
            name=op.f("fk_courses_reviewed_by_id_users"),
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_courses")),
    )
    op.create_index(op.f("ix_courses_invite_code"), "courses", ["invite_code"], unique=True)
    op.create_index(op.f("ix_courses_status"), "courses", ["status"], unique=False)
    op.create_index(op.f("ix_courses_teacher_id"), "courses", ["teacher_id"], unique=False)

    op.create_table(
        "chapters",
        sa.Column(
            "course_id",
            sa.BigInteger().with_variant(sa.Integer(), "sqlite"),
            nullable=False,
        ),
        sa.Column("title", sa.String(length=100), nullable=False),
        sa.Column("description", sa.String(length=500), nullable=True),
        sa.Column("order_no", sa.Integer(), nullable=False),
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
            name=op.f("fk_chapters_course_id_courses"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_chapters")),
    )
    op.create_index(op.f("ix_chapters_course_id"), "chapters", ["course_id"], unique=False)

    op.create_table(
        "knowledges",
        sa.Column(
            "course_id",
            sa.BigInteger().with_variant(sa.Integer(), "sqlite"),
            nullable=False,
        ),
        sa.Column(
            "chapter_id",
            sa.BigInteger().with_variant(sa.Integer(), "sqlite"),
            nullable=False,
        ),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("description", sa.String(length=500), nullable=True),
        sa.Column("difficulty", sa.Integer(), nullable=False),
        sa.Column(
            "id",
            sa.BigInteger().with_variant(sa.Integer(), "sqlite"),
            autoincrement=True,
            nullable=False,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["chapter_id"],
            ["chapters.id"],
            name=op.f("fk_knowledges_chapter_id_chapters"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["course_id"],
            ["courses.id"],
            name=op.f("fk_knowledges_course_id_courses"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_knowledges")),
    )
    op.create_index(op.f("ix_knowledges_chapter_id"), "knowledges", ["chapter_id"], unique=False)
    op.create_index(op.f("ix_knowledges_course_id"), "knowledges", ["course_id"], unique=False)

    op.create_table(
        "course_enrollments",
        sa.Column(
            "course_id",
            sa.BigInteger().with_variant(sa.Integer(), "sqlite"),
            nullable=False,
        ),
        sa.Column(
            "student_id",
            sa.BigInteger().with_variant(sa.Integer(), "sqlite"),
            nullable=False,
        ),
        sa.Column("source", sa.String(length=16), nullable=False),
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
            name=op.f("fk_course_enrollments_course_id_courses"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["student_id"],
            ["users.id"],
            name=op.f("fk_course_enrollments_student_id_users"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_course_enrollments")),
        sa.UniqueConstraint("course_id", "student_id", name="uq_course_enrollment"),
    )
    op.create_index(
        op.f("ix_course_enrollments_course_id"),
        "course_enrollments",
        ["course_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_course_enrollments_student_id"),
        "course_enrollments",
        ["student_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_course_enrollments_student_id"), table_name="course_enrollments")
    op.drop_index(op.f("ix_course_enrollments_course_id"), table_name="course_enrollments")
    op.drop_table("course_enrollments")
    op.drop_index(op.f("ix_knowledges_course_id"), table_name="knowledges")
    op.drop_index(op.f("ix_knowledges_chapter_id"), table_name="knowledges")
    op.drop_table("knowledges")
    op.drop_index(op.f("ix_chapters_course_id"), table_name="chapters")
    op.drop_table("chapters")
    op.drop_index(op.f("ix_courses_teacher_id"), table_name="courses")
    op.drop_index(op.f("ix_courses_status"), table_name="courses")
    op.drop_index(op.f("ix_courses_invite_code"), table_name="courses")
    op.drop_table("courses")
