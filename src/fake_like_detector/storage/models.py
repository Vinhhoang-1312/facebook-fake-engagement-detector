from __future__ import annotations

from datetime import datetime

from sqlalchemy import Float, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class PageModel(Base):
    __tablename__ = "pages"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    name: Mapped[str]
    followers_count: Mapped[int | None] = mapped_column(Integer, nullable=True)


class PostModel(Base):
    __tablename__ = "posts"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    page_id: Mapped[str] = mapped_column(ForeignKey("pages.id"), index=True)
    created_at: Mapped[datetime]
    message: Mapped[str | None] = mapped_column(Text, nullable=True)
    media_type: Mapped[str]
    paid_status: Mapped[str]
    permalink: Mapped[str | None] = mapped_column(Text, nullable=True)


class SnapshotModel(Base):
    __tablename__ = "metric_snapshots"
    __table_args__ = (UniqueConstraint("post_id", "collected_at", name="uq_snapshot_time"),)
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    post_id: Mapped[str] = mapped_column(ForeignKey("posts.id"), index=True)
    collected_at: Mapped[datetime] = mapped_column(index=True)
    reactions: Mapped[int | None] = mapped_column(Integer, nullable=True)
    comments: Mapped[int | None] = mapped_column(Integer, nullable=True)
    shares: Mapped[int | None] = mapped_column(Integer, nullable=True)
    views: Mapped[int | None] = mapped_column(Integer, nullable=True)
    available_fields_json: Mapped[str] = mapped_column(Text, default="[]")


class CollectionRunModel(Base):
    __tablename__ = "collection_runs"
    run_id: Mapped[str] = mapped_column(String, primary_key=True)
    page_id: Mapped[str] = mapped_column(String, index=True)
    started_at: Mapped[datetime]
    completed_at: Mapped[datetime | None] = mapped_column(nullable=True)
    status: Mapped[str]
    posts_seen: Mapped[int] = mapped_column(Integer, default=0)
    snapshots_added: Mapped[int] = mapped_column(Integer, default=0)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)


class AssessmentModel(Base):
    __tablename__ = "risk_assessments"
    assessment_id: Mapped[str] = mapped_column(String, primary_key=True)
    post_id: Mapped[str] = mapped_column(ForeignKey("posts.id"), index=True)
    assessed_at: Mapped[datetime]
    score: Mapped[float] = mapped_column(Float)
    confidence: Mapped[float] = mapped_column(Float)
    coverage: Mapped[float] = mapped_column(Float)
    level: Mapped[str]
    detector_version: Mapped[str]
    evidence_json: Mapped[str] = mapped_column(Text, default="[]")
    counter_evidence_json: Mapped[str] = mapped_column(Text, default="[]")


class ReviewModel(Base):
    __tablename__ = "analyst_reviews"
    assessment_id: Mapped[str] = mapped_column(ForeignKey("risk_assessments.assessment_id"), primary_key=True)
    label: Mapped[str]
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    reviewed_at: Mapped[datetime]

