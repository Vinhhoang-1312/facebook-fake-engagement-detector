from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from fake_like_detector.domain import AnalystReview, ReviewLabel
from fake_like_detector.storage.repository import Repository


def display_metric(value: int | float | None) -> str:
    return "Not available" if value is None else str(value)


@dataclass(frozen=True)
class OverviewView:
    post_count: int
    assessed_count: int
    suspicious_count: int
    failed_collection_runs: int


@dataclass(frozen=True)
class PostSummaryView:
    post_id: str
    created_at: datetime
    media_type: str
    reactions: str
    comments: str
    shares: str
    risk_level: str
    score: float | None


@dataclass(frozen=True)
class PostDetailView:
    post: PostSummaryView
    snapshots: tuple[dict[str, object], ...]
    evidence: tuple[dict[str, object], ...]
    counter_evidence: tuple[dict[str, object], ...]


@dataclass(frozen=True)
class DataHealthView:
    total_snapshots: int
    reactions_coverage: float
    comments_coverage: float
    shares_coverage: float


class DashboardRepository:
    def __init__(self, repository: Repository) -> None:
        self.repository = repository

    def overview(self) -> OverviewView:
        posts = self.repository.list_posts()
        assessments = self.repository.list_assessments()
        suspicious = sum(item.level in {"suspicious", "highly_suspicious"} for item in assessments)
        return OverviewView(len(posts), len(assessments), suspicious, self.repository.count_collection_runs("failed"))

    def posts(self) -> list[PostSummaryView]:
        result: list[PostSummaryView] = []
        for post in self.repository.list_posts():
            snapshots = self.repository.snapshots_for_post(post.id)
            latest = snapshots[-1] if snapshots else None
            assessment = self.repository.latest_assessment(post.id)
            result.append(PostSummaryView(post.id, post.created_at, post.media_type, display_metric(latest.reactions if latest else None), display_metric(latest.comments if latest else None), display_metric(latest.shares if latest else None), assessment.level if assessment else "not_assessed", assessment.score if assessment else None))
        return result

    def post_detail(self, post_id: str) -> PostDetailView:
        summary = next((item for item in self.posts() if item.post_id == post_id), None)
        if summary is None:
            raise KeyError(post_id)
        snapshots: tuple[dict[str, object], ...] = tuple({"collected_at": item.collected_at.isoformat(), "reactions": item.reactions, "comments": item.comments, "shares": item.shares} for item in self.repository.snapshots_for_post(post_id))
        assessment = self.repository.latest_assessment(post_id)
        return PostDetailView(summary, snapshots, assessment.evidence if assessment else (), assessment.counter_evidence if assessment else ())

    def data_health(self) -> DataHealthView:
        snapshots = [snapshot for post in self.repository.list_posts() for snapshot in self.repository.snapshots_for_post(post.id)]
        total = len(snapshots)
        def coverage(field: str) -> float:
            return 0.0 if total == 0 else sum(getattr(item, field) is not None for item in snapshots) / total
        return DataHealthView(total, coverage("reactions"), coverage("comments"), coverage("shares"))

    def save_review(self, assessment_id: str, label: ReviewLabel, note: str | None, reviewed_at: datetime) -> None:
        self.repository.save_review(AnalystReview(assessment_id=assessment_id, label=label, note=note, reviewed_at=reviewed_at))
