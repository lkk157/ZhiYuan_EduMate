"""Material upload, review, RAG indexing, download and soft deletion."""

from __future__ import annotations

import asyncio
import re

import pytest
from sqlalchemy import select

from app.core.config import get_settings
from app.core.errors import RagError
from app.db.models.course import Course
from app.db.models.material import Material
from app.main import app
from app.services.rag_client import get_rag_client


class FakeRagClient:
    def __init__(self) -> None:
        self.ensure_calls: list[str] = []
        self.uploads: list[dict] = []
        self.fail_uploads = 0
        self._groups: dict[str, int] = {}

    async def health(self) -> dict:
        return {
            "status": "ok",
            "reachable": True,
            "auth_ok": True,
            "latency_ms": 1,
            "base_url": "http://fake-rag",
            "error": None,
        }

    async def ensure_group(self, name: str) -> int:
        self.ensure_calls.append(name)
        if name not in self._groups:
            self._groups[name] = 100 + len(self._groups)
        return self._groups[name]

    async def upload_document(
        self, group_id: int, *, filename: str, path, content_type: str | None = None
    ) -> dict:
        if self.fail_uploads > 0:
            self.fail_uploads -= 1
            raise RagError("模拟索引失败")
        self.uploads.append(
            {
                "group_id": group_id,
                "filename": filename,
                "path": str(path),
                "content_type": content_type,
                "size": path.stat().st_size,
            }
        )
        return {"ok": True, "doc_id": 9000 + len(self.uploads)}


@pytest.fixture
def fake_rag() -> FakeRagClient:
    return FakeRagClient()


@pytest.fixture(autouse=True)
def override_rag(fake_rag):
    app.dependency_overrides[get_rag_client] = lambda: fake_rag
    yield
    app.dependency_overrides.pop(get_rag_client, None)


async def login(client, username: str, password: str):
    return await client.post(
        "/api/v1/auth/login", json={"username": username, "password": password}
    )


async def auth_headers(client, username: str, password: str) -> dict[str, str]:
    response = await login(client, username, password)
    assert response.status_code == 200, response.text
    return {"Authorization": f"Bearer {response.json()['data']['access_token']}"}


async def create_second_teacher(client, admin_headers, username="material_teacher"):
    response = await client.post(
        "/api/v1/admin/users",
        headers=admin_headers,
        json={
            "username": username,
            "password": "TeacherPass123!",
            "email": f"{username}@example.com",
            "role": "teacher",
        },
    )
    assert response.status_code == 201, response.text
    return await auth_headers(client, username, "TeacherPass123!")


async def build_approved_course(client, teacher, admin, title="资料课程"):
    created = await client.post(
        "/api/v1/courses",
        headers=teacher,
        json={"title": title, "description": "material test course"},
    )
    assert created.status_code == 201, created.text
    course_id = created.json()["data"]["id"]
    chapter = await client.post(
        f"/api/v1/courses/{course_id}/chapters",
        headers=teacher,
        json={"title": "第一章", "order_no": 0},
    )
    assert chapter.status_code == 201, chapter.text
    chapter_id = chapter.json()["data"]["id"]
    knowledge = await client.post(
        f"/api/v1/courses/{course_id}/chapters/{chapter_id}/knowledges",
        headers=teacher,
        json={"name": "监督学习", "difficulty": 2},
    )
    assert knowledge.status_code == 201, knowledge.text
    knowledge_id = knowledge.json()["data"]["id"]
    await client.post(f"/api/v1/courses/{course_id}/submit", headers=teacher)
    approved = await client.post(
        f"/api/v1/courses/{course_id}/review",
        headers=admin,
        json={"decision": "approve"},
    )
    assert approved.status_code == 200, approved.text
    return approved.json()["data"], chapter_id, knowledge_id


async def upload_material(
    client,
    headers,
    course_id: int,
    *,
    filename: str = "notes.pdf",
    content: bytes = b"%PDF-1.4 material content",
    title: str = "第一章讲义",
    chapter_id: int | None = None,
    knowledge_id: int | None = None,
    content_type: str = "application/pdf",
):
    data = {"course_id": str(course_id), "title": title}
    if chapter_id is not None:
        data["chapter_id"] = str(chapter_id)
    if knowledge_id is not None:
        data["knowledge_id"] = str(knowledge_id)
    return await client.post(
        "/api/v1/materials",
        headers=headers,
        data=data,
        files={"file": (filename, content, content_type)},
    )


async def upload_batch(
    client,
    headers,
    course_id: int,
    filenames: list[str],
    *,
    chapter_id: int | None = None,
    title: str | None = None,
    content: bytes = b"%PDF-1.4 batch content",
):
    data = {"course_id": str(course_id)}
    if chapter_id is not None:
        data["chapter_id"] = str(chapter_id)
    if title is not None:
        data["title"] = title
    files = []
    for name in filenames:
        content_type = (
            "application/pdf" if name.lower().endswith(".pdf") else "application/octet-stream"
        )
        files.append(("files", (name, content, content_type)))
    return await client.post("/api/v1/materials/batch", headers=headers, data=data, files=files)


async def wait_for_index(client, headers, material_id: int, timeout: float = 3.0):
    deadline = asyncio.get_running_loop().time() + timeout
    response = None
    while asyncio.get_running_loop().time() < deadline:
        response = await client.get(f"/api/v1/materials/{material_id}", headers=headers)
        if response.json()["data"]["index_status"] in {"indexed", "failed"}:
            return response
        await asyncio.sleep(0.05)
    return response


async def test_upload_approve_and_student_access(client, seeded, fake_rag, session_factory):
    teacher = await auth_headers(client, "teacher", seeded["password"])
    admin = await auth_headers(client, "admin", seeded["password"])
    student = await auth_headers(client, "student", seeded["password"])
    course, chapter_id, knowledge_id = await build_approved_course(client, teacher, admin)

    uploaded = await upload_material(
        client,
        teacher,
        course["id"],
        chapter_id=chapter_id,
        knowledge_id=knowledge_id,
    )
    assert uploaded.status_code == 201, uploaded.text
    material = uploaded.json()["data"]
    assert material["status"] == "pending"
    assert material["index_status"] == "pending"
    assert re.fullmatch(r"m\d+__notes\.pdf", material["rag_filename"])
    assert material["file_size"] == len(b"%PDF-1.4 material content")
    assert material["chapter_id"] == chapter_id
    material_id = material["id"]

    student_before = await client.get(
        f"/api/v1/materials?course_id={course['id']}", headers=student
    )
    assert student_before.status_code == 403
    student_all = await client.get("/api/v1/materials", headers=student)
    assert student_all.json()["data"]["total"] == 0

    student_review = await client.post(
        f"/api/v1/materials/{material_id}/review",
        headers=student,
        json={"decision": "approve"},
    )
    assert student_review.status_code == 403

    pending_list = await client.get("/api/v1/materials?status=pending", headers=admin)
    assert pending_list.status_code == 200
    assert pending_list.json()["data"]["total"] == 1
    assert pending_list.json()["data"]["items"][0]["rag_filename"].startswith(f"m{material_id}__")

    approved = await client.post(
        f"/api/v1/materials/{material_id}/review",
        headers=admin,
        json={"decision": "approve", "comment": "内容合格"},
    )
    assert approved.status_code == 200
    assert approved.json()["data"]["status"] == "approved"

    indexed = await wait_for_index(client, admin, material_id)
    assert indexed.json()["data"]["index_status"] == "indexed"
    assert indexed.json()["data"]["vector_doc_id"] == "9001"
    assert fake_rag.ensure_calls == [f"edumate-course-{course['id']}"]
    assert len(fake_rag.uploads) == 1
    assert fake_rag.uploads[0]["filename"] == f"m{material_id}__notes.pdf"
    assert fake_rag.uploads[0]["size"] == len(b"%PDF-1.4 material content")

    async with session_factory() as session:
        db_course = await session.scalar(select(Course).where(Course.id == course["id"]))
        assert db_course.rag_group_id == 100

    await client.post(
        "/api/v1/courses/join",
        headers=student,
        json={"invite_code": course["invite_code"]},
    )

    listed = await client.get(f"/api/v1/materials?course_id={course['id']}", headers=student)
    assert listed.status_code == 200
    assert listed.json()["data"]["total"] == 1
    item = listed.json()["data"]["items"][0]
    assert item["title"] == "第一章讲义"
    assert item["course_title"] == "资料课程"
    assert item["chapter_title"] == "第一章"
    assert "index_error" not in item
    assert "rag_filename" not in item

    downloaded = await client.get(f"/api/v1/materials/{material_id}/download", headers=student)
    assert downloaded.status_code == 200
    assert downloaded.content == b"%PDF-1.4 material content"

    after_download = await client.get(f"/api/v1/materials/{material_id}", headers=teacher)
    assert after_download.json()["data"]["download_count"] == 1


async def test_reject_requires_comment_and_hides_from_students(client, seeded, fake_rag):
    teacher = await auth_headers(client, "teacher", seeded["password"])
    admin = await auth_headers(client, "admin", seeded["password"])
    student = await auth_headers(client, "student", seeded["password"])
    course, chapter_id, _ = await build_approved_course(client, teacher, admin, "驳回课程")

    uploaded = await upload_material(
        client, teacher, course["id"], chapter_id=chapter_id, title="待驳回资料"
    )
    material_id = uploaded.json()["data"]["id"]

    missing_comment = await client.post(
        f"/api/v1/materials/{material_id}/review",
        headers=admin,
        json={"decision": "reject"},
    )
    assert missing_comment.status_code == 422

    rejected = await client.post(
        f"/api/v1/materials/{material_id}/review",
        headers=admin,
        json={"decision": "reject", "comment": "内容不完整"},
    )
    assert rejected.status_code == 200
    assert rejected.json()["data"]["status"] == "rejected"
    assert rejected.json()["data"]["review_comment"] == "内容不完整"
    assert fake_rag.uploads == []

    await client.post(
        "/api/v1/courses/join",
        headers=student,
        json={"invite_code": course["invite_code"]},
    )
    student_list = await client.get(f"/api/v1/materials?course_id={course['id']}", headers=student)
    assert student_list.json()["data"]["total"] == 0

    teacher_list = await client.get(f"/api/v1/materials?course_id={course['id']}", headers=teacher)
    assert teacher_list.json()["data"]["total"] == 1
    assert teacher_list.json()["data"]["items"][0]["status"] == "rejected"


async def test_course_group_is_created_once_for_multiple_materials(client, seeded, fake_rag):
    teacher = await auth_headers(client, "teacher", seeded["password"])
    admin = await auth_headers(client, "admin", seeded["password"])
    course, chapter_id, _ = await build_approved_course(client, teacher, admin, "分组课程")

    material_ids = []
    for index in range(2):
        uploaded = await upload_material(
            client,
            teacher,
            course["id"],
            filename=f"lesson-{index}.pdf",
            content=f"content-{index}".encode(),
            title=f"资料 {index}",
            chapter_id=chapter_id,
        )
        material_id = uploaded.json()["data"]["id"]
        material_ids.append(material_id)
        approved = await client.post(
            f"/api/v1/materials/{material_id}/review",
            headers=admin,
            json={"decision": "approve"},
        )
        assert approved.status_code == 200
        indexed = await wait_for_index(client, admin, material_id)
        assert indexed.json()["data"]["index_status"] == "indexed"

    assert fake_rag.ensure_calls == [f"edumate-course-{course['id']}"]
    assert len(fake_rag.uploads) == 2
    assert {item["group_id"] for item in fake_rag.uploads} == {100}


async def test_index_failure_and_retry(client, seeded, fake_rag):
    teacher = await auth_headers(client, "teacher", seeded["password"])
    admin = await auth_headers(client, "admin", seeded["password"])
    student = await auth_headers(client, "student", seeded["password"])
    course, _, _ = await build_approved_course(client, teacher, admin, "重试课程")

    fake_rag.fail_uploads = 1
    uploaded = await upload_material(client, teacher, course["id"], title="索引失败资料")
    material_id = uploaded.json()["data"]["id"]
    await client.post(
        f"/api/v1/materials/{material_id}/review",
        headers=admin,
        json={"decision": "approve"},
    )

    failed = await wait_for_index(client, teacher, material_id)
    assert failed.json()["data"]["index_status"] == "failed"
    assert "模拟索引失败" in failed.json()["data"]["index_error"]

    denied = await client.post(f"/api/v1/materials/{material_id}/index/retry", headers=student)
    assert denied.status_code == 403

    retried = await client.post(f"/api/v1/materials/{material_id}/index/retry", headers=teacher)
    assert retried.status_code == 200
    indexed = await wait_for_index(client, teacher, material_id)
    assert indexed.json()["data"]["index_status"] == "indexed"
    assert indexed.json()["data"]["index_error"] is None

    again = await client.post(f"/api/v1/materials/{material_id}/index/retry", headers=teacher)
    assert again.status_code == 409


async def test_upload_validation_and_course_permissions(client, seeded, fake_rag):
    teacher = await auth_headers(client, "teacher", seeded["password"])
    admin = await auth_headers(client, "admin", seeded["password"])
    student = await auth_headers(client, "student", seeded["password"])
    course, chapter_id, _ = await build_approved_course(client, teacher, admin, "校验课程")

    invalid_type = await upload_material(
        client, teacher, course["id"], filename="virus.exe", content=b"x"
    )
    assert invalid_type.status_code == 422

    empty = await upload_material(client, teacher, course["id"], filename="empty.pdf", content=b"")
    assert empty.status_code == 422

    student_upload = await upload_material(client, student, course["id"], filename="student.pdf")
    assert student_upload.status_code == 403

    other_teacher = await create_second_teacher(client, admin)
    other_upload = await upload_material(client, other_teacher, course["id"], filename="other.pdf")
    assert other_upload.status_code == 403

    draft = await client.post(
        "/api/v1/courses",
        headers=teacher,
        json={"title": "未发布课程"},
    )
    draft_id = draft.json()["data"]["id"]
    not_approved = await upload_material(client, teacher, draft_id, filename="draft.pdf")
    assert not_approved.status_code == 409

    draft_chapter = await client.post(
        f"/api/v1/courses/{draft_id}/chapters",
        headers=teacher,
        json={"title": "其他章节"},
    )
    wrong_chapter = await upload_material(
        client,
        teacher,
        course["id"],
        filename="wrong-chapter.pdf",
        chapter_id=draft_chapter.json()["data"]["id"],
    )
    assert wrong_chapter.status_code == 422
    assert chapter_id > 0


async def test_upload_size_limit(client, seeded, monkeypatch):
    teacher = await auth_headers(client, "teacher", seeded["password"])
    admin = await auth_headers(client, "admin", seeded["password"])
    course, _, _ = await build_approved_course(client, teacher, admin, "大小限制课程")

    monkeypatch.setattr(get_settings(), "max_upload_mb", 1)
    too_large = await upload_material(
        client,
        teacher,
        course["id"],
        filename="large.pdf",
        content=b"x" * (1024 * 1024 + 10),
    )
    assert too_large.status_code == 422
    assert "1MB" in too_large.json()["message"]


async def test_soft_delete_hides_material_and_blocks_download(
    client, seeded, fake_rag, session_factory
):
    teacher = await auth_headers(client, "teacher", seeded["password"])
    admin = await auth_headers(client, "admin", seeded["password"])
    student = await auth_headers(client, "student", seeded["password"])
    course, _, _ = await build_approved_course(client, teacher, admin, "删除课程")

    uploaded = await upload_material(client, teacher, course["id"], title="待删除资料")
    material_id = uploaded.json()["data"]["id"]
    await client.post(
        f"/api/v1/materials/{material_id}/review",
        headers=admin,
        json={"decision": "approve"},
    )
    await wait_for_index(client, admin, material_id)
    await client.post(
        "/api/v1/courses/join",
        headers=student,
        json={"invite_code": course["invite_code"]},
    )

    deleted = await client.delete(f"/api/v1/materials/{material_id}", headers=teacher)
    assert deleted.status_code == 200

    student_list = await client.get(f"/api/v1/materials?course_id={course['id']}", headers=student)
    assert student_list.json()["data"]["total"] == 0
    denied = await client.get(f"/api/v1/materials/{material_id}/download", headers=student)
    assert denied.status_code == 404

    admin_deleted = await client.get("/api/v1/materials?status=deleted", headers=admin)
    assert admin_deleted.json()["data"]["total"] == 1

    async with session_factory() as session:
        row = await session.scalar(select(Material).where(Material.id == material_id))
        assert row.status == "deleted"

    logs = await client.get("/api/v1/admin/audit-logs?action=material.delete", headers=admin)
    assert logs.json()["data"]["total"] == 1


async def test_material_access_guards_and_rag_health(client, seeded, fake_rag):
    teacher = await auth_headers(client, "teacher", seeded["password"])
    admin = await auth_headers(client, "admin", seeded["password"])
    student = await auth_headers(client, "student", seeded["password"])
    course, _, _ = await build_approved_course(client, teacher, admin, "访问课程")

    uploaded = await upload_material(client, teacher, course["id"], title="待审核资料")
    material_id = uploaded.json()["data"]["id"]

    unenrolled = await client.get(f"/api/v1/materials/{material_id}", headers=student)
    assert unenrolled.status_code == 403

    other_teacher = await create_second_teacher(client, admin, username="material_teacher2")
    forbidden = await client.get(f"/api/v1/materials/{material_id}", headers=other_teacher)
    assert forbidden.status_code == 403
    forbidden_list = await client.get(
        f"/api/v1/materials?course_id={course['id']}", headers=other_teacher
    )
    assert forbidden_list.status_code == 403

    health = await client.get("/api/v1/materials/rag-health", headers=student)
    assert health.status_code == 200
    assert health.json()["data"]["status"] == "ok"
    assert health.json()["data"]["auth_ok"] is True


async def test_batch_upload_creates_multiple_materials(client, seeded):
    teacher = await auth_headers(client, "teacher", seeded["password"])
    admin = await auth_headers(client, "admin", seeded["password"])
    student = await auth_headers(client, "student", seeded["password"])
    course, chapter_id, _ = await build_approved_course(client, teacher, admin, "批量上传课程")

    batch = await upload_batch(
        client,
        teacher,
        course["id"],
        ["lesson-1.pdf", "lesson-2.pdf", "lesson-3.pdf"],
        chapter_id=chapter_id,
    )
    assert batch.status_code == 201, batch.text
    data = batch.json()["data"]
    assert data["succeeded"] == 3
    assert data["failed"] == 0
    assert len(data["items"]) == 3
    assert {item["title"] for item in data["items"]} == {
        "lesson-1",
        "lesson-2",
        "lesson-3",
    }
    assert all(item["status"] == "pending" for item in data["items"])
    assert all(item["chapter_id"] == chapter_id for item in data["items"])
    assert len({item["rag_filename"] for item in data["items"]}) == 3

    listed = await client.get(f"/api/v1/materials?course_id={course['id']}", headers=teacher)
    assert listed.json()["data"]["total"] == 3

    logs = await client.get(
        "/api/v1/admin/audit-logs?action=material.upload&page_size=100", headers=admin
    )
    assert logs.json()["data"]["total"] == 3

    student_batch = await upload_batch(client, student, course["id"], ["student-1.pdf"])
    assert student_batch.status_code == 403


async def test_batch_upload_rejects_invalid_type_and_too_many_files(client, seeded):
    teacher = await auth_headers(client, "teacher", seeded["password"])
    admin = await auth_headers(client, "admin", seeded["password"])
    course, _, _ = await build_approved_course(client, teacher, admin, "批量校验课程")

    invalid = await upload_batch(client, teacher, course["id"], ["good.pdf", "bad.exe"])
    assert invalid.status_code == 422
    assert invalid.json()["code"] == 1001
    errors = invalid.json()["data"]["errors"]
    assert errors == [{"filename": "bad.exe", "message": "不支持的文件类型"}]

    listed = await client.get(f"/api/v1/materials?course_id={course['id']}", headers=teacher)
    assert listed.json()["data"]["total"] == 0

    too_many = await upload_batch(
        client, teacher, course["id"], [f"file-{index}.pdf" for index in range(11)]
    )
    assert too_many.status_code == 422

    empty_title_batch = await upload_batch(
        client, teacher, course["id"], ["single.pdf"], title="批量单文件标题"
    )
    assert empty_title_batch.status_code == 201
    assert empty_title_batch.json()["data"]["items"][0]["title"] == "批量单文件标题"


async def test_teacher_can_map_material_to_chapter(client, seeded, fake_rag):
    teacher = await auth_headers(client, "teacher", seeded["password"])
    admin = await auth_headers(client, "admin", seeded["password"])
    student = await auth_headers(client, "student", seeded["password"])
    course, chapter_id, knowledge_id = await build_approved_course(
        client, teacher, admin, "资料映射课程"
    )

    uploaded = await upload_material(
        client, teacher, course["id"], title="待映射资料", filename="mapping.pdf"
    )
    assert uploaded.status_code == 201, uploaded.text
    material_id = uploaded.json()["data"]["id"]
    assert uploaded.json()["data"]["chapter_id"] is None

    denied = await client.put(
        f"/api/v1/materials/{material_id}/mapping",
        headers=student,
        json={"chapter_id": chapter_id},
    )
    assert denied.status_code == 403

    other_teacher = await create_second_teacher(client, admin, username="mapping_teacher")
    other_denied = await client.put(
        f"/api/v1/materials/{material_id}/mapping",
        headers=other_teacher,
        json={"chapter_id": chapter_id},
    )
    assert other_denied.status_code == 403

    knowledge_without_chapter = await client.put(
        f"/api/v1/materials/{material_id}/mapping",
        headers=teacher,
        json={"knowledge_id": knowledge_id},
    )
    assert knowledge_without_chapter.status_code == 422

    invalid_chapter = await client.put(
        f"/api/v1/materials/{material_id}/mapping",
        headers=teacher,
        json={"chapter_id": 99999},
    )
    assert invalid_chapter.status_code == 422

    mapped = await client.put(
        f"/api/v1/materials/{material_id}/mapping",
        headers=teacher,
        json={"chapter_id": chapter_id, "knowledge_id": knowledge_id},
    )
    assert mapped.status_code == 200, mapped.text
    assert mapped.json()["data"]["chapter_id"] == chapter_id
    assert mapped.json()["data"]["knowledge_id"] == knowledge_id
    assert mapped.json()["data"]["chapter_title"] == "第一章"
    assert mapped.json()["data"]["knowledge_title"] == "监督学习"

    _, other_chapter_id, _ = await build_approved_course(client, teacher, admin, "其他映射课程")
    mismatch = await client.put(
        f"/api/v1/materials/{material_id}/mapping",
        headers=teacher,
        json={"chapter_id": other_chapter_id},
    )
    assert mismatch.status_code == 422

    cleared = await client.put(
        f"/api/v1/materials/{material_id}/mapping",
        headers=teacher,
        json={"chapter_id": None, "knowledge_id": None},
    )
    assert cleared.status_code == 200
    assert cleared.json()["data"]["chapter_id"] is None
    assert cleared.json()["data"]["knowledge_id"] is None

    await client.post(
        f"/api/v1/materials/{material_id}/review",
        headers=admin,
        json={"decision": "approve"},
    )
    await wait_for_index(client, admin, material_id)
    await client.post(
        "/api/v1/courses/join",
        headers=student,
        json={"invite_code": course["invite_code"]},
    )

    await client.put(
        f"/api/v1/materials/{material_id}/mapping",
        headers=teacher,
        json={"chapter_id": chapter_id},
    )
    filtered = await client.get(
        f"/api/v1/materials?course_id={course['id']}&chapter_id={chapter_id}",
        headers=student,
    )
    assert filtered.status_code == 200
    assert [item["id"] for item in filtered.json()["data"]["items"]] == [material_id]


async def test_list_materials_filters_by_chapter_for_students(
    client, seeded, fake_rag, session_factory
):
    teacher = await auth_headers(client, "teacher", seeded["password"])
    admin = await auth_headers(client, "admin", seeded["password"])
    student = await auth_headers(client, "student", seeded["password"])
    course, chapter_id, knowledge_id = await build_approved_course(
        client, teacher, admin, "章节资料课程"
    )

    uploaded = await upload_material(
        client,
        teacher,
        course["id"],
        chapter_id=chapter_id,
        knowledge_id=knowledge_id,
        title="章节内资料",
    )
    material_id = uploaded.json()["data"]["id"]
    await client.post(
        f"/api/v1/materials/{material_id}/review",
        headers=admin,
        json={"decision": "approve"},
    )
    await wait_for_index(client, admin, material_id)

    before_join = await client.get(
        f"/api/v1/materials?course_id={course['id']}&chapter_id={chapter_id}",
        headers=student,
    )
    assert before_join.status_code == 403

    await client.post(
        "/api/v1/courses/join",
        headers=student,
        json={"invite_code": course["invite_code"]},
    )

    filtered = await client.get(
        f"/api/v1/materials?course_id={course['id']}&chapter_id={chapter_id}",
        headers=student,
    )
    assert filtered.status_code == 200
    assert filtered.json()["data"]["total"] == 1
    assert filtered.json()["data"]["items"][0]["chapter_id"] == chapter_id

    empty = await client.get(
        f"/api/v1/materials?course_id={course['id']}&chapter_id={chapter_id + 9999}",
        headers=student,
    )
    assert empty.status_code == 404

    _, other_chapter_id, _ = await build_approved_course(client, teacher, admin, "另一门课程")
    mismatched = await client.get(
        f"/api/v1/materials?course_id={course['id']}&chapter_id={other_chapter_id}",
        headers=student,
    )
    assert mismatched.status_code == 404
