"""Material metadata and review schemas."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, model_validator

from app.db.models.material import Material


class MaterialReviewRequest(BaseModel):
    decision: Literal["approve", "reject"]
    comment: str | None = Field(default=None, max_length=500)

    @model_validator(mode="after")
    def reject_requires_comment(self) -> MaterialReviewRequest:
        if self.decision == "reject" and not (self.comment or "").strip():
            raise ValueError("驳回资料时必须填写审核意见")
        return self


def material_out(material: Material, *, management: bool) -> dict:
    payload = {
        "id": material.id,
        "scope": material.scope,
        "course_id": material.course_id,
        "course_title": material.course.title if material.course else None,
        "knowledge_base_id": material.knowledge_base_id,
        "knowledge_base_name": (material.knowledge_base.name if material.knowledge_base else None),
        "owner_id": material.owner_id,
        "owner": (
            {"id": material.owner.id, "username": material.owner.username}
            if material.owner
            else None
        ),
        "chapter_id": material.chapter_id,
        "chapter_title": material.chapter.title if material.chapter else None,
        "knowledge_id": material.knowledge_id,
        "knowledge_title": material.knowledge.name if material.knowledge else None,
        "title": material.title,
        "source_filename": material.source_filename,
        "file_type": material.file_type,
        "file_size": material.file_size,
        "status": material.status,
        "index_status": material.index_status,
        "view_count": material.view_count,
        "download_count": material.download_count,
        "review_comment": material.review_comment,
        "uploader": (
            {
                "id": material.uploader.id,
                "username": material.uploader.username,
            }
            if material.uploader
            else None
        ),
        "created_at": material.created_at,
        "updated_at": material.updated_at,
        "reviewed_at": material.reviewed_at,
        "indexed_at": material.indexed_at,
    }
    if management:
        payload.update(
            {
                "rag_filename": material.rag_filename,
                "vector_doc_id": material.vector_doc_id,
                "index_error": material.index_error,
            }
        )
    return payload


def material_list_out(material: Material, *, management: bool) -> dict:
    data = material_out(material, management=management)
    # Serialize datetimes consistently for the JSON envelope.
    return {
        key: (value.isoformat() if isinstance(value, datetime) else value)
        for key, value in data.items()
    }
