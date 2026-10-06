from __future__ import annotations

from datetime import UTC, datetime, timedelta

from fake_like_detector.domain import MetricSnapshot
from fake_like_detector.features.baseline import build_baseline
from fake_like_detector.features.quality import compute_quality_features
from fake_like_detector.features.temporal import compute_temporal_features


def snap(at: datetime, reactions: int | None, comments: int | None = 0, shares: int | None = 0) -> MetricSnapshot:
    fields = {name for name, value in {"reactions": reactions, "comments": comments, "shares": shares}.items() if value is not None}
    return MetricSnapshot(post_id="x", collected_at=at, reactions=reactions, comments=comments, shares=shares, available_fields=frozenset(fields))


def test_robust_baseline_ignores_large_outlier_and_needs_eight_values() -> None:
    assert build_baseline([1, 2, 3, 4, 5, 6, 7]) is None
    baseline = build_baseline([10, 10, 11, 11, 12, 12, 13, 1000])
    assert baseline is not None
    assert baseline.median == 11.5
    assert baseline.mad < 3


def test_temporal_sorts_and_never_turns_counter_correction_into_growth() -> None:
    now = datetime(2026, 1, 1, tzinfo=UTC)
    features = compute_temporal_features([snap(now + timedelta(hours=1), 90), snap(now, 100)], None)
    assert features.counter_correction is True
    assert features.total_growth == 0
    assert features.max_rate == 0


def test_quality_preserves_missing_denominator_and_explicit_zero() -> None:
    now = datetime(2026, 1, 1, tzinfo=UTC)
    missing = compute_quality_features(snap(now, None, 2, 1))
    zero = compute_quality_features(snap(now, 0, 0, 0))
    assert missing.comment_ratio is None
    assert zero.comment_ratio == 0

