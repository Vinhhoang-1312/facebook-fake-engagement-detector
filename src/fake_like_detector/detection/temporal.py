from __future__ import annotations

from fake_like_detector.detection.types import DetectorResult, Evidence
from fake_like_detector.features.temporal import TemporalFeatures


class TemporalDetector:
    def evaluate(self, features: TemporalFeatures) -> DetectorResult:
        evidence: list[Evidence] = []
        counter: list[Evidence] = []
        anomaly = 0.0
        if features.rate_z is not None and features.rate_z >= 3:
            severity = min(1.0, features.rate_z / 12)
            anomaly = max(anomaly, 0.45 + 0.55 * severity)
            evidence.append(Evidence("temporal_burst", severity, "Engagement rate is far above the robust baseline.", features.rate_z, 3.0, features.coverage))
        elif features.max_rate is not None and features.max_rate >= 500:
            severity = min(1.0, features.max_rate / 1000)
            anomaly = max(anomaly, 0.55 + 0.35 * severity)
            evidence.append(Evidence("absolute_burst", severity, "A large engagement burst occurred between snapshots.", features.max_rate, 500.0, features.coverage))
        if features.abrupt_stop:
            anomaly = min(1.0, anomaly + 0.1)
            evidence.append(Evidence("abrupt_stop", 0.5, "The burst stopped abruptly.", coverage=features.coverage))
        if features.counter_correction:
            counter.append(Evidence("counter_correction", 0.6, "A platform counter correction was observed; negative growth was ignored.", coverage=features.coverage))
            anomaly *= 0.8
        if features.snapshot_count < 2:
            evidence.append(Evidence("missing_history", 0.0, "At least two snapshots are needed for temporal analysis.", coverage=0.0))
        return DetectorResult("temporal", min(max(anomaly, 0.0), 1.0), features.coverage, tuple(evidence), tuple(counter))

