from __future__ import annotations

from collections.abc import Iterator
from datetime import datetime
from typing import Protocol

from fake_like_detector.domain import MetricSnapshot, PageRecord, PostRecord


class ProviderError(RuntimeError):
    pass


class ProviderAuthenticationError(ProviderError):
    pass


class ProviderPermissionError(ProviderError):
    pass


class ProviderRateLimitError(ProviderError):
    def __init__(self, message: str, retry_after_seconds: float | None = None) -> None:
        super().__init__(message)
        self.retry_after_seconds = retry_after_seconds


class ProviderTransientError(ProviderError):
    pass


class ProviderSchemaError(ProviderError):
    pass


class PageDataProvider(Protocol):
    def fetch_page(self, page_id: str) -> PageRecord: ...
    def iter_posts(self, page_id: str, since: datetime | None) -> Iterator[PostRecord]: ...
    def fetch_snapshot(self, post_id: str, collected_at: datetime) -> MetricSnapshot: ...

