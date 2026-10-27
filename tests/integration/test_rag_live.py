"""Optional live RAG integration test.

Run only when the real RAG service is available and explicitly enabled:

    RUN_RAG_TESTS=1 pytest -m integration tests/integration/test_rag_live.py -q
"""

from __future__ import annotations

import os
import uuid
from pathlib import Path

import pytest

from app.core.config import get_settings
from app.services.rag_client import RagClient

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(
        os.getenv("RUN_RAG_TESTS") != "1",
        reason="set RUN_RAG_TESTS=1 to run against the real RAG service",
    ),
]

SAMPLE = Path(__file__).resolve().parents[2] / "samples" / "机器学习基础.docx"


async def test_live_rag_health_upload_and_ask():
    settings = get_settings()
    if not settings.rag_api_key:
        pytest.skip("RAG_API_KEY is not configured")
    if not SAMPLE.exists():
        pytest.skip("sample docx is missing")

    rag = RagClient(settings)
    try:
        health = await rag.health()
        assert health["status"] == "ok", health

        group_name = f"edumate-live-{uuid.uuid4().hex[:10]}"
        group_id = await rag.ensure_group(group_name)
        uploaded = await rag.upload_document(
            group_id,
            filename="live-smoke.docx",
            path=SAMPLE,
            content_type=(
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
            ),
        )
        assert uploaded.get("doc_id"), uploaded

        result = await rag.ask(
            "什么是监督学习？",
            group_ids=[group_id],
        )
        assert result.get("answer"), result
        assert isinstance(result.get("sources"), list)
    finally:
        await rag.aclose()
