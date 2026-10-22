from __future__ import annotations

import os

import pytest
from httpx import ASGITransport, AsyncClient

os.environ.setdefault("APP_ENV", "test")
os.environ.setdefault("SECRET_KEY", "test-secret-key-with-more-than-32-characters")

from app.main import app  # noqa: E402


@pytest.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        yield client
