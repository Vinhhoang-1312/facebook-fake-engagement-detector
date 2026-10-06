from __future__ import annotations

from dataclasses import dataclass

from fake_like_detector.domain import MetricSnapshot


@dataclass(frozen=True)
class QualityFeatures:
    reactions: int | None
    comments: int | None
    shares: int | None
    views: int | None
    comment_ratio: float | None
    share_ratio: float | None
    downstream_ratio: float | None
    paid_status: str = "unknown"
    coverage: float = 0.0


def _ratio(numerator: int | None, denominator: int | None) -> float | None:
    if numerator is None or denominator is None:
        return None
    if denominator == 0:
        return 0.0 if numerator == 0 else None
    return numerator / denominator


def compute_quality_features(snapshot: MetricSnapshot, paid_status: str = "unknown") -> QualityFeatures:
    ratios = [_ratio(snapshot.comments, snapshot.reactions), _ratio(snapshot.shares, snapshot.reactions)]
    downstream = None
    if snapshot.reactions is not None and snapshot.comments is not None and snapshot.shares is not None:
        downstream = _ratio(snapshot.comments + snapshot.shares, snapshot.reactions)
    present = sum(value is not None for value in (snapshot.reactions, snapshot.comments, snapshot.shares, snapshot.views))
    return QualityFeatures(snapshot.reactions, snapshot.comments, snapshot.shares, snapshot.views, ratios[0], ratios[1], downstream, paid_status, present / 4)

