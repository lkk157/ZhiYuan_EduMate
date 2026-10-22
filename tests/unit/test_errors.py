from __future__ import annotations

from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from app.core.errors import register_exception_handlers, success


def build_test_app() -> FastAPI:
    app = FastAPI()
    register_exception_handlers(app)

    @app.get("/ok")
    async def ok():
        return success({"value": 1})

    @app.get("/validate")
    async def validate(limit: int):
        return {"limit": limit}

    @app.get("/boom")
    async def boom():
        raise RuntimeError("boom")

    return app


async def test_unknown_route_returns_unified_404():
    transport = ASGITransport(app=build_test_app())
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/missing")

    assert response.status_code == 404
    body = response.json()
    assert body["code"] == 1004
    assert body["message"] == "接口不存在"


async def test_validation_error_returns_unified_422():
    transport = ASGITransport(app=build_test_app())
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/validate", params={"limit": "not-an-int"})

    assert response.status_code == 422
    body = response.json()
    assert body["code"] == 1001
    assert body["data"]["errors"]


async def test_unexpected_error_returns_unified_500():
    transport = ASGITransport(app=build_test_app(), raise_app_exceptions=False)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/boom")

    assert response.status_code == 500
    body = response.json()
    assert body["code"] == 5000
    assert body["message"] == "服务内部错误"


async def test_success_envelope():
    transport = ASGITransport(app=build_test_app())
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/ok")

    assert response.status_code == 200
    assert response.json() == {"code": 0, "message": "ok", "data": {"value": 1}}
