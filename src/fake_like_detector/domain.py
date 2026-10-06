from __future__ import annotations

from datetime import UTC, datetime
from typing import Literal
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field, field_validator


def utc_now() -> datetime:
    return datetime.now(UTC)


class FrozenModel(BaseModel):
    model_config = ConfigDict(frozen=True)


class PageRecord(FrozenModel):
    id: str
    name: str
    followers_count: int | None = None


class PostRecord(FrozenModel):
    id: str
    page_id: str
    created_at: datetime
    message: str | None = None
    media_type: str = "unknown"
    paid_status: Literal["organic", "paid", "unknown"] = "unknown"
    permalink: str | None = None

    @field_validator("created_at")
    @classmethod
    def timezone_required(cls, value: datetime) -> datetime:
        if value.tzinfo is None:
            raise ValueError("created_at must be timezone-aware")
        return value.astimezone(UTC)


class MetricSnapshot(FrozenModel):
    post_id: str
    collected_at: datetime
    reactions: int | None = None
    comments: int | None = None
    shares: int | None = None
    views: int | None = None
    available_fields: frozenset[str] = Field(default_factory=frozenset)

    @field_validator("collected_at")
    @classmethod
    def collected_timezone_required(cls, value: datetime) -> datetime:
        if value.tzinfo is None:
            raise ValueError("collected_at must be timezone-aware")
        return value.astimezone(UTC)


class CommentRecord(FrozenModel):
    id: str
    post_id: str
    created_at: datetime
    message: str | None = None


class InteractionEvent(FrozenModel):
    post_id: str
    occurred_at: datetime
    kind: str
    actor_hash: str | None = None


class CollectionRun(FrozenModel):
    run_id: str = Field(default_factory=lambda: str(uuid4()))
    page_id: str
    started_at: datetime
    completed_at: datetime | None = None
    status: Literal["running", "success", "failed"] = "running"
    posts_seen: int = 0
    snapshots_added: int = 0
    error: str | None = None


PaidStatus = Literal["organic", "paid", "unknown"]
RiskLevel = Literal["normal", "watch", "suspicious", "highly_suspicious", "insufficient_data"]


class RiskAssessment(FrozenModel):
    assessment_id: str = Field(default_factory=lambda: str(uuid4()))
    post_id: str
    assessed_at: datetime = Field(default_factory=utc_now)
    score: float
    confidence: float
    coverage: float
    level: RiskLevel
    detector_version: str
    evidence: tuple[dict[str, object], ...] = ()
    counter_evidence: tuple[dict[str, object], ...] = ()


ReviewLabel = Literal["confirmed_suspicious", "legitimate", "uncertain"]


class AnalystReview(FrozenModel):
    assessment_id: str
    label: ReviewLabel
    note: str | None = None
    reviewed_at: datetime = Field(default_factory=utc_now)
