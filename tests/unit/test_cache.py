from __future__ import annotations

from app.core import cache


class FakeRedis:
    def __init__(self) -> None:
        self.values: dict[str, str] = {}
        self.closed = False

    async def get(self, key: str):
        return self.values.get(key)

    async def set(self, key: str, value: str, ex: int | None = None):
        self.values[key] = value
        return True

    async def aclose(self) -> None:
        self.closed = True


class BrokenRedis(FakeRedis):
    async def get(self, key: str):
        raise RuntimeError("redis down")

    async def set(self, key: str, value: str, ex: int | None = None):
        raise RuntimeError("redis down")


async def test_cache_round_trip(monkeypatch):
    client = FakeRedis()
    monkeypatch.setattr(cache, "create_cache_client", lambda: client)

    assert await cache.cache_set_json("demo", {"items": [1, 2]}, ttl=30) is True
    assert await cache.cache_get_json("demo") == {"items": [1, 2]}
    assert client.closed is True


async def test_cache_degrades_when_redis_is_down(monkeypatch):
    monkeypatch.setattr(cache, "create_cache_client", lambda: BrokenRedis())

    assert await cache.cache_get_json("demo") is None
    assert await cache.cache_set_json("demo", {"items": []}) is False


async def test_cache_is_skipped_when_disabled(monkeypatch):
    monkeypatch.setattr(cache, "create_cache_client", lambda: None)

    assert await cache.cache_get_json("demo") is None
    assert await cache.cache_set_json("demo", {"items": []}) is False
