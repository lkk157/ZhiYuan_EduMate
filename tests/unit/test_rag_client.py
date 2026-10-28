from __future__ import annotations

import httpx
import pytest

from app.core.config import Settings
from app.core.errors import RagError
from app.services.rag_client import RagClient


def make_settings(**overrides) -> Settings:
    values = {
        "rag_base_url": "http://rag.test",
        "rag_api_key": "zy_test_key",
        "rag_timeout_seconds": 5,
        "rag_connect_timeout_seconds": 1,
        "rag_health_timeout_seconds": 1,
        "rag_max_retries": 1,
    }
    values.update(overrides)
    return Settings(**values)


async def make_client(handler, **settings_overrides) -> RagClient:
    return RagClient(
        make_settings(**settings_overrides),
        transport=httpx.MockTransport(handler),
    )


async def test_ensure_group_creates_and_sends_api_key():
    seen = {}

    async def handler(request: httpx.Request) -> httpx.Response:
        seen["path"] = request.url.path
        seen["key"] = request.headers.get("X-API-Key")
        return httpx.Response(201, json={"id": 12, "name": "edumate-course-1"})

    client = await make_client(handler)
    try:
        group_id = await client.ensure_group("edumate-course-1")
    finally:
        await client.aclose()

    assert group_id == 12
    assert seen == {"path": "/v1/kb/groups", "key": "zy_test_key"}


async def test_ensure_group_reuses_existing_group_on_409():
    async def handler(request: httpx.Request) -> httpx.Response:
        if request.method == "POST":
            return httpx.Response(409, json={"error": {"code": 409, "message": "同名分组"}})
        return httpx.Response(
            200,
            json=[
                {"id": 3, "name": "other"},
                {"id": 9, "name": "edumate-course-2", "doc_count": 0},
            ],
        )

    client = await make_client(handler)
    try:
        group_id = await client.ensure_group("edumate-course-2")
    finally:
        await client.aclose()

    assert group_id == 9


async def test_upload_document_returns_doc_id(tmp_path):
    path = tmp_path / "m1__notes.pdf"
    path.write_bytes(b"%PDF-1.4 test")

    async def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/v1/kb/groups/5/documents"
        assert request.headers.get("X-API-Key") == "zy_test_key"
        return httpx.Response(
            200,
            json={
                "results": [{"ok": True, "doc_id": 77, "file_name": "m1__notes.pdf"}],
                "succeeded": 1,
                "failed": 0,
            },
        )

    client = await make_client(handler)
    try:
        result = await client.upload_document(
            5, filename="m1__notes.pdf", path=path, content_type="application/pdf"
        )
    finally:
        await client.aclose()

    assert result["doc_id"] == 77


async def test_upload_document_surfaces_rag_error_result(tmp_path):
    path = tmp_path / "bad.pdf"
    path.write_bytes(b"broken")

    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "results": [{"ok": False, "error": "解析失败"}],
                "succeeded": 0,
                "failed": 1,
            },
        )

    client = await make_client(handler)
    try:
        with pytest.raises(RagError, match="解析失败"):
            await client.upload_document(5, filename="bad.pdf", path=path)
    finally:
        await client.aclose()


async def test_delete_document_uses_group_and_doc_id():
    seen = {}

    async def handler(request: httpx.Request) -> httpx.Response:
        seen["method"] = request.method
        seen["path"] = request.url.path
        seen["key"] = request.headers.get("X-API-Key")
        return httpx.Response(200, json={"ok": True, "doc_id": 77})

    client = await make_client(handler)
    try:
        removed = await client.delete_document(5, 77)
    finally:
        await client.aclose()

    assert removed is True
    assert seen == {
        "method": "DELETE",
        "path": "/v1/kb/groups/5/documents/77",
        "key": "zy_test_key",
    }


async def test_delete_document_treats_404_as_already_deleted():
    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(404, json={"detail": "文档不存在"})

    client = await make_client(handler)
    try:
        removed = await client.delete_document(5, 77)
    finally:
        await client.aclose()

    assert removed is False


async def test_delete_document_by_name_encodes_query():
    seen = {}

    async def handler(request: httpx.Request) -> httpx.Response:
        seen["path"] = request.url.path
        seen["file_name"] = request.url.params.get("file_name")
        seen["query"] = request.url.query.decode()
        return httpx.Response(200, json={"ok": True, "doc_id": 12})

    name = "m1__第二章+A.docx"
    client = await make_client(handler)
    try:
        removed = await client.delete_document_by_name(5, name)
    finally:
        await client.aclose()

    assert removed is True
    assert seen["path"] == "/v1/kb/groups/5/documents"
    assert seen["file_name"] == name
    assert "%2B" in seen["query"]


async def test_429_is_retried_once(monkeypatch):
    attempts = {"count": 0}

    async def no_sleep(_seconds):
        return None

    monkeypatch.setattr("app.services.rag_client.asyncio.sleep", no_sleep)

    async def handler(request: httpx.Request) -> httpx.Response:
        attempts["count"] += 1
        if attempts["count"] == 1:
            return httpx.Response(429, headers={"Retry-After": "0"})
        return httpx.Response(201, json={"id": 21, "name": "course"})

    client = await make_client(handler)
    try:
        group_id = await client.ensure_group("course")
    finally:
        await client.aclose()

    assert group_id == 21
    assert attempts["count"] == 2


async def test_auth_and_connection_errors_are_normalized():
    async def unauthorized(request: httpx.Request) -> httpx.Response:
        return httpx.Response(401, json={"error": {"code": 401, "message": "bad key"}})

    client = await make_client(unauthorized)
    try:
        with pytest.raises(RagError, match="鉴权失败"):
            await client.ensure_group("course")
    finally:
        await client.aclose()

    async def boom(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("refused", request=request)

    client = await make_client(boom)
    try:
        with pytest.raises(RagError, match="无法连接"):
            await client.ensure_group("course")
    finally:
        await client.aclose()


async def test_health_reports_reachable_and_auth_status():
    async def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/healthz":
            return httpx.Response(200, json={"status": "ok"})
        return httpx.Response(200, json=[])

    client = await make_client(handler)
    try:
        health = await client.health()
    finally:
        await client.aclose()

    assert health["status"] == "ok"
    assert health["reachable"] is True
    assert health["auth_ok"] is True
    assert health["latency_ms"] >= 0


async def test_ask_returns_answer_and_sources():
    seen = {}

    async def handler(request: httpx.Request) -> httpx.Response:
        seen["path"] = request.url.path
        seen["body"] = request.content.decode()
        return httpx.Response(
            200,
            json={
                "answer": "监督学习使用带标签的数据。",
                "sources": [
                    {
                        "file_name": "m1__notes.pdf",
                        "page_no": 2,
                        "snippet": "监督学习",
                        "score": 0.9,
                    }
                ],
                "hit": True,
                "intent": "qa",
                "scope_note": None,
            },
        )

    client = await make_client(handler)
    try:
        result = await client.ask("什么是监督学习？", group_ids=[11, 22])
    finally:
        await client.aclose()

    assert result["hit"] is True
    assert result["answer"].startswith("监督学习")
    assert seen["path"] == "/v1/rag/ask"
    assert '"group_ids":[11,22]' in seen["body"]


async def test_ask_does_not_retry_server_errors(monkeypatch):
    attempts = {"count": 0}

    async def no_sleep(_seconds):
        return None

    monkeypatch.setattr("app.services.rag_client.asyncio.sleep", no_sleep)

    async def handler(request: httpx.Request) -> httpx.Response:
        attempts["count"] += 1
        return httpx.Response(502, json={"error": {"code": 502, "message": "upstream"}})

    client = await make_client(handler)
    try:
        with pytest.raises(RagError, match="暂时不可用"):
            await client.ask("问题", group_ids=[1])
    finally:
        await client.aclose()

    assert attempts["count"] == 1


async def test_missing_api_key_is_rejected():
    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=[])

    client = await make_client(handler, rag_api_key="")
    try:
        with pytest.raises(RagError, match="API Key 未配置"):
            await client.ensure_group("course")
    finally:
        await client.aclose()
