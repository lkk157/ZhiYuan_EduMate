"""Personal knowledge base schemas."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field, field_validator

from app.db.models.knowledge_base import KnowledgeBase


class KnowledgeBaseCreateRequest(BaseModel):
    name: str = Field(min_length=2, max_length=100)
    description: str | None = Field(default=None, max_length=500)

    @field_validator("name")
    @classmethod
    def strip_name(cls, value: str) -> str:
        value = value.strip()
        if len(value) < 2:
            raise ValueError("知识库名称至少 2 个字符")
        return value


class KnowledgeBaseUpdateRequest(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=100)
    description: str | None = Field(default=None, max_length=500)

    @field_validator("name")
    @classmethod
    def strip_name(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip()
        if len(value) < 2:
            raise ValueError("知识库名称至少 2 个字符")
        return value


def knowledge_base_out(
    kb: KnowledgeBase,
    *,
    material_count: int = 0,
    indexed_count: int = 0,
) -> dict:
    return {
        "id": kb.id,
        "name": kb.name,
        "description": kb.description,
        "is_default": kb.is_default,
        "status": kb.status,
        "material_count": material_count,
        "indexed_count": indexed_count,
        "created_at": kb.created_at.isoformat()
        if isinstance(kb.created_at, datetime)
        else kb.created_at,
        "updated_at": kb.updated_at.isoformat()
        if isinstance(kb.updated_at, datetime)
        else kb.updated_at,
    }
