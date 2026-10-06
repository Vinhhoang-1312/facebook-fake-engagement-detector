from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from fake_like_detector.domain import MetricSnapshot

if TYPE_CHECKING:
    from collections.abc import Sequence

    from fake_like_detector.features.baseline import RobustBaseline


@dataclass(frozen=True)
class TemporalFeatures:
    snapshot_count: int
    total_growth: float | None
    max_rate: float | None
    rate_z: float | None
    counter_correction: bool
    abrupt_stop: bool
    coverage: float


def _total(snapshot: MetricSnapshot) -> int | None:
    values = [snapshot.reactions, snapshot.comments, snapshot.shares]
    available = [value for value in values if value is not None]
    return None if not available else sum(available)


def compute_temporal_features(snapshots: Sequence[MetricSnapshot], baseline: RobustBaseline | None) -> TemporalFeatures:
    ordered = sorted(snapshots, key=lambda item: item.collected_at)
    totals = [_total(snapshot) for snapshot in ordered]
    valid_pairs = 0
    rates: list[float] = []
    positive_growth = 0.0
    correction = False
    for previous, current, old_total, new_total in zip(
        ordered[:-1], ordered[1:], totals[:-1], totals[1:], strict=True
    ):
        if old_total is None or new_total is None:
            continue
        hours = (current.collected_at - previous.collected_at).total_seconds() / 3600
        if hours <= 0:
            continue
        valid_pairs += 1
        delta = new_total - old_total
        if delta < 0:
            correction = True
            delta = 0
        positive_growth += delta
        rates.append(delta / hours)
    max_rate = max(rates, default=None)
    rate_z = baseline.robust_z(max_rate) if baseline and max_rate is not None else None
    abrupt_stop = len(rates) >= 2 and rates[-2] > 0 and rates[-1] < rates[-2] * 0.05
    possible_pairs = max(len(ordered) - 1, 1)
    coverage = min(1.0, valid_pairs / possible_pairs)
    return TemporalFeatures(len(ordered), positive_growth if valid_pairs else None, max_rate, rate_z, correction, abrupt_stop, coverage)
