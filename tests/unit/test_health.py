from __future__ import annotations


async def test_liveness_returns_ok(client):
    response = await client.get("/api/v1/health/live")

    assert response.status_code == 200
    body = response.json()
    assert body["code"] == 0
    assert body["data"]["status"] == "ok"
    assert body["data"]["service"] == "EduMate"


async def test_readiness_ok(client, monkeypatch):
    from app.api.v1 import health

    async def fake_db() -> None:
        return None

    async def fake_redis() -> str:
        return "ok"

    monkeypatch.setattr(health, "check_database", fake_db)
    monkeypatch.setattr(health, "check_redis", fake_redis)

    response = await client.get("/api/v1/health/ready")

    assert response.status_code == 200
    body = response.json()
    assert body["data"]["status"] == "ok"
    assert body["data"]["checks"] == {"database": "ok", "redis": "ok"}


async def test_readiness_degrades_when_redis_down(client, monkeypatch):
    from app.api.v1 import health

    async def fake_db() -> None:
        return None

    async def fake_redis() -> str:
        return "error"

    monkeypatch.setattr(health, "check_database", fake_db)
    monkeypatch.setattr(health, "check_redis", fake_redis)

    response = await client.get("/api/v1/health/ready")

    assert response.status_code == 200
    assert response.json()["data"]["status"] == "degraded"


async def test_readiness_unavailable_when_database_down(client, monkeypatch):
    from app.api.v1 import health

    async def fake_db() -> None:
        raise RuntimeError("db down")

    async def fake_redis() -> str:
        return "ok"

    monkeypatch.setattr(health, "check_database", fake_db)
    monkeypatch.setattr(health, "check_redis", fake_redis)

    response = await client.get("/api/v1/health/ready")

    assert response.status_code == 503
    body = response.json()
    assert body["code"] == 5030
    assert body["data"]["status"] == "unavailable"
    assert body["data"]["checks"]["database"] == "error"


async def test_request_id_is_echoed_and_generated(client):
    response = await client.get("/", headers={"X-Request-ID": "trace-123"})
    assert response.headers["X-Request-ID"] == "trace-123"

    response = await client.get("/")
    assert response.headers.get("X-Request-ID")


async def test_root_uses_success_envelope(client):
    response = await client.get("/")
    body = response.json()
    assert body["code"] == 0
    assert body["message"] == "ok"
    assert body["data"]["service"] == "EduMate"
