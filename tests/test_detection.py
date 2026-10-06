from __future__ import annotations

from fake_like_detector.detection.fusion import fuse_results
from fake_like_detector.detection.quality import QualityDetector
from fake_like_detector.detection.temporal import TemporalDetector
from fake_like_detector.detection.types import (
    DetectorResult,
    SufficiencyResult,
    check_data_sufficiency,
)
from fake_like_detector.features.quality import QualityFeatures
from fake_like_detector.features.temporal import TemporalFeatures


def test_sufficiency_requires_history_and_comparable_posts() -> None:
    result = check_data_sufficiency(comparable_count=7, snapshot_count=2, coverage=1.0)
    assert result.sufficient is False
    assert result.reason == "need_at_least_8_comparable_posts"


def test_burst_plus_low_quality_becomes_suspicious() -> None:
    temporal = TemporalDetector().evaluate(TemporalFeatures(snapshot_count=3, total_growth=900, max_rate=900, rate_z=12, counter_correction=False, abrupt_stop=False, coverage=1.0))
    quality = QualityDetector().evaluate(QualityFeatures(reactions=1000, comments=2, shares=1, views=None, comment_ratio=.002, share_ratio=.001, downstream_ratio=.003, paid_status="organic", coverage=.75))
    assessment = fuse_results([temporal, quality], SufficiencyResult(True, None, 1.0), "test-v1", post_id="x")
    assert assessment.level in {"suspicious", "highly_suspicious"}
    assert assessment.score >= .6
    assert assessment.evidence


def test_low_coverage_returns_insufficient_and_disagreement_lowers_confidence() -> None:
    unavailable = DetectorResult(name="x", anomaly=.9, coverage=.1)
    result = fuse_results([unavailable], SufficiencyResult(True, None, .1), "v1", post_id="x")
    assert result.level == "insufficient_data"

