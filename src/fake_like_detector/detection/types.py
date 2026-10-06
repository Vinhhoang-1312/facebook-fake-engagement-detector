from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Evidence:
    code: str
    severity: float
    message: str
    observed: float | None = None
    expected: float | None = None
    coverage: float = 1.0

    def as_dict(self) -> dict[str, object]:
        return {"code": self.code, "severity": round(self.severity, 6), "message": self.message, "observed": self.observed, "expected": self.expected, "coverage": round(self.coverage, 6)}


@dataclass(frozen=True)
class DetectorResult:
    name: str
    anomaly: float
    coverage: float
    evidence: tuple[Evidence, ...] = field(default_factory=tuple)
    counter_evidence: tuple[Evidence, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class SufficiencyResult:
    sufficient: bool
    reason: str | None
    coverage: float


def check_data_sufficiency(comparable_count: int, snapshot_count: int, coverage: float) -> SufficiencyResult:
    if comparable_count < 8:
        return SufficiencyResult(False, "need_at_least_8_comparable_posts", coverage)
    if snapshot_count < 2:
        return SufficiencyResult(False, "need_at_least_2_snapshots", coverage)
    if coverage < 0.35:
        return SufficiencyResult(False, "metric_coverage_too_low", coverage)
    return SufficiencyResult(True, None, coverage)

