from __future__ import annotations

from fake_like_detector.detection.types import DetectorResult, Evidence
from fake_like_detector.features.quality import QualityFeatures


class QualityDetector:
    def evaluate(self, features: QualityFeatures) -> DetectorResult:
        evidence: list[Evidence] = []
        counter: list[Evidence] = []
        anomaly = 0.0
        ratio = features.downstream_ratio
        if features.reactions is not None and features.reactions >= 100 and ratio is not None and ratio < 0.01:
            severity = min(1.0, (0.01 - ratio) / 0.01)
            anomaly = 0.55 + 0.4 * severity
            evidence.append(Evidence("low_downstream_quality", severity, "Many reactions produced unusually few comments and shares.", ratio, 0.01, features.coverage))
        elif ratio is not None and ratio >= 0.03:
            counter.append(Evidence("healthy_downstream_quality", 0.5, "Comments and shares are healthy relative to reactions.", ratio, 0.03, features.coverage))
            anomaly = max(0.0, anomaly - 0.2)
        if features.paid_status == "paid":
            counter.append(Evidence("declared_paid_promotion", 0.8, "The post is declared as paid promotion.", coverage=features.coverage))
            anomaly *= 0.55
        return DetectorResult("quality", min(max(anomaly, 0.0), 1.0), features.coverage, tuple(evidence), tuple(counter))

