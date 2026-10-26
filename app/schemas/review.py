"""Batch review request schema shared by courses and materials."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator


class BatchReviewRequest(BaseModel):
    ids: list[int] = Field(min_length=1, max_length=100)
    decision: Literal["approve", "reject"]
    comment: str | None = Field(default=None, max_length=500)

    @field_validator("ids")
    @classmethod
    def validate_ids(cls, value: list[int]) -> list[int]:
        if any(item < 1 for item in value):
            raise ValueError("ID 必须为正整数")
        return list(dict.fromkeys(value))

    @model_validator(mode="after")
    def reject_requires_comment(self) -> BatchReviewRequest:
        if self.decision == "reject" and not (self.comment or "").strip():
            raise ValueError("批量驳回时必须填写审核意见")
        return self
