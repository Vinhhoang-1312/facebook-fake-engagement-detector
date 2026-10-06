from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from statistics import median


@dataclass(frozen=True)
class ComparableKey:
    media_type: str
    paid_status: str
    hour_bucket: int
    weekday: int
    audience_bucket: str


@dataclass(frozen=True)
class RobustBaseline:
    count: int
    median: float
    mad: float

    def robust_z(self, value: float) -> float:
        scale = max(1.4826 * self.mad, 1.0)
        return (value - self.median) / scale


def build_baseline(values: Sequence[float], minimum_count: int = 8) -> RobustBaseline | None:
    clean = [float(value) for value in values]
    if len(clean) < minimum_count:
        return None
    center = float(median(clean))
    mad = float(median(abs(value - center) for value in clean))
    return RobustBaseline(len(clean), center, mad)


def audience_bucket(followers_count: int | None) -> str:
    if followers_count is None:
        return "unknown"
    if followers_count < 1_000:
        return "small"
    if followers_count < 10_000:
        return "medium"
    if followers_count < 100_000:
        return "large"
    return "very_large"

