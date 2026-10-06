from __future__ import annotations

from collections.abc import Sequence
from datetime import UTC, datetime
from statistics import pstdev

from fake_like_detector.detection.types import DetectorResult, SufficiencyResult
from fake_like_detector.domain import RiskAssessment, RiskLevel


def fuse_results(results: Sequence[DetectorResult], sufficiency: SufficiencyResult, detector_version: str, *, post_id: str, assessed_at: datetime | None = None) -> RiskAssessment:
    active = [result for result in results if result.coverage >= 0.2]
    coverage = sum(result.coverage for result in active) / len(active) if active else 0.0
    if not sufficiency.sufficient or not active or coverage < 0.35:
        return RiskAssessment(post_id=post_id, assessed_at=assessed_at or datetime.now(UTC), score=0.0, confidence=min(coverage, sufficiency.coverage), coverage=coverage, level="insufficient_data", detector_version=detector_version)
    weighted_sum = sum(result.anomaly * result.coverage for result in active)
    weight = sum(result.coverage for result in active)
    score = weighted_sum / weight
    disagreement = pstdev([result.anomaly for result in active]) if len(active) > 1 else 0.0
    confidence = max(0.0, min(1.0, coverage * (1 - 0.65 * disagreement)))
    if score >= 0.82:
        level: RiskLevel = "highly_suspicious"
    elif score >= 0.60:
        level = "suspicious"
    elif score >= 0.32:
        level = "watch"
    else:
        level = "normal"
    evidence = sorted((item for result in active for item in result.evidence), key=lambda item: (-item.severity * item.coverage, item.code))
    counter = sorted((item for result in active for item in result.counter_evidence), key=lambda item: (-item.severity * item.coverage, item.code))
    return RiskAssessment(post_id=post_id, assessed_at=assessed_at or datetime.now(UTC), score=round(score, 6), confidence=round(confidence, 6), coverage=round(coverage, 6), level=level, detector_version=detector_version, evidence=tuple(item.as_dict() for item in evidence), counter_evidence=tuple(item.as_dict() for item in counter))
