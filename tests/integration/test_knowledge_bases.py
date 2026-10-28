"""Student personal knowledge bases and personal material indexing."""

from __future__ import annotations

import asyncio
import re

import pytest

from app.core.config import get_settings
from app.core.errors import RagError
from app.main import app
from app.services.rag_client import get_rag_client


class FakeRagClient:
    def __init__(self) -> None:
        self.ensure_calls: list[str] = []
        self.uploads: list[dict] = []
        self.deletes: list[dict] = []
        self.fail_uploads = 0
        self.fail_deletes = 0
        self._groups: dict[str, int] = {}

    async def health(self) -> dict:
        return {"status": "ok", "reachable": True, "auth_ok": True, "latency_ms": 1}

    async def ensure_group(self, name: str) -> int:
        self.ensure_calls.append(name)
        if name not in self._groups:
            self._groups[name] = 300 + len(self._groups)
        return self._groups[name]

    async def upload_document(
        self, group_id: int, *, filename: str, path, content_type: str | None = None
    ) -> dict:
        if self.fail_uploads > 0:
            self.fail_uploads -= 1
            raise RagError("模拟个人资料索引失败")
        self.uploads.append(
            {
                "group_id": group_id,
                "filename": filename,
                "size": path.stat().st_size,
                "content_type": content_type,
            }
        )
        return {"ok": True, "doc_id": 7000 + len(self.uploads)}

    async def delete_document(self, group_id: int, doc_id: int) -> bool:
        if self.fail_deletes > 0:
            self.fail_deletes -= 1
            raise RagError("模拟个人资料 RAG 删除失败")
        self.deletes.append({"by": "id", "group_id": group_id, "doc_id": doc_id})
        return True

    async def delete_document_by_name(self, group_id: int, file_name: str) -> bool:
        if self.fail_deletes > 0:
            self.fail_deletes -= 1
            raise RagError("模拟个人资料 RAG 删除失败")
        self.deletes.append({"by": "name", "group_id": group_id, "file_name": file_name})
        return True


@pytest.fixture
def fake_rag() -> FakeRagClient:
    return FakeRagClient()


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


async def default_kb(client, headers) -> dict:
    response = await client.get("/api/v1/knowledge-bases", headers=headers)
    assert response.status_code == 200, response.text
    items = response.json()["data"]["items"]
    assert items
    return items[0]


async def upload_personal(
    client,
    headers,
    kb_id: int,
    *,
    filename: str = "notes.pdf",
    content: bytes = b"%PDF-1.4 personal notes",
    title: str = "我的笔记",
):
    return await client.post(
        f"/api/v1/knowledge-bases/{kb_id}/materials",
        headers=headers,
        data={"title": title},
        files={"file": (filename, content, "application/pdf")},
    )


async def wait_for_personal_index(
    client, headers, kb_id: int, material_id: int, timeout: float = 3.0
):
    deadline = asyncio.get_running_loop().time() + timeout
    response = None
    while asyncio.get_running_loop().time() < deadline:
        response = await client.get(
            f"/api/v1/knowledge-bases/{kb_id}/materials?page_size=100",
            headers=headers,
        )
        items = response.json()["data"]["items"] if response.status_code == 200 else []
        current = next((item for item in items if item["id"] == material_id), None)
        if current and current["index_status"] in {"indexed", "failed"}:
            return current
        await asyncio.sleep(0.05)
    return response


async def test_default_knowledge_base_is_created_once(client, seeded):
    student = await auth_headers(client, "student", seeded["password"])

    first = await client.get("/api/v1/knowledge-bases", headers=student)
    second = await client.get("/api/v1/knowledge-bases", headers=student)

    assert first.status_code == 200
    assert second.status_code == 200
    assert len(first.json()["data"]["items"]) == 1
    assert len(second.json()["data"]["items"]) == 1
    kb = first.json()["data"]["items"][0]
    assert kb["name"] == "我的知识库"
    assert kb["is_default"] is True
    assert kb["material_count"] == 0

    teacher = await auth_headers(client, "teacher", seeded["password"])
    admin = await auth_headers(client, "admin", seeded["password"])
    assert (await client.get("/api/v1/knowledge-bases", headers=teacher)).status_code == 403
    assert (await client.get("/api/v1/knowledge-bases", headers=admin)).status_code == 403


async def test_create_rename_and_delete_knowledge_base(client, seeded):
    student = await auth_headers(client, "student", seeded["password"])
    default = await default_kb(client, student)

    created = await client.post(
        "/api/v1/knowledge-bases",
        headers=student,
        json={"name": "考研数学", "description": "高数与线代错题"},
    )
    assert created.status_code == 201
    kb = created.json()["data"]
    assert kb["name"] == "考研数学"
    assert kb["is_default"] is False

    duplicate = await client.post(
        "/api/v1/knowledge-bases",
        headers=student,
        json={"name": "考研数学"},
    )
    assert duplicate.status_code == 409

    renamed = await client.put(
        f"/api/v1/knowledge-bases/{kb['id']}",
        headers=student,
        json={"name": "高数错题本"},
    )
    assert renamed.status_code == 200
    assert renamed.json()["data"]["name"] == "高数错题本"

    default_delete = await client.delete(
        f"/api/v1/knowledge-bases/{default['id']}", headers=student
    )
    assert default_delete.status_code == 409

    deleted = await client.delete(f"/api/v1/knowledge-bases/{kb['id']}", headers=student)
    assert deleted.status_code == 200

    listed = await client.get("/api/v1/knowledge-bases", headers=student)
    names = [item["name"] for item in listed.json()["data"]["items"]]
    assert names == ["我的知识库"]

    admin = await auth_headers(client, "admin", seeded["password"])
    logs = await client.get("/api/v1/admin/audit-logs?keyword=knowledge_base", headers=admin)
    actions = {item["action"] for item in logs.json()["data"]["items"]}
    assert {"knowledge_base.create", "knowledge_base.update", "knowledge_base.delete"} <= actions


async def test_personal_material_indexes_privately(client, seeded, fake_rag):
    student = await auth_headers(client, "student", seeded["password"])
    kb = await default_kb(client, student)

    uploaded = await upload_personal(client, student, kb["id"])
    assert uploaded.status_code == 201, uploaded.text
    material = uploaded.json()["data"]
    assert material["scope"] == "personal"
    assert material["status"] == "approved"
    assert material["knowledge_base_id"] == kb["id"]
    assert material["knowledge_base_name"] == "我的知识库"
    assert material["course_id"] is None
    assert material["owner_id"] == seeded["users"]["student"]["id"]
    assert re.fullmatch(r"m\d+__notes\.pdf", material["rag_filename"])

    indexed = await wait_for_personal_index(client, student, kb["id"], material["id"])
    assert indexed["index_status"] == "indexed"
    assert indexed["vector_doc_id"] == "7001"
    assert fake_rag.ensure_calls == [f"edumate-kb-{kb['id']}"]
    assert fake_rag.uploads[0]["filename"] == material["rag_filename"]
    assert fake_rag.uploads[0]["group_id"] == 300

    kb_list = await client.get("/api/v1/knowledge-bases", headers=student)
    kb_row = kb_list.json()["data"]["items"][0]
    assert kb_row["material_count"] == 1
    assert kb_row["indexed_count"] == 1

    downloaded = await client.get(f"/api/v1/materials/{material['id']}/download", headers=student)
    assert downloaded.status_code == 200
    assert downloaded.content == b"%PDF-1.4 personal notes"

    other_student = await register_student(client, "kbstudent2")
    other_detail = await client.get(f"/api/v1/materials/{material['id']}", headers=other_student)
    assert other_detail.status_code == 403
    other_download = await client.get(
        f"/api/v1/materials/{material['id']}/download", headers=other_student
    )
    assert other_download.status_code == 403
    other_kb = await client.get(
        f"/api/v1/knowledge-bases/{kb['id']}/materials", headers=other_student
    )
    assert other_kb.status_code == 404

    teacher = await auth_headers(client, "teacher", seeded["password"])
    admin = await auth_headers(client, "admin", seeded["password"])
    assert (
        await client.get(f"/api/v1/materials/{material['id']}", headers=teacher)
    ).status_code == 403
    assert (
        await client.get(f"/api/v1/materials/{material['id']}", headers=admin)
    ).status_code == 403

    deleted = await client.delete(
        f"/api/v1/knowledge-bases/{kb['id']}/materials/{material['id']}",
        headers=student,
    )
    assert deleted.status_code == 200
    after_delete = await client.get(
        f"/api/v1/knowledge-bases/{kb['id']}/materials", headers=student
    )
    assert after_delete.json()["data"]["total"] == 0
    denied_download = await client.get(
        f"/api/v1/materials/{material['id']}/download", headers=student
    )
    assert denied_download.status_code == 404
    assert fake_rag.deletes == [{"by": "id", "group_id": 300, "doc_id": 7001}]


async def test_personal_index_failure_and_retry(client, seeded, fake_rag):
    student = await auth_headers(client, "student", seeded["password"])
    kb = await default_kb(client, student)

    fake_rag.fail_uploads = 1
    uploaded = await upload_personal(client, student, kb["id"], filename="retry.pdf")
    material_id = uploaded.json()["data"]["id"]

    failed = await wait_for_personal_index(client, student, kb["id"], material_id)
    assert failed["index_status"] == "failed"
    assert "模拟个人资料索引失败" in failed["index_error"]

    retried = await client.post(
        f"/api/v1/knowledge-bases/{kb['id']}/materials/{material_id}/index/retry",
        headers=student,
    )
    assert retried.status_code == 200
    indexed = await wait_for_personal_index(client, student, kb["id"], material_id)
    assert indexed["index_status"] == "indexed"
    assert indexed["index_error"] is None

    again = await client.post(
        f"/api/v1/knowledge-bases/{kb['id']}/materials/{material_id}/index/retry",
        headers=student,
    )
    assert again.status_code == 409


async def test_personal_upload_validation(client, seeded):
    student = await auth_headers(client, "student", seeded["password"])
    kb = await default_kb(client, student)

    invalid_type = await upload_personal(
        client, student, kb["id"], filename="bad.exe", content=b"x"
    )
    assert invalid_type.status_code == 422

    empty = await upload_personal(client, student, kb["id"], filename="empty.pdf", content=b"")
    assert empty.status_code == 422

    settings = get_settings()
    original = settings.max_upload_mb
    settings.max_upload_mb = 1
    try:
        too_large = await upload_personal(
            client,
            student,
            kb["id"],
            filename="large.pdf",
            content=b"x" * (1024 * 1024 + 10),
        )
        assert too_large.status_code == 422
    finally:
        settings.max_upload_mb = original


async def test_deleted_knowledge_base_hides_materials(client, seeded, fake_rag):
    student = await auth_headers(client, "student", seeded["password"])
    created = await client.post(
        "/api/v1/knowledge-bases",
        headers=student,
        json={"name": "临时知识库"},
    )
    kb = created.json()["data"]
    uploaded = await upload_personal(client, student, kb["id"], filename="temp.pdf")
    material_id = uploaded.json()["data"]["id"]
    await wait_for_personal_index(client, student, kb["id"], material_id)

    deleted = await client.delete(f"/api/v1/knowledge-bases/{kb['id']}", headers=student)
    assert deleted.status_code == 200

    missing = await client.get(f"/api/v1/knowledge-bases/{kb['id']}/materials", headers=student)
    assert missing.status_code == 404
    material = await client.get(f"/api/v1/materials/{material_id}", headers=student)
    assert material.status_code == 404
    download = await client.get(f"/api/v1/materials/{material_id}/download", headers=student)
    assert download.status_code == 404
    assert fake_rag.deletes == [{"by": "id", "group_id": 300, "doc_id": 7001}]


async def test_knowledge_base_delete_aborts_when_rag_delete_fails(client, seeded, fake_rag):
    student = await auth_headers(client, "student", seeded["password"])
    created = await client.post(
        "/api/v1/knowledge-bases",
        headers=student,
        json={"name": "RAG 删除失败知识库"},
    )
    kb = created.json()["data"]
    uploaded = await upload_personal(client, student, kb["id"], filename="keep.pdf")
    material_id = uploaded.json()["data"]["id"]
    await wait_for_personal_index(client, student, kb["id"], material_id)

    fake_rag.fail_deletes = 1
    blocked = await client.delete(f"/api/v1/knowledge-bases/{kb['id']}", headers=student)
    assert blocked.status_code == 502
    assert fake_rag.deletes == []

    listed = await client.get("/api/v1/knowledge-bases", headers=student)
    names = [item["name"] for item in listed.json()["data"]["items"]]
    assert "RAG 删除失败知识库" in names

    deleted = await client.delete(f"/api/v1/knowledge-bases/{kb['id']}", headers=student)
    assert deleted.status_code == 200
    assert fake_rag.deletes == [{"by": "id", "group_id": 300, "doc_id": 7001}]
