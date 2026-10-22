"""EduMate FastAPI application entry point."""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app import __version__
from app.api.v1 import health
from app.core.config import get_settings
from app.core.errors import register_exception_handlers, success
from app.core.logging import configure_logging
from app.core.middleware import RequestIdMiddleware
from app.db.session import dispose_engine

settings = get_settings()
configure_logging(settings.log_level)


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings.upload_path.mkdir(parents=True, exist_ok=True)
    yield
    await dispose_engine()


app = FastAPI(
    title=settings.app_name,
    version=__version__,
    description="智课学伴 EduMate - AI 个性化学习与课程教学平台",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-Request-ID"],
)
app.add_middleware(RequestIdMiddleware)

register_exception_handlers(app)

app.include_router(health.router, prefix=f"{settings.api_prefix}/health")


@app.get("/", tags=["meta"])
async def index() -> dict:
    return success(
        {
            "service": settings.app_name,
            "version": __version__,
            "docs": "/docs",
            "api_prefix": settings.api_prefix,
        }
    )
