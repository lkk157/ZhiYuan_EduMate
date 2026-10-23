"""Scoped RAG Q&A, citations and personal history."""

from __future__ import annotations

import pytest

from app.core.errors import RagError
from app.db.models.course import Course
from app.db.models.knowledge_base import KnowledgeBase
from app.db.models.material import Material
from app.main import app
from app.services.rag_client import get_rag_client


class FakeAskRag:
    def __init__(self) -> None:
        self.calls: list[dict] = []
        self.result = {
            "answer": "默认答案",
            "sources": [],
            "hit": False,
            "intent": "qa",
            "scope_note": None,
        }
        self.error: Exception | None = None

    async def ask(self, question: str, *, group_ids=None, guide_mode: bool = False):
        self.calls.append({"question": question, "group_ids": group_ids, "guide_mode": guide_mode})
        if self.error is not None:
            raise self.error
        return dict(self.result)

    async def health(self) -> dict:
        return {"status": "ok"}


@pytest.fixture
def fake_rag() -> FakeAskRag:
    return FakeAskRag()


@pytest.fixture(autouse=True)
def override_rag(fake_rag):
    app.dependency_overrides[get_rag_client] = lambda: fake_rag
    yield
    app.dependency_overrides.pop(get_rag_client, None)


async def auth_headers(client, username: str, password: str) -> dict[str, str]:
    response = await client.post(
        "/api/v1/auth/login", json={"username": username, "password": password}
    )
    assert response.status_code == 200, response.text
    return {"Authorization": f"Bearer {response.json()['data']['access_token']}"}


async def register_student(client, username: str) -> dict[str, str]:
    response = await client.post(
        "/api/v1/auth/register",
        json={
            "username": username,
            "password": "StudentPass123!",
            "password_confirm": "StudentPass123!",
        },
    )
    assert response.status_code == 201, response.text
    return {"Authorization": f"Bearer {response.json()['data']['access_token']}"}


async def setup_course_context(client, seeded, session_factory, fake_rag):
    teacher = await auth_headers(client, "teacher", seeded["password"])
    admin = await auth_headers(client, "admin", seeded["password"])
    student = await auth_headers(client, "student", seeded["password"])

    created = await client.post(
        "/api/v1/courses",
        headers=teacher,
        json={"title": "问答课程", "description": "QA test course"},
    )
    course_id = created.json()["data"]["id"]
    chapter = await client.post(
        f"/api/v1/courses/{course_id}/chapters",
        headers=teacher,
        json={"title": "第一章 绪论", "order_no": 0},
    )
    chapter_id = chapter.json()["data"]["id"]
    await client.post(f"/api/v1/courses/{course_id}/submit", headers=teacher)
    approved = await client.post(
        f"/api/v1/courses/{course_id}/review",
        headers=admin,
        json={"decision": "approve"},
    )
    course = approved.json()["data"]
    joined = await client.post(
        "/api/v1/courses/join",
        headers=student,
        json={"invite_code": course["invite_code"]},
    )
    assert joined.status_code == 200

    async with session_factory() as session:
        db_course = await session.get(Course, course_id)
        db_course.rag_group_id = 111
        material = Material(
            scope="course",
            course_id=course_id,
            chapter_id=chapter_id,
            owner_id=seeded["users"]["student"]["id"],
            uploader_id=seeded["users"]["teacher"]["id"],
            title="课程讲义",
            source_filename="lecture.pdf",
            rag_filename="",
            file_path="test/lecture.pdf",
            file_type=".pdf",
            file_size=10,
            status="approved",
            index_status="indexed",
            vector_doc_id="11",
        )
        session.add(material)
        await session.flush()
        material.rag_filename = f"m{material.id}__lecture.pdf"
        await session.commit()
        material_id = material.id

    return {
        "teacher": teacher,
        "admin": admin,
        "student": student,
        "course_id": course_id,
        "chapter_id": chapter_id,
        "material_id": material_id,
    }


async def setup_kb_context(client, seeded, session_factory, student_headers):
    listed = await client.get("/api/v1/knowledge-bases", headers=student_headers)
    kb_id = listed.json()["data"]["items"][0]["id"]
    async with session_factory() as session:
        kb = await session.get(KnowledgeBase, kb_id)
        kb.rag_group_id = 222
        material = Material(
            scope="personal",
            knowledge_base_id=kb_id,
            owner_id=seeded["users"]["student"]["id"],
            uploader_id=seeded["users"]["student"]["id"],
            title="个人笔记",
            source_filename="notes.pdf",
            rag_filename="",
            file_path="test/notes.pdf",
            file_type=".pdf",
            file_size=10,
            status="approved",
            index_status="indexed",
            vector_doc_id="22",
        )
        session.add(material)
        await session.flush()
        material.rag_filename = f"m{material.id}__notes.pdf"
        await session.commit()
        material_id = material.id
    return {"kb_id": kb_id, "material_id": material_id}


async def test_course_scope_ask_maps_citation_and_history(
    client, seeded, session_factory, fake_rag
):
    context = await setup_course_context(client, seeded, session_factory, fake_rag)
    fake_rag.result = {
        "answer": "监督学习使用带标签的数据训练模型。",
        "sources": [
            {
                "file_name": f"m{context['material_id']}__lecture.pdf",
                "page_no": 3,
                "snippet": "监督学习",
                "score": 0.88,
            }
        ],
        "hit": True,
        "intent": "qa",
        "scope_note": None,
    }

    response = await client.post(
        "/api/v1/qa/ask",
        headers=context["student"],
        json={
            "question": "什么是监督学习？",
            "scope": "course",
            "course_id": context["course_id"],
        },
    )

    assert response.status_code == 200, response.text
    data = response.json()["data"]
    assert data["status"] == "success"
    assert data["hit"] is True
    assert data["answer"].startswith("监督学习")
    assert data["course_id"] == context["course_id"]
    assert data["course_title"] == "问答课程"
    assert fake_rag.calls[0]["group_ids"] == [111]
    reference = data["references"][0]
    assert reference["material_id"] == context["material_id"]
    assert reference["title"] == "课程讲义"
    assert reference["chapter_title"] == "第一章 绪论"
    assert reference["page_no"] == 3
    assert reference["scope"] == "course"
    assert reference["course_title"] == "问答课程"

    history = await client.get("/api/v1/qa/history", headers=context["student"])
    assert history.status_code == 200
    assert history.json()["data"]["total"] == 1
    assert history.json()["data"]["items"][0]["question"] == "什么是监督学习？"

    other = await register_student(client, "qaother1")
    other_history = await client.get("/api/v1/qa/history", headers=other)
    assert other_history.json()["data"]["total"] == 0


async def test_personal_scope_owner_isolation(client, seeded, session_factory, fake_rag):
    context = await setup_course_context(client, seeded, session_factory, fake_rag)
    kb = await setup_kb_context(client, seeded, session_factory, context["student"])
    fake_rag.result = {
        "answer": "单链表插入需要先找到前驱结点，时间复杂度 O(n)。",
        "sources": [
            {
                "file_name": f"m{kb['material_id']}__notes.pdf",
                "page_no": 1,
                "snippet": "单链表插入",
                "score": 0.91,
            }
        ],
        "hit": True,
        "intent": "qa",
        "scope_note": None,
    }

    response = await client.post(
        "/api/v1/qa/ask",
        headers=context["student"],
        json={
            "question": "单链表插入的时间复杂度？",
            "scope": "personal",
            "knowledge_base_id": kb["kb_id"],
        },
    )
    assert response.status_code == 200, response.text
    data = response.json()["data"]
    assert fake_rag.calls[0]["group_ids"] == [222]
    assert data["knowledge_base_id"] == kb["kb_id"]
    assert data["references"][0]["scope"] == "personal"
    assert data["references"][0]["knowledge_base_name"] == "我的知识库"

    other = await register_student(client, "qaother2")
    other_ask = await client.post(
        "/api/v1/qa/ask",
        headers=other,
        json={
            "question": "偷看",
            "scope": "personal",
            "knowledge_base_id": kb["kb_id"],
        },
    )
    assert other_ask.status_code == 404

    admin_ask = await client.post(
        "/api/v1/qa/ask",
        headers=context["admin"],
        json={
            "question": "管理员偷看",
            "scope": "personal",
            "knowledge_base_id": kb["kb_id"],
        },
    )
    assert admin_ask.status_code == 403


async def test_all_scope_merges_course_and_kb_groups(client, seeded, session_factory, fake_rag):
    context = await setup_course_context(client, seeded, session_factory, fake_rag)
    kb = await setup_kb_context(client, seeded, session_factory, context["student"])
    fake_rag.result = {
        "answer": "综合回答",
        "sources": [],
        "hit": False,
        "intent": "qa",
        "scope_note": "同时检索课程与个人知识库",
    }

    response = await client.post(
        "/api/v1/qa/ask",
        headers=context["student"],
        json={
            "question": "综合问题",
            "scope": "all",
            "course_id": context["course_id"],
            "knowledge_base_id": kb["kb_id"],
        },
    )

    assert response.status_code == 200
    assert fake_rag.calls[0]["group_ids"] == [111, 222]
    data = response.json()["data"]
    assert data["hit"] is False
    assert data["references"] == []
    assert data["scope_note"] == "同时检索课程与个人知识库"


async def test_scope_validation_enrollment_and_readiness(client, seeded, session_factory, fake_rag):
    context = await setup_course_context(client, seeded, session_factory, fake_rag)
    unenrolled = await register_student(client, "qaunjoined")

    unenrolled_ask = await client.post(
        "/api/v1/qa/ask",
        headers=unenrolled,
        json={
            "question": "课程问题",
            "scope": "course",
            "course_id": context["course_id"],
        },
    )
    assert unenrolled_ask.status_code == 403

    missing_course = await client.post(
        "/api/v1/qa/ask",
        headers=context["student"],
        json={"question": "缺少课程", "scope": "course"},
    )
    assert missing_course.status_code == 422

    missing_kb = await client.post(
        "/api/v1/qa/ask",
        headers=context["student"],
        json={"question": "缺少知识库", "scope": "personal"},
    )
    assert missing_kb.status_code == 422

    all_without_target = await client.post(
        "/api/v1/qa/ask",
        headers=context["student"],
        json={"question": "综合但没有目标", "scope": "all"},
    )
    assert all_without_target.status_code == 422

    async with session_factory() as session:
        course = await session.get(Course, context["course_id"])
        course.rag_group_id = None
        await session.commit()
    not_ready = await client.post(
        "/api/v1/qa/ask",
        headers=context["student"],
        json={
            "question": "未就绪",
            "scope": "course",
            "course_id": context["course_id"],
        },
    )
    assert not_ready.status_code == 409

    kb_list = await client.get("/api/v1/knowledge-bases", headers=context["student"])
    kb_id = kb_list.json()["data"]["items"][0]["id"]
    kb_not_ready = await client.post(
        "/api/v1/qa/ask",
        headers=context["student"],
        json={
            "question": "知识库未就绪",
            "scope": "personal",
            "knowledge_base_id": kb_id,
        },
    )
    assert kb_not_ready.status_code == 409
    assert fake_rag.calls == []


async def test_degraded_answer_is_recorded(client, seeded, session_factory, fake_rag):
    context = await setup_course_context(client, seeded, session_factory, fake_rag)
    fake_rag.error = RagError("模拟超时")

    response = await client.post(
        "/api/v1/qa/ask",
        headers=context["student"],
        json={
            "question": "服务故障时的问题",
            "scope": "course",
            "course_id": context["course_id"],
        },
    )

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["status"] == "degraded"
    assert data["hit"] is False
    assert data["references"] == []
    assert "暂时不可用" in data["answer"]
    history = await client.get("/api/v1/qa/history", headers=context["student"])
    assert history.json()["data"]["items"][0]["status"] == "degraded"


async def test_history_filters(client, seeded, session_factory, fake_rag):
    context = await setup_course_context(client, seeded, session_factory, fake_rag)
    kb = await setup_kb_context(client, seeded, session_factory, context["student"])

    for payload in (
        {"question": "课程问题", "scope": "course", "course_id": context["course_id"]},
        {
            "question": "个人问题",
            "scope": "personal",
            "knowledge_base_id": kb["kb_id"],
        },
    ):
        response = await client.post("/api/v1/qa/ask", headers=context["student"], json=payload)
        assert response.status_code == 200

    by_course = await client.get(
        "/api/v1/qa/history",
        headers=context["student"],
        params={"course_id": context["course_id"]},
    )
    assert by_course.json()["data"]["total"] == 1

    by_kb = await client.get(
        "/api/v1/qa/history",
        headers=context["student"],
        params={"knowledge_base_id": kb["kb_id"]},
    )
    assert by_kb.json()["data"]["total"] == 1
    assert by_kb.json()["data"]["items"][0]["question"] == "个人问题"

    by_scope = await client.get(
        "/api/v1/qa/history", headers=context["student"], params={"scope": "personal"}
    )
    assert by_scope.json()["data"]["total"] == 1

    paged = await client.get(
        "/api/v1/qa/history",
        headers=context["student"],
        params={"page": 1, "page_size": 1},
    )
    assert len(paged.json()["data"]["items"]) == 1
    assert paged.json()["data"]["total"] == 2
