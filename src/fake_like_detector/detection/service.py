from __future__ import annotations

from datetime import datetime

from fake_like_detector.detection.fusion import fuse_results
from fake_like_detector.detection.quality import QualityDetector
from fake_like_detector.detection.temporal import TemporalDetector
from fake_like_detector.detection.types import check_data_sufficiency
from fake_like_detector.domain import RiskAssessment
from fake_like_detector.features.baseline import build_baseline
from fake_like_detector.features.quality import QualityFeatures, compute_quality_features
from fake_like_detector.features.temporal import compute_temporal_features
from fake_like_detector.storage.repository import Repository


class AssessmentService:
    def __init__(self, repository: Repository, detector_version: str = "mvp-1") -> None:
        self.repository = repository
        self.detector_version = detector_version

    def assess_post(self, post_id: str, assessed_at: datetime) -> RiskAssessment:
        post = self.repository.get_post(post_id)
        if post is None:
            raise KeyError(f"Unknown post: {post_id}")
        snapshots = self.repository.snapshots_for_post(post_id)
        comparable_rates: list[float] = []
        comparable_count = 0
        for candidate in self.repository.list_posts():
            if candidate.id == post_id or candidate.media_type != post.media_type or candidate.paid_status != post.paid_status:
                continue
            candidate_features = compute_temporal_features(self.repository.snapshots_for_post(candidate.id), None)
            comparable_count += 1
            if candidate_features.max_rate is not None:
                comparable_rates.append(candidate_features.max_rate)
        baseline = build_baseline(comparable_rates)
        temporal_features = compute_temporal_features(snapshots, baseline)
        if snapshots:
            quality_features = compute_quality_features(snapshots[-1], post.paid_status)
            quality_result = QualityDetector().evaluate(quality_features)
            coverage = (temporal_features.coverage + quality_features.coverage) / 2
        else:
            quality_result = QualityDetector().evaluate(compute_quality_features_placeholder(post.paid_status))
            coverage = 0.0
        temporal_result = TemporalDetector().evaluate(temporal_features)
        sufficiency = check_data_sufficiency(comparable_count, len(snapshots), coverage)
        assessment = fuse_results([temporal_result, quality_result], sufficiency, self.detector_version, post_id=post_id, assessed_at=assessed_at)
        self.repository.save_assessment(assessment)
        return assessment


def compute_quality_features_placeholder(paid_status: str) -> QualityFeatures:
    return QualityFeatures(None, None, None, None, None, None, None, paid_status, 0.0)
