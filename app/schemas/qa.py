"""Q&A request and record schemas."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator, model_validator

from app.db.models.qa import QARecord


class AskRequest(BaseModel):
    question: str = Field(min_length=1, max_length=2000)
    scope: Literal["course", "personal", "all"] = "course"
    course_id: int | None = Field(default=None, ge=1)
    knowledge_base_id: int | None = Field(default=None, ge=1)

    @field_validator("question")
    @classmethod
    def strip_question(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("问题不能为空")
        return value

    @model_validator(mode="after")
    def validate_scope_targets(self) -> AskRequest:
        if self.scope == "course" and self.course_id is None:
            raise ValueError("课程问答必须指定 course_id")
        if self.scope == "personal" and self.knowledge_base_id is None:
            raise ValueError("个人知识库问答必须指定 knowledge_base_id")
        if self.scope == "all" and self.course_id is None and self.knowledge_base_id is None:
            raise ValueError("综合问答至少需要选择一个课程或知识库")
        return self


def qa_record_out(record: QARecord) -> dict[str, Any]:
    return {
        "id": record.id,
        "scope": record.scope,
        "question": record.question,
        "answer": record.answer,
        "references": record.references_json or [],
        "hit": record.hit,
        "intent": record.intent,
        "scope_note": record.scope_note,
        "latency_ms": record.latency_ms,
        "status": record.status,
        "course_id": record.course_id,
        "course_title": record.course.title if record.course else None,
        "knowledge_base_id": record.knowledge_base_id,
        "knowledge_base_name": (record.knowledge_base.name if record.knowledge_base else None),
        "created_at": (
            record.created_at.isoformat()
            if isinstance(record.created_at, datetime)
            else record.created_at
        ),
    }
