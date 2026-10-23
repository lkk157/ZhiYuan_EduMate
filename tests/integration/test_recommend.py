"""Recommendations inside enrolled courses and the student home aggregate."""

from __future__ import annotations

import pytest

from app.db.models.knowledge_base import KnowledgeBase
from app.db.models.material import Material
from app.db.models.qa import QARecord
from app.services import recommend_service


class MemoryCache:
    def __init__(self) -> None:
        self.store: dict[str, object] = {}
        self.gets: list[str] = []
        self.sets: list[str] = []


@pytest.fixture(autouse=True)
def memory_cache(monkeypatch):
    cache = MemoryCache()

    async def fake_get(key: str):
        cache.gets.append(key)
        return cache.store.get(key)

    async def fake_set(key: str, value, *, ttl: int = 60):
        cache.sets.append(key)
        cache.store[key] = value
        return True

    monkeypatch.setattr(recommend_service, "cache_get_json", fake_get)
    monkeypatch.setattr(recommend_service, "cache_set_json", fake_set)
    return cache


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


async def build_course(
    client,
    teacher: dict[str, str],
    admin: dict[str, str],
    *,
    title: str,
    chapter_titles: list[str],
) -> dict:
    created = await client.post(
        "/api/v1/courses",
        headers=teacher,
        json={"title": title, "description": f"{title} 简介"},
    )
    assert created.status_code == 201, created.text
    course_id = created.json()["data"]["id"]

    chapters = []
    for index, chapter_title in enumerate(chapter_titles):
        chapter = await client.post(
            f"/api/v1/courses/{course_id}/chapters",
            headers=teacher,
            json={"title": chapter_title, "order_no": index},
        )
        assert chapter.status_code == 201, chapter.text
        chapter_id = chapter.json()["data"]["id"]
        knowledge = await client.post(
            f"/api/v1/courses/{course_id}/chapters/{chapter_id}/knowledges",
            headers=teacher,
            json={"name": f"{chapter_title}知识点", "difficulty": 2},
        )
        assert knowledge.status_code == 201, knowledge.text
        chapters.append(
            {
                "id": chapter_id,
                "title": chapter_title,
                "knowledge_id": knowledge.json()["data"]["id"],
            }
        )

    await client.post(f"/api/v1/courses/{course_id}/submit", headers=teacher)
    approved = await client.post(
        f"/api/v1/courses/{course_id}/review",
        headers=admin,
        json={"decision": "approve"},
    )
    assert approved.status_code == 200, approved.text
    return {
        **approved.json()["data"],
        "chapters": chapters,
    }


async def add_material(
    session_factory,
    *,
    uploader_id: int,
    course_id: int,
    chapter_id: int | None,
    knowledge_id: int | None,
    title: str,
    view_count: int = 0,
    download_count: int = 0,
    status: str = "approved",
    index_status: str = "indexed",
) -> int:
    async with session_factory() as session:
        material = Material(
            scope="course",
            course_id=course_id,
            chapter_id=chapter_id,
            knowledge_id=knowledge_id,
            uploader_id=uploader_id,
            title=title,
            source_filename=f"{title}.pdf",
            rag_filename="",
            file_path=f"test/{title}.pdf",
            file_type=".pdf",
            file_size=10,
            status=status,
            index_status=index_status,
            view_count=view_count,
            download_count=download_count,
        )
        session.add(material)
        await session.flush()
        material.rag_filename = f"m{material.id}__{title}.pdf"
        await session.commit()
        return material.id


async def setup_catalogue(client, seeded, session_factory):
    teacher = await auth_headers(client, "teacher", seeded["password"])
    admin = await auth_headers(client, "admin", seeded["password"])
    student = await auth_headers(client, "student", seeded["password"])

    course_a = await build_course(
        client,
        teacher,
        admin,
        title="推荐课程 A",
        chapter_titles=["第一章 基础", "第二章 进阶"],
    )
    course_b = await build_course(
        client,
        teacher,
        admin,
        title="未加入课程 B",
        chapter_titles=["第一章 其他"],
    )

    joined = await client.post(
        "/api/v1/courses/join",
        headers=student,
        json={"invite_code": course_a["invite_code"]},
    )
    assert joined.status_code == 200, joined.text

    ch1 = course_a["chapters"][0]
    ch2 = course_a["chapters"][1]
    teacher_id = seeded["users"]["teacher"]["id"]
    ids = {
        "a1": await add_material(
            session_factory,
            uploader_id=teacher_id,
            course_id=course_a["id"],
            chapter_id=ch1["id"],
            knowledge_id=ch1["knowledge_id"],
            title="A1 监督学习讲义",
            view_count=10,
            download_count=5,
        ),
        "a2": await add_material(
            session_factory,
            uploader_id=teacher_id,
            course_id=course_a["id"],
            chapter_id=ch1["id"],
            knowledge_id=ch1["knowledge_id"],
            title="A2 监督学习练习",
            view_count=2,
        ),
        "a3": await add_material(
            session_factory,
            uploader_id=teacher_id,
            course_id=course_a["id"],
            chapter_id=ch1["id"],
            knowledge_id=ch2["knowledge_id"],
            title="A3 基础补充",
            view_count=1,
        ),
        "a4": await add_material(
            session_factory,
            uploader_id=teacher_id,
            course_id=course_a["id"],
            chapter_id=ch2["id"],
            knowledge_id=ch2["knowledge_id"],
            title="A4 进阶热门",
            view_count=80,
        ),
        "pending": await add_material(
            session_factory,
            uploader_id=teacher_id,
            course_id=course_a["id"],
            chapter_id=ch1["id"],
            knowledge_id=ch1["knowledge_id"],
            title="A5 待审核",
            view_count=999,
            status="pending",
        ),
        "not_indexed": await add_material(
            session_factory,
            uploader_id=teacher_id,
            course_id=course_a["id"],
            chapter_id=ch1["id"],
            knowledge_id=ch1["knowledge_id"],
            title="A6 未索引",
            view_count=999,
            index_status="pending",
        ),
        "b1": await add_material(
            session_factory,
            uploader_id=teacher_id,
            course_id=course_b["id"],
            chapter_id=course_b["chapters"][0]["id"],
            knowledge_id=course_b["chapters"][0]["knowledge_id"],
            title="B1 其他课程",
            view_count=1000,
        ),
    }
    return {
        "teacher": teacher,
        "admin": admin,
        "student": student,
        "course_a": course_a,
        "course_b": course_b,
        "chapters": {"ch1": ch1, "ch2": ch2},
        "materials": ids,
    }


async def test_hot_materials_only_cover_enrolled_approved_indexed(client, seeded, session_factory):
    context = await setup_catalogue(client, seeded, session_factory)
    materials = context["materials"]

    response = await client.get("/api/v1/recommendations", headers=context["student"])
    assert response.status_code == 200, response.text
    data = response.json()["data"]

    hot_ids = [item["id"] for item in data["groups"]["hot"]]
    assert hot_ids == [
        materials["a4"],
        materials["a1"],
        materials["a2"],
        materials["a3"],
    ]
    assert materials["pending"] not in hot_ids
    assert materials["not_indexed"] not in hot_ids
    assert materials["b1"] not in hot_ids
    assert data["seed"] is None
    assert data["groups"]["same_chapter"] == []
    assert data["groups"]["similar"] == []

    scores = [item["score"] for item in data["groups"]["hot"]]
    assert scores == sorted(scores, reverse=True)
    assert data["groups"]["hot"][0]["reason"].startswith("热门资料")
    assert data["groups"]["hot"][0]["kind"] == "hot"


async def test_view_creates_same_chapter_and_similar_recommendations(
    client, seeded, session_factory
):
    context = await setup_catalogue(client, seeded, session_factory)
    materials = context["materials"]

    viewed = await client.post(
        f"/api/v1/materials/{materials['a1']}/view",
        headers=context["student"],
    )
    assert viewed.status_code == 200, viewed.text
    assert viewed.json()["data"]["view_count"] == 11

    response = await client.get("/api/v1/recommendations", headers=context["student"])
    assert response.status_code == 200, response.text
    data = response.json()["data"]

    assert data["seed"]["id"] == materials["a1"]
    assert data["seed"]["chapter_title"] == "第一章 基础"
    assert data["seed"]["knowledge_name"] == "第一章 基础知识点"

    same_ids = [item["id"] for item in data["groups"]["same_chapter"]]
    similar_ids = [item["id"] for item in data["groups"]["similar"]]
    assert same_ids == [materials["a3"]]
    assert similar_ids == [materials["a2"]]
    assert "同属「第一章 基础」" in data["groups"]["same_chapter"][0]["reason"]
    assert "共享知识点「第一章 基础知识点」" in data["groups"]["similar"][0]["reason"]

    hot_ids = [item["id"] for item in data["groups"]["hot"]]
    assert materials["a1"] not in hot_ids
    assert materials["b1"] not in hot_ids

    # A second view updates the per-user seed time, not the view count only.
    second = await client.post(
        f"/api/v1/materials/{materials['a1']}/view",
        headers=context["student"],
    )
    assert second.json()["data"]["view_count"] == 12


async def test_recommendations_support_course_filter_and_explicit_seed(
    client, seeded, session_factory
):
    context = await setup_catalogue(client, seeded, session_factory)
    materials = context["materials"]

    seeded_response = await client.get(
        "/api/v1/recommendations",
        headers=context["student"],
        params={"material_id": materials["a1"]},
    )
    assert seeded_response.status_code == 200, seeded_response.text
    assert seeded_response.json()["data"]["seed"]["id"] == materials["a1"]

    filtered = await client.get(
        "/api/v1/recommendations",
        headers=context["student"],
        params={"course_id": context["course_a"]["id"]},
    )
    assert filtered.status_code == 200, filtered.text
    assert all(
        item["course_id"] == context["course_a"]["id"]
        for group in filtered.json()["data"]["groups"].values()
        for item in group
    )

    forbidden = await client.get(
        "/api/v1/recommendations",
        headers=context["student"],
        params={"course_id": context["course_b"]["id"]},
    )
    assert forbidden.status_code == 403

    forbidden_seed = await client.get(
        "/api/v1/recommendations",
        headers=context["student"],
        params={"material_id": materials["b1"]},
    )
    assert forbidden_seed.status_code == 403


async def test_new_student_gets_empty_home_and_join_guidance(client, seeded):
    student = await register_student(client, "fresh_recommend_student")

    response = await client.get("/api/v1/recommendations", headers=student)
    assert response.status_code == 200, response.text
    data = response.json()["data"]
    assert data["seed"] is None
    assert data["total"] == 0
    assert all(group == [] for group in data["groups"].values())

    home = await client.get("/api/v1/home/overview", headers=student)
    assert home.status_code == 200, home.text
    payload = home.json()["data"]
    assert payload["courses"] == []
    assert payload["hot"] == []
    assert payload["recommendations"]["seed"] is None
    assert payload["recommendations"]["same_chapter"] == []
    assert payload["recommendations"]["similar"] == []
    assert payload["recent_personal"] == []
    assert payload["stats"] == {
        "course_count": 0,
        "weekly_questions": 0,
        "recommendation_count": 0,
        "personal_material_count": 0,
        "average_mastery": None,
    }


async def test_home_aggregates_courses_hot_qa_and_personal_materials(
    client, seeded, session_factory
):
    context = await setup_catalogue(client, seeded, session_factory)
    student_id = seeded["users"]["student"]["id"]

    kb_response = await client.get("/api/v1/knowledge-bases", headers=context["student"])
    kb_id = kb_response.json()["data"]["items"][0]["id"]

    async with session_factory() as session:
        kb = await session.get(KnowledgeBase, kb_id)
        assert kb is not None
        personal = Material(
            scope="personal",
            knowledge_base_id=kb_id,
            owner_id=student_id,
            uploader_id=student_id,
            title="我的算法笔记",
            source_filename="notes.pdf",
            rag_filename="",
            file_path="test/notes.pdf",
            file_type=".pdf",
            file_size=10,
            status="approved",
            index_status="indexed",
        )
        session.add(personal)
        qa = QARecord(
            user_id=student_id,
            scope="course",
            question="什么是监督学习？",
            answer="使用带标签的数据训练模型。",
            references_json=[],
            hit=True,
            latency_ms=120,
            status="success",
        )
        session.add(qa)
        await session.flush()
        personal.rag_filename = f"m{personal.id}__notes.pdf"
        await session.commit()
        personal_id = personal.id

    home = await client.get("/api/v1/home/overview", headers=context["student"])
    assert home.status_code == 200, home.text
    data = home.json()["data"]

    assert [course["id"] for course in data["courses"]] == [context["course_a"]["id"]]
    assert data["stats"]["course_count"] == 1
    assert data["stats"]["weekly_questions"] == 1
    assert data["stats"]["personal_material_count"] == 1
    assert data["stats"]["average_mastery"] is None
    assert data["stats"]["recommendation_count"] == 4
    assert len(data["hot"]) == 4
    assert data["recommendations"]["seed"] is None
    assert [item["id"] for item in data["recent_personal"]] == [personal_id]

    await client.post(
        f"/api/v1/materials/{context['materials']['a1']}/view",
        headers=context["student"],
    )
    refreshed = await client.get("/api/v1/home/overview", headers=context["student"])
    refreshed_data = refreshed.json()["data"]
    assert refreshed_data["recommendations"]["seed"]["id"] == context["materials"]["a1"]
    # A3 appears in both hot and same_chapter, A2 in hot and similar; the
    # headline counter reports unique materials.
    assert refreshed_data["stats"]["recommendation_count"] == 3
    assert refreshed_data["stats"]["weekly_questions"] == 1


async def test_hot_materials_cache_is_reused(client, seeded, session_factory, memory_cache):
    context = await setup_catalogue(client, seeded, session_factory)

    first = await client.get("/api/v1/recommendations", headers=context["student"])
    assert first.status_code == 200, first.text
    assert len(memory_cache.gets) == 1
    assert len(memory_cache.sets) == 1

    second = await client.get("/api/v1/recommendations", headers=context["student"])
    assert second.status_code == 200, second.text
    assert len(memory_cache.gets) == 2
    assert len(memory_cache.sets) == 1
    assert second.json()["data"]["groups"]["hot"] == first.json()["data"]["groups"]["hot"]


async def test_viewing_unenrolled_material_is_forbidden(client, seeded, session_factory):
    context = await setup_catalogue(client, seeded, session_factory)
    outsider = await register_student(client, "outsider_recommend_student")

    response = await client.post(
        f"/api/v1/materials/{context['materials']['a1']}/view",
        headers=outsider,
    )
    assert response.status_code == 403

    home = await client.get("/api/v1/home/overview", headers=outsider)
    assert home.status_code == 200
    assert home.json()["data"]["stats"]["course_count"] == 0
