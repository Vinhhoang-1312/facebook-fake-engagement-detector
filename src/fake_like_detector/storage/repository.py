from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import cast

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker

from fake_like_detector.domain import (
    AnalystReview,
    CollectionRun,
    MetricSnapshot,
    PageRecord,
    PaidStatus,
    PostRecord,
    RiskAssessment,
    RiskLevel,
)
from fake_like_detector.storage.models import (
    AssessmentModel,
    CollectionRunModel,
    PageModel,
    PostModel,
    ReviewModel,
    SnapshotModel,
)


class Repository:
    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self.session_factory = session_factory

    def upsert_page(self, page: PageRecord) -> None:
        with self.session_factory.begin() as session:
            row = session.get(PageModel, page.id)
            if row is None:
                session.add(PageModel(id=page.id, name=page.name, followers_count=page.followers_count))
            else:
                row.name, row.followers_count = page.name, page.followers_count

    def upsert_post(self, post: PostRecord) -> None:
        with self.session_factory.begin() as session:
            row = session.get(PostModel, post.id)
            values = post.model_dump()
            if row is None:
                session.add(PostModel(**values))
            else:
                for key, value in values.items():
                    setattr(row, key, value)

    def add_snapshot(self, snapshot: MetricSnapshot) -> bool:
        try:
            with self.session_factory.begin() as session:
                session.add(SnapshotModel(
                    post_id=snapshot.post_id,
                    collected_at=snapshot.collected_at,
                    reactions=snapshot.reactions,
                    comments=snapshot.comments,
                    shares=snapshot.shares,
                    views=snapshot.views,
                    available_fields_json=json.dumps(sorted(snapshot.available_fields)),
                ))
            return True
        except IntegrityError:
            return False

    def snapshots_for_post(self, post_id: str) -> list[MetricSnapshot]:
        with self.session_factory() as session:
            rows = session.scalars(select(SnapshotModel).where(SnapshotModel.post_id == post_id).order_by(SnapshotModel.collected_at)).all()
            return [self._snapshot(row) for row in rows]

    def save_collection_run(self, run: CollectionRun) -> None:
        with self.session_factory.begin() as session:
            row = session.get(CollectionRunModel, run.run_id)
            values = run.model_dump()
            if row is None:
                session.add(CollectionRunModel(**values))
            else:
                for key, value in values.items():
                    setattr(row, key, value)

    def save_assessment(self, assessment: RiskAssessment) -> None:
        with self.session_factory.begin() as session:
            values = assessment.model_dump(exclude={"evidence", "counter_evidence"})
            values["evidence_json"] = json.dumps(assessment.evidence, sort_keys=True)
            values["counter_evidence_json"] = json.dumps(assessment.counter_evidence, sort_keys=True)
            session.merge(AssessmentModel(**values))

    def save_review(self, review: AnalystReview) -> None:
        with self.session_factory.begin() as session:
            session.merge(ReviewModel(**review.model_dump()))

    def get_post(self, post_id: str) -> PostRecord | None:
        with self.session_factory() as session:
            row = session.get(PostModel, post_id)
            return None if row is None else self._post(row)

    def list_posts(self) -> list[PostRecord]:
        with self.session_factory() as session:
            rows = session.scalars(select(PostModel).order_by(PostModel.created_at.desc(), PostModel.id)).all()
            return [self._post(row) for row in rows]

    def list_assessments(self) -> list[RiskAssessment]:
        with self.session_factory() as session:
            rows = session.scalars(select(AssessmentModel).order_by(AssessmentModel.assessed_at.desc())).all()
            return [self._assessment(row) for row in rows]

    def latest_assessment(self, post_id: str) -> RiskAssessment | None:
        with self.session_factory() as session:
            row = session.scalars(select(AssessmentModel).where(AssessmentModel.post_id == post_id).order_by(AssessmentModel.assessed_at.desc()).limit(1)).first()
            return None if row is None else self._assessment(row)

    def count_collection_runs(self, status: str | None = None) -> int:
        with self.session_factory() as session:
            rows = session.scalars(select(CollectionRunModel)).all()
            return sum(1 for row in rows if status is None or row.status == status)

    @staticmethod
    def _snapshot(row: SnapshotModel) -> MetricSnapshot:
        return MetricSnapshot(post_id=row.post_id, collected_at=_as_utc(row.collected_at), reactions=row.reactions, comments=row.comments, shares=row.shares, views=row.views, available_fields=frozenset(json.loads(row.available_fields_json)))

    @staticmethod
    def _post(row: PostModel) -> PostRecord:
        return PostRecord(id=row.id, page_id=row.page_id, created_at=_as_utc(row.created_at), message=row.message, media_type=row.media_type, paid_status=cast(PaidStatus, row.paid_status), permalink=row.permalink)

    @staticmethod
    def _assessment(row: AssessmentModel) -> RiskAssessment:
        return RiskAssessment(assessment_id=row.assessment_id, post_id=row.post_id, assessed_at=_as_utc(row.assessed_at), score=row.score, confidence=row.confidence, coverage=row.coverage, level=cast(RiskLevel, row.level), detector_version=row.detector_version, evidence=tuple(json.loads(row.evidence_json)), counter_evidence=tuple(json.loads(row.counter_evidence_json)))


def _as_utc(value: datetime) -> datetime:
    return value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)
