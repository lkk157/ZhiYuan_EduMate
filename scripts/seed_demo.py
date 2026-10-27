"""Idempotent phase-one demo data.

Creates five accounts, three published courses, chapters/knowledge points,
enrollments, approved materials and two personal knowledge bases. Pass
``--with-rag`` to index the seeded materials into the real RAG service.

Usage:
    python scripts/seed_demo.py
    python scripts/seed_demo.py --with-rag
    python scripts/seed_demo.py --reset-passwords --with-rag
"""

from __future__ import annotations

import argparse
import asyncio
import shutil
import sys
from dataclasses import dataclass
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from sqlalchemy import select  # noqa: E402

from app.core.config import get_settings  # noqa: E402
from app.core.security import hash_password  # noqa: E402
from app.db.base import utc_now  # noqa: E402
from app.db.models.course import (  # noqa: E402
    COURSE_STATUS_APPROVED,
    ENROLLMENT_SOURCE_INVITE,
    Chapter,
    Course,
    CourseEnrollment,
    Knowledge,
)
from app.db.models.knowledge_base import KB_STATUS_ACTIVE, KnowledgeBase  # noqa: E402
from app.db.models.material import (  # noqa: E402
    INDEX_STATUS_INDEXED,
    MATERIAL_SCOPE_COURSE,
    MATERIAL_SCOPE_PERSONAL,
    MATERIAL_STATUS_APPROVED,
    Material,
)
from app.db.models.rbac import USER_STATUS_ACTIVE, Role, User  # noqa: E402
from app.db.session import AsyncSessionLocal  # noqa: E402
from app.services.material_service import index_material, sanitize_filename  # noqa: E402
from app.services.rag_client import RagClient  # noqa: E402
from scripts.seed import seed as seed_rbac  # noqa: E402

AUTO_REVIEW_COMMENT = "演示数据自动审核通过"
SAMPLES = PROJECT_ROOT / "samples"

DEMO_ACCOUNTS = [
    ("admin", "admin@edumate.local", "admin"),
    ("teacher", "teacher@edumate.local", "teacher"),
    ("teacher2", "teacher2@edumate.local", "teacher"),
    ("student", "student@edumate.local", "student"),
    ("student2", "student2@edumate.local", "student"),
]


@dataclass(frozen=True)
class CourseSpec:
    title: str
    description: str
    invite_code: str
    teacher: str
    chapters: tuple[tuple[str, tuple[str, ...]], ...]
    materials: tuple[tuple[str, str, str, str], ...]
    # (title, chapter title, knowledge name, sample file name)


COURSES = (
    CourseSpec(
        title="人工智能基础入门",
        description="从监督学习到模型评估，适合零基础入门的人工智能课程。",
        invite_code="AI2026AA",
        teacher="teacher",
        chapters=(
            ("第一章 机器学习概述", ("监督学习", "无监督学习")),
            ("第二章 模型评估", ("过拟合与欠拟合", "交叉验证")),
        ),
        materials=(
            ("机器学习基础讲义", "第一章 机器学习概述", "监督学习", "机器学习基础.docx"),
            ("模型评估方法讲义", "第二章 模型评估", "交叉验证", "机器学习基础.docx"),
        ),
    ),
    CourseSpec(
        title="数据结构与算法",
        description="线性表、树与图、算法复杂度与常见数据结构实现。",
        invite_code="DS2026BB",
        teacher="teacher",
        chapters=(
            ("第一章 线性表", ("顺序表", "单链表")),
            ("第二章 树与图", ("二叉树", "图的遍历")),
        ),
        materials=(
            ("线性表与链表讲义", "第一章 线性表", "单链表", "数据结构与算法基础.docx"),
            ("树与图基础讲义", "第二章 树与图", "二叉树", "数据结构与算法基础.docx"),
        ),
    ),
    CourseSpec(
        title="Python 程序设计入门",
        description="Python 基础语法、函数、模块与异常处理。",
        invite_code="PY2026CC",
        teacher="teacher2",
        chapters=(
            ("第一章 基础语法", ("变量与数据类型", "流程控制")),
            ("第二章 函数与模块", ("函数定义", "模块与异常")),
        ),
        materials=(
            ("Python 基础语法讲义", "第一章 基础语法", "变量与数据类型", "Python程序设计基础.docx"),
            ("函数与模块讲义", "第二章 函数与模块", "函数定义", "Python程序设计基础.docx"),
        ),
    ),
)

ENROLLMENTS = (
    ("student", "人工智能基础入门"),
    ("student", "数据结构与算法"),
    ("student2", "数据结构与算法"),
    ("student2", "Python 程序设计入门"),
)

PERSONAL_LIBRARIES = (
    ("student", "算法学习笔记", "数据结构与算法基础.docx"),
    ("student2", "Python 练习笔记", "Python程序设计基础.docx"),
)


async def ensure_user(
    session,
    *,
    username: str,
    email: str,
    role: Role,
    password: str,
    reset_passwords: bool,
) -> User:
    user = await session.scalar(select(User).where(User.username == username))
    if user is None:
        user = User(
            username=username,
            email=email,
            role_id=role.id,
            status=USER_STATUS_ACTIVE,
            password_hash=hash_password(password),
        )
        session.add(user)
        await session.flush()
        return user
    if reset_passwords:
        user.password_hash = hash_password(password)
        user.token_version += 1
        user.role_id = role.id
        user.status = USER_STATUS_ACTIVE
    return user


async def ensure_course(session, spec: CourseSpec, teacher: User) -> Course:
    course = await session.scalar(
        select(Course).where(
            Course.teacher_id == teacher.id,
            Course.title == spec.title,
        )
    )
    if course is None:
        course = Course(
            title=spec.title,
            description=spec.description,
            teacher_id=teacher.id,
            invite_code=spec.invite_code,
            invite_enabled=True,
            status=COURSE_STATUS_APPROVED,
            submitted_at=utc_now(),
            reviewed_at=utc_now(),
            review_comment=AUTO_REVIEW_COMMENT,
        )
        session.add(course)
        await session.flush()
    return course


async def ensure_chapter(session, course: Course, title: str, order_no: int) -> Chapter:
    chapter = await session.scalar(
        select(Chapter).where(Chapter.course_id == course.id, Chapter.title == title)
    )
    if chapter is None:
        chapter = Chapter(
            course_id=course.id,
            title=title,
            description=f"{title}演示章节",
            order_no=order_no,
        )
        session.add(chapter)
        await session.flush()
    return chapter


async def ensure_knowledge(session, chapter: Chapter, name: str, difficulty: int = 2) -> Knowledge:
    knowledge = await session.scalar(
        select(Knowledge).where(
            Knowledge.chapter_id == chapter.id,
            Knowledge.name == name,
        )
    )
    if knowledge is None:
        knowledge = Knowledge(
            course_id=chapter.course_id,
            chapter_id=chapter.id,
            name=name,
            description=f"{name}演示知识点",
            difficulty=difficulty,
        )
        session.add(knowledge)
        await session.flush()
    return knowledge


def _copy_sample(sample_name: str, relative: Path) -> Path:
    source = SAMPLES / sample_name
    if not source.exists():
        raise FileNotFoundError(
            f"缺少示例文件 {source}，请先执行 python scripts/generate_samples.py"
        )
    destination = get_settings().upload_path / relative
    destination.parent.mkdir(parents=True, exist_ok=True)
    if not destination.exists():
        shutil.copy2(source, destination)
    return destination


async def ensure_course_material(
    session,
    *,
    course: Course,
    chapter: Chapter,
    knowledge: Knowledge,
    teacher: User,
    title: str,
    sample_name: str,
) -> Material:
    material = await session.scalar(
        select(Material).where(
            Material.course_id == course.id,
            Material.title == title,
            Material.scope == MATERIAL_SCOPE_COURSE,
        )
    )
    if material is not None:
        return material

    sample = SAMPLES / sample_name
    suffix = sample.suffix.lower()
    material = Material(
        scope=MATERIAL_SCOPE_COURSE,
        course_id=course.id,
        chapter_id=chapter.id,
        knowledge_id=knowledge.id,
        uploader_id=teacher.id,
        title=title,
        source_filename=sample.name,
        rag_filename="",
        file_path="",
        file_type=suffix,
        file_size=0,
        status=MATERIAL_STATUS_APPROVED,
        index_status="pending",
        review_comment=AUTO_REVIEW_COMMENT,
        reviewed_at=utc_now(),
    )
    session.add(material)
    await session.flush()

    rag_filename = f"m{material.id}__{sanitize_filename(sample.name)}"
    relative = Path("courses") / str(course.id) / rag_filename
    destination = _copy_sample(sample_name, relative)
    material.rag_filename = rag_filename
    material.file_path = relative.as_posix()
    material.file_size = destination.stat().st_size
    return material


async def ensure_enrollment(session, course: Course, student: User) -> None:
    existing = await session.scalar(
        select(CourseEnrollment).where(
            CourseEnrollment.course_id == course.id,
            CourseEnrollment.student_id == student.id,
        )
    )
    if existing is None:
        session.add(
            CourseEnrollment(
                course_id=course.id,
                student_id=student.id,
                source=ENROLLMENT_SOURCE_INVITE,
            )
        )


async def ensure_default_kb(session, student: User) -> KnowledgeBase:
    kb = await session.scalar(
        select(KnowledgeBase).where(
            KnowledgeBase.owner_id == student.id,
            KnowledgeBase.status == KB_STATUS_ACTIVE,
            KnowledgeBase.is_default.is_(True),
        )
    )
    if kb is None:
        kb = KnowledgeBase(
            owner_id=student.id,
            name="我的知识库",
            description="个人学习资料默认知识库",
            is_default=True,
            status=KB_STATUS_ACTIVE,
        )
        session.add(kb)
        await session.flush()
    return kb


async def ensure_personal_material(
    session,
    *,
    student: User,
    kb: KnowledgeBase,
    title: str,
    sample_name: str,
) -> Material:
    material = await session.scalar(
        select(Material).where(
            Material.knowledge_base_id == kb.id,
            Material.title == title,
            Material.scope == MATERIAL_SCOPE_PERSONAL,
        )
    )
    if material is not None:
        return material

    sample = SAMPLES / sample_name
    material = Material(
        scope=MATERIAL_SCOPE_PERSONAL,
        knowledge_base_id=kb.id,
        owner_id=student.id,
        uploader_id=student.id,
        title=title,
        source_filename=sample.name,
        rag_filename="",
        file_path="",
        file_type=sample.suffix.lower(),
        file_size=0,
        status=MATERIAL_STATUS_APPROVED,
        index_status="pending",
        review_comment=AUTO_REVIEW_COMMENT,
        reviewed_at=utc_now(),
    )
    session.add(material)
    await session.flush()

    rag_filename = f"m{material.id}__{sanitize_filename(sample.name)}"
    relative = Path("personal") / str(student.id) / str(kb.id) / rag_filename
    destination = _copy_sample(sample_name, relative)
    material.rag_filename = rag_filename
    material.file_path = relative.as_posix()
    material.file_size = destination.stat().st_size
    return material


async def seed_demo(*, reset_passwords: bool = False, with_rag: bool = False) -> int:
    settings = get_settings()
    password = settings.seed_demo_password
    await seed_rbac(reset_passwords=reset_passwords)

    material_ids: list[int] = []
    async with AsyncSessionLocal() as session:
        roles = {role.name: role for role in (await session.scalars(select(Role))).all()}
        users: dict[str, User] = {}
        for username, email, role_name in DEMO_ACCOUNTS:
            users[username] = await ensure_user(
                session,
                username=username,
                email=email,
                role=roles[role_name],
                password=password,
                reset_passwords=reset_passwords,
            )
        await session.flush()

        courses: dict[str, Course] = {}
        for spec in COURSES:
            course = await ensure_course(session, spec, users[spec.teacher])
            chapters: dict[str, Chapter] = {}
            for order_no, (chapter_title, knowledge_names) in enumerate(spec.chapters):
                chapter = await ensure_chapter(session, course, chapter_title, order_no)
                chapters[chapter_title] = chapter
                for knowledge_name in knowledge_names:
                    await ensure_knowledge(session, chapter, knowledge_name)
            await session.flush()

            for title, chapter_title, knowledge_name, sample_name in spec.materials:
                chapter = chapters[chapter_title]
                knowledge = await session.scalar(
                    select(Knowledge).where(
                        Knowledge.chapter_id == chapter.id,
                        Knowledge.name == knowledge_name,
                    )
                )
                assert knowledge is not None
                material = await ensure_course_material(
                    session,
                    course=course,
                    chapter=chapter,
                    knowledge=knowledge,
                    teacher=users[spec.teacher],
                    title=title,
                    sample_name=sample_name,
                )
                material_ids.append(material.id)
            courses[spec.title] = course

        for username, course_title in ENROLLMENTS:
            await ensure_enrollment(session, courses[course_title], users[username])

        for username, material_title, sample_name in PERSONAL_LIBRARIES:
            student = users[username]
            kb = await ensure_default_kb(session, student)
            material = await ensure_personal_material(
                session,
                student=student,
                kb=kb,
                title=material_title,
                sample_name=sample_name,
            )
            material_ids.append(material.id)

        await session.commit()

    print("\nDemo data seeded.")
    print("  accounts (password from SEED_DEMO_PASSWORD):")
    for username, email, role_name in DEMO_ACCOUNTS:
        print(f"    {username:10s} {role_name:8s} {email}")
    print("  courses:")
    for spec in COURSES:
        print(f"    {spec.title}  invite={spec.invite_code}  teacher={spec.teacher}")
    print("  enrollments:")
    for username, course_title in ENROLLMENTS:
        print(f"    {username} -> {course_title}")
    print("  personal libraries:")
    for username, material_title, _ in PERSONAL_LIBRARIES:
        print(f"    {username}: {material_title}")

    if not with_rag:
        print("\nRAG indexing skipped (materials stay pending). Use --with-rag to index.")
        return 0

    rag = RagClient()
    try:
        health = await rag.health()
        if health.get("status") != "ok":
            print(f"\nRAG is not ready: {health}", file=sys.stderr)
            return 2

        async with AsyncSessionLocal() as session:
            materials = list(
                await session.scalars(
                    select(Material).where(
                        Material.id.in_(material_ids),
                        Material.index_status != INDEX_STATUS_INDEXED,
                    )
                )
            )

        for material in materials:
            print(f"  indexing material {material.id}: {material.title} ...")
            await index_material(material.id, AsyncSessionLocal, rag)

        async with AsyncSessionLocal() as session:
            rows = list(
                await session.scalars(select(Material).where(Material.id.in_(material_ids)))
            )
            failed = [row for row in rows if row.index_status != INDEX_STATUS_INDEXED]
            for row in rows:
                print(f"    material {row.id}: {row.index_status}")
            if failed:
                print(f"\n{len(failed)} material(s) failed to index.", file=sys.stderr)
                return 1
        print("\nRAG indexing complete.")
        return 0
    finally:
        await rag.aclose()


def main() -> None:
    parser = argparse.ArgumentParser(description="Seed EduMate phase-one demo data")
    parser.add_argument(
        "--reset-passwords",
        action="store_true",
        help="reset demo account passwords to SEED_DEMO_PASSWORD",
    )
    parser.add_argument(
        "--with-rag",
        action="store_true",
        help="index seeded course and personal materials into the RAG service",
    )
    args = parser.parse_args()
    raise SystemExit(
        asyncio.run(
            seed_demo(
                reset_passwords=args.reset_passwords,
                with_rag=args.with_rag,
            )
        )
    )


if __name__ == "__main__":
    main()
