"""Async client for the existing ZhiYuan RAG service (``/v1`` API)."""

from __future__ import annotations

import asyncio
import logging
import time
from pathlib import Path
from typing import Any

import httpx

from app.core.config import Settings, get_settings
from app.core.errors import RagError

logger = logging.getLogger(__name__)

HEALTH_CACHE_SECONDS = 30.0


def _retry_after(response: httpx.Response, default: float = 5.0) -> float:
    value = response.headers.get("Retry-After")
    if not value:
        return default
    try:
        return max(0.0, min(float(value), 30.0))
    except ValueError:
        return default


def _error_message(response: httpx.Response) -> str:
    try:
        body = response.json()
    except ValueError:
        return ""
    if isinstance(body, dict):
        error = body.get("error")
        if isinstance(error, dict):
            message = error.get("message")
            return str(message) if message else ""
        if body.get("detail"):
            return str(body["detail"])
    return ""


class RagClient:
    """Thin HTTP adapter with retries and a short-lived health cache."""

    def __init__(
        self,
        settings: Settings | None = None,
        *,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self.settings = settings or get_settings()
        self._transport = transport
        self._client: httpx.AsyncClient | None = None
        self._health_cache: tuple[float, dict[str, Any]] | None = None

    @property
    def configured(self) -> bool:
        return bool(self.settings.rag_api_key)

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None:
            headers = {}
            if self.settings.rag_api_key:
                headers["X-API-Key"] = self.settings.rag_api_key
            self._client = httpx.AsyncClient(
                base_url=self.settings.rag_base_url.rstrip("/"),
                headers=headers,
                transport=self._transport,
                timeout=httpx.Timeout(
                    self.settings.rag_timeout_seconds,
                    connect=self.settings.rag_connect_timeout_seconds,
                ),
            )
        return self._client

    async def aclose(self) -> None:
        if self._client is not None:
            await self._client.aclose()
            self._client = None

    def _require_key(self) -> None:
        if not self.settings.rag_api_key:
            raise RagError("RAG API Key 未配置，请先运行 scripts/register_rag_key.py")

    def _friendly_error(self, response: httpx.Response) -> RagError:
        detail = _error_message(response)
        if response.status_code == 401:
            return RagError("RAG 服务鉴权失败，请检查 API Key")
        if response.status_code == 404:
            return RagError("RAG 分组或文档不存在")
        if response.status_code == 409:
            return RagError("RAG 分组名称冲突")
        if response.status_code == 429:
            return RagError("RAG 服务繁忙，请稍后重试")
        if response.status_code >= 500:
            return RagError("RAG 服务暂时不可用，请稍后重试")
        if response.status_code == 422 and detail:
            return RagError(f"RAG 服务拒绝了请求：{detail}")
        return RagError(f"RAG 服务调用失败（HTTP {response.status_code}）")

    async def _request(
        self,
        method: str,
        path: str,
        *,
        json: dict[str, Any] | None = None,
        timeout: float | None = None,
        allowed_statuses: set[int] | None = None,
        retry_server_errors: bool = True,
    ) -> httpx.Response:
        self._require_key()
        client = await self._get_client()
        allowed = allowed_statuses or set()
        max_retries = max(0, self.settings.rag_max_retries)
        attempt = 0
        while True:
            try:
                response = await client.request(method, path, json=json, timeout=timeout)
            except httpx.TimeoutException as exc:
                raise RagError("RAG 服务响应超时，请稍后重试") from exc
            except httpx.HTTPError as exc:
                raise RagError("无法连接 RAG 服务，请确认服务已启动") from exc

            if response.status_code in allowed:
                return response
            if response.status_code == 429 and attempt < max_retries:
                attempt += 1
                await asyncio.sleep(_retry_after(response))
                continue
            if retry_server_errors and response.status_code >= 500 and attempt < max_retries:
                attempt += 1
                await asyncio.sleep(min(2**attempt, 10))
                continue
            if 200 <= response.status_code < 300:
                return response
            raise self._friendly_error(response)

    async def health(self) -> dict[str, Any]:
        now = time.monotonic()
        if self._health_cache and now - self._health_cache[0] < HEALTH_CACHE_SECONDS:
            return dict(self._health_cache[1])

        started = time.perf_counter()
        reachable = False
        auth_ok = False
        error: str | None = None
        client = await self._get_client()
        try:
            response = await client.get(
                "/healthz", timeout=self.settings.rag_health_timeout_seconds
            )
            reachable = response.status_code == 200
            if not reachable:
                error = f"健康检查返回 HTTP {response.status_code}"
        except httpx.HTTPError:
            error = "无法连接 RAG 服务"

        if reachable:
            if not self.settings.rag_api_key:
                error = "RAG API Key 未配置"
            else:
                try:
                    response = await client.get(
                        "/v1/kb/groups",
                        timeout=self.settings.rag_health_timeout_seconds,
                    )
                    auth_ok = response.status_code == 200
                    if not auth_ok:
                        error = f"API Key 校验失败（HTTP {response.status_code}）"
                except httpx.HTTPError:
                    error = "API Key 校验请求失败"

        latency_ms = int((time.perf_counter() - started) * 1000)
        result = {
            "status": "ok"
            if reachable and auth_ok
            else ("unreachable" if not reachable else "auth_failed"),
            "reachable": reachable,
            "auth_ok": auth_ok,
            "latency_ms": latency_ms,
            "base_url": self.settings.rag_base_url,
            "error": error,
        }
        self._health_cache = (now, result)
        return dict(result)

    async def list_groups(self) -> list[dict[str, Any]]:
        response = await self._request("GET", "/v1/kb/groups")
        data = response.json()
        return data if isinstance(data, list) else []

    async def ensure_group(self, name: str) -> int:
        response = await self._request(
            "POST",
            "/v1/kb/groups",
            json={"name": name},
            allowed_statuses={409},
        )
        if response.status_code == 201:
            return int(response.json()["id"])

        for group in await self.list_groups():
            if group.get("name") == name:
                return int(group["id"])
        raise RagError("RAG 分组已存在但无法读取，请稍后重试")

    async def upload_document(
        self,
        group_id: int,
        *,
        filename: str,
        path: Path,
        content_type: str | None = None,
    ) -> dict[str, Any]:
        self._require_key()
        if not path.exists():
            raise RagError("本地资料文件不存在，请重新上传")
        client = await self._get_client()
        max_retries = max(0, self.settings.rag_max_retries)
        attempt = 0
        while True:
            try:
                with path.open("rb") as handle:
                    response = await client.post(
                        f"/v1/kb/groups/{group_id}/documents",
                        files={
                            "file": (filename, handle, content_type or "application/octet-stream")
                        },
                    )
            except httpx.TimeoutException as exc:
                raise RagError("RAG 索引超时，请稍后重试") from exc
            except httpx.HTTPError as exc:
                raise RagError("无法连接 RAG 服务，请确认服务已启动") from exc

            if response.status_code == 429 and attempt < max_retries:
                attempt += 1
                await asyncio.sleep(_retry_after(response))
                continue
            if response.status_code >= 500 and attempt < max_retries:
                attempt += 1
                await asyncio.sleep(min(2**attempt, 10))
                continue
            if not (200 <= response.status_code < 300):
                raise self._friendly_error(response)

            data = response.json()
            results = data.get("results") or []
            first = results[0] if results else {}
            if not first.get("ok"):
                raise RagError(first.get("error") or "RAG 索引失败")
            if first.get("doc_id") is None:
                raise RagError("RAG 未返回文档 ID")
            return first


_rag_client: RagClient | None = None


def get_rag_client() -> RagClient:
    global _rag_client
    if _rag_client is None:
        _rag_client = RagClient()
    return _rag_client


async def close_rag_client() -> None:
    global _rag_client
    if _rag_client is not None:
        await _rag_client.aclose()
        _rag_client = None
