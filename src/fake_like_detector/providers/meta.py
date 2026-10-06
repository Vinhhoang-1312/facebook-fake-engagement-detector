from __future__ import annotations

import time
from collections.abc import Callable, Iterator
from dataclasses import dataclass
from datetime import datetime
from typing import Any

import httpx
from pydantic import SecretStr

from fake_like_detector.domain import MetricSnapshot, PageRecord, PostRecord
from fake_like_detector.providers.base import (
    ProviderAuthenticationError,
    ProviderPermissionError,
    ProviderRateLimitError,
    ProviderSchemaError,
    ProviderTransientError,
)
from fake_like_detector.security import redact_secrets


@dataclass(frozen=True)
class FieldAvailabilityReport:
    accessible: tuple[str, ...]
    unavailable: tuple[str, ...]
    denied: tuple[str, ...]


class MetaGraphProvider:
    """Minimal documented Meta Graph API client for a managed Facebook Page."""

    def __init__(self, client: httpx.Client, page_id: str, access_token: SecretStr, api_version: str, max_retries: int = 3, sleep: Callable[[float], None] = time.sleep, base_url: str = "https://graph.facebook.com") -> None:
        self.client = client
        self.page_id = page_id
        self._token = access_token.get_secret_value()
        self.api_version = api_version.lstrip("/")
        self.max_retries = max_retries
        self.sleep = sleep
        self.base_url = base_url.rstrip("/")

    def _get(self, path: str, params: dict[str, str]) -> dict[str, Any]:
        url = f"{self.base_url}/{self.api_version}/{path.lstrip('/')}"
        for attempt in range(self.max_retries + 1):
            try:
                response = self.client.get(url, params=params, headers={"Authorization": f"Bearer {self._token}"})
            except httpx.HTTPError as exc:
                if attempt < self.max_retries:
                    self.sleep(2**attempt)
                    continue
                raise ProviderTransientError(redact_secrets(str(exc), [self._token])) from None
            payload = self._safe_json(response)
            error = payload.get("error") if isinstance(payload, dict) else None
            code = error.get("code") if isinstance(error, dict) else None
            message = error.get("message", response.reason_phrase) if isinstance(error, dict) else response.reason_phrase
            safe_message = redact_secrets(str(message), [self._token])
            retryable = response.status_code == 429 or code in {4, 17, 32, 613}
            if retryable and attempt < self.max_retries:
                delay = float(response.headers.get("Retry-After", 2**attempt))
                self.sleep(delay)
                continue
            if retryable:
                raise ProviderRateLimitError(safe_message)
            if response.is_success and isinstance(payload, dict):
                return payload
            if code == 190 or response.status_code == 401:
                raise ProviderAuthenticationError(safe_message)
            if code in {10, 200} or response.status_code == 403:
                raise ProviderPermissionError(safe_message)
            if response.status_code >= 500:
                raise ProviderTransientError(safe_message)
            raise ProviderSchemaError(safe_message)
        raise ProviderTransientError("Meta request failed")

    @staticmethod
    def _safe_json(response: httpx.Response) -> dict[str, Any]:
        try:
            payload = response.json()
            return payload if isinstance(payload, dict) else {}
        except ValueError:
            return {}

    def fetch_page(self, page_id: str) -> PageRecord:
        payload = self._get(page_id, {"fields": "id,name,followers_count"})
        try:
            return PageRecord(id=str(payload["id"]), name=str(payload["name"]), followers_count=payload.get("followers_count"))
        except (KeyError, TypeError, ValueError) as exc:
            raise ProviderSchemaError(f"Invalid Page response: {type(exc).__name__}") from None

    def iter_posts(self, page_id: str, since: datetime | None) -> Iterator[PostRecord]:
        params = {"fields": "id,created_time,message,permalink_url,type,is_published", "limit": "100"}
        if since is not None:
            params["since"] = str(int(since.timestamp()))
        seen: set[str] = set()
        while True:
            payload = self._get(f"{page_id}/posts", params)
            data = payload.get("data", [])
            if not isinstance(data, list):
                raise ProviderSchemaError("Posts response data is not a list")
            for item in data:
                post_id = str(item["id"])
                if post_id in seen:
                    continue
                seen.add(post_id)
                yield PostRecord(id=post_id, page_id=page_id, created_at=datetime.fromisoformat(str(item["created_time"])), message=item.get("message"), media_type=str(item.get("type", "unknown")), paid_status="unknown", permalink=item.get("permalink_url"))
            paging = payload.get("paging", {})
            cursors = paging.get("cursors", {}) if isinstance(paging, dict) else {}
            after = cursors.get("after") if isinstance(cursors, dict) else None
            if not after or not paging.get("next"):
                break
            params = {**params, "after": str(after)}

    def fetch_snapshot(self, post_id: str, collected_at: datetime) -> MetricSnapshot:
        payload = self._get(post_id, {"fields": "id,reactions.limit(0).summary(true),comments.limit(0).summary(true),shares"})
        fields: set[str] = set()

        def summary_count(name: str) -> int | None:
            block = payload.get(name)
            if not isinstance(block, dict):
                return None
            summary = block.get("summary")
            if not isinstance(summary, dict) or "total_count" not in summary:
                return None
            fields.add(name)
            return int(summary["total_count"])

        reactions = summary_count("reactions")
        comments = summary_count("comments")
        shares = None
        if isinstance(payload.get("shares"), dict) and "count" in payload["shares"]:
            shares = int(payload["shares"]["count"])
            fields.add("shares")
        return MetricSnapshot(post_id=post_id, collected_at=collected_at, reactions=reactions, comments=comments, shares=shares, views=None, available_fields=frozenset(fields))

    def audit_fields(self) -> FieldAvailabilityReport:
        requested = ("id", "name", "followers_count")
        payload = self._get(self.page_id, {"fields": ",".join(requested)})
        accessible = tuple(field for field in requested if field in payload)
        unavailable = tuple(field for field in requested if field not in payload)
        return FieldAvailabilityReport(accessible, unavailable, ())

