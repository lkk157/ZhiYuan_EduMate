"""Unified error contract and FastAPI exception handlers.

Success envelope: ``{"code": 0, "message": "ok", "data": ...}``
Error envelope:   ``{"code": <business code>, "message": "...", "data": ...}``

HTTP status codes keep their standard meaning; the business ``code`` adds a
stable machine-readable identifier for frontend handling.
"""

from __future__ import annotations

import logging
from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

logger = logging.getLogger(__name__)


class AppError(Exception):
    """Base class for expected application errors."""

    code: int = 5000
    http_status: int = 500
    default_message: str = "服务内部错误"

    def __init__(
        self,
        message: str | None = None,
        *,
        code: int | None = None,
        http_status: int | None = None,
        data: Any = None,
    ) -> None:
        self.message = message or self.default_message
        self.code = code if code is not None else self.code
        self.http_status = http_status if http_status is not None else self.http_status
        self.data = data
        super().__init__(self.message)


class ValidationError(AppError):
    code = 1001
    http_status = 422
    default_message = "参数校验失败"


class AuthError(AppError):
    code = 1002
    http_status = 401
    default_message = "未认证或登录已过期"


class ForbiddenError(AppError):
    code = 1003
    http_status = 403
    default_message = "无权访问该资源"


class NotFoundError(AppError):
    code = 1004
    http_status = 404
    default_message = "资源不存在"


class ConflictError(AppError):
    code = 1005
    http_status = 409
    default_message = "资源状态冲突"


class RagError(AppError):
    code = 2001
    http_status = 502
    default_message = "智能问答服务暂时不可用"


class ServiceUnavailableError(AppError):
    code = 5030
    http_status = 503
    default_message = "服务暂时不可用，请稍后重试"


def envelope(data: Any = None, *, code: int = 0, message: str = "ok") -> dict[str, Any]:
    return {"code": code, "message": message, "data": data}


def success(data: Any = None, message: str = "ok") -> dict[str, Any]:
    return envelope(data, code=0, message=message)


def _error_content(code: int, message: str, data: Any = None) -> dict[str, Any]:
    return {"code": code, "message": message, "data": data}


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def handle_app_error(request: Request, exc: AppError) -> JSONResponse:
        if exc.http_status >= 500:
            logger.error("application error: %s", exc.message, exc_info=exc)
        return JSONResponse(
            status_code=exc.http_status,
            content=_error_content(exc.code, exc.message, exc.data),
        )

    @app.exception_handler(RequestValidationError)
    async def handle_validation_error(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        errors = []
        for item in exc.errors():
            errors.append(
                {
                    "loc": [str(part) for part in item.get("loc", [])],
                    "msg": item.get("msg", "invalid value"),
                    "type": item.get("type", "value_error"),
                }
            )
        return JSONResponse(
            status_code=422,
            content=_error_content(1001, "参数校验失败", {"errors": errors}),
        )

    @app.exception_handler(StarletteHTTPException)
    async def handle_http_error(request: Request, exc: StarletteHTTPException) -> JSONResponse:
        mapping = {
            401: 1002,
            403: 1003,
            404: 1004,
            405: 1001,
            409: 1005,
        }
        code = mapping.get(exc.status_code, exc.status_code)
        message = str(exc.detail) if exc.detail else "请求失败"
        if exc.status_code == 404:
            message = "接口不存在"
        return JSONResponse(
            status_code=exc.status_code,
            content=_error_content(code, message),
        )

    @app.exception_handler(Exception)
    async def handle_unexpected(request: Request, exc: Exception) -> JSONResponse:
        logger.exception("unhandled exception on %s %s", request.method, request.url.path)
        return JSONResponse(
            status_code=500,
            content=_error_content(5000, "服务内部错误"),
        )
