from __future__ import annotations

from datetime import UTC, datetime

import httpx
import pytest
from pydantic import SecretStr

from fake_like_detector.providers.base import ProviderPermissionError
from fake_like_detector.providers.meta import MetaGraphProvider


def test_meta_provider_paginates_and_uses_bearer_auth() -> None:
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        if request.url.params.get("after") == "next-cursor":
            return httpx.Response(200, json={"data": [{"id": "2", "created_time": "2026-01-01T01:00:00+0000", "type": "photo"}]})
        return httpx.Response(200, json={"data": [{"id": "1", "created_time": "2026-01-01T00:00:00+0000", "type": "status"}], "paging": {"cursors": {"after": "next-cursor"}, "next": "yes"}})

    client = httpx.Client(transport=httpx.MockTransport(handler))
    provider = MetaGraphProvider(client, "page", SecretStr("super-secret"), "v24.0", sleep=lambda _: None)
    posts = list(provider.iter_posts("page", None))
    assert [post.id for post in posts] == ["1", "2"]
    assert all(request.headers["Authorization"] == "Bearer super-secret" for request in seen)
    assert seen[1].url.params["after"] == "next-cursor"


def test_meta_provider_preserves_missing_fields_and_redacts_errors() -> None:
    calls = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        if calls == 1:
            return httpx.Response(429, json={"error": {"message": "slow down", "code": 4}})
        return httpx.Response(200, json={"id": "x", "reactions": {"summary": {"total_count": 0}}, "comments": {"summary": {"total_count": 2}}})

    provider = MetaGraphProvider(httpx.Client(transport=httpx.MockTransport(handler)), "page", SecretStr("super-secret"), "v24.0", max_retries=1, sleep=lambda _: None)
    snapshot = provider.fetch_snapshot("x", datetime(2026, 1, 1, tzinfo=UTC))
    assert snapshot.reactions == 0
    assert snapshot.shares is None
    assert calls == 2

    denied = MetaGraphProvider(httpx.Client(transport=httpx.MockTransport(lambda _: httpx.Response(403, json={"error": {"message": "bad super-secret", "code": 10}}))), "page", SecretStr("super-secret"), "v24.0")
    with pytest.raises(ProviderPermissionError) as exc_info:
        denied.fetch_page("page")
    assert "super-secret" not in str(exc_info.value)


def test_pagination_rate_limit_retries_same_cursor_without_duplicates() -> None:
    cursors: list[str | None] = []
    second_page_attempts = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal second_page_attempts
        cursor = request.url.params.get("after")
        cursors.append(cursor)
        if cursor is None:
            return httpx.Response(
                200,
                json={
                    "data": [
                        {
                            "id": "1",
                            "created_time": "2026-01-01T00:00:00+0000",
                        }
                    ],
                    "paging": {
                        "cursors": {"after": "cursor-2"},
                        "next": "present",
                    },
                },
            )
        second_page_attempts += 1
        if second_page_attempts == 1:
            return httpx.Response(
                429,
                json={"error": {"message": "rate limited", "code": 4}},
            )
        return httpx.Response(
            200,
            json={
                "data": [
                    {"id": "2", "created_time": "2026-01-01T01:00:00+0000"}
                ]
            },
        )

    provider = MetaGraphProvider(
        httpx.Client(transport=httpx.MockTransport(handler)),
        "page",
        SecretStr("super-secret"),
        "v24.0",
        max_retries=1,
        sleep=lambda _: None,
    )
    posts = list(provider.iter_posts("page", None))

    assert [post.id for post in posts] == ["1", "2"]
    assert cursors == [None, "cursor-2", "cursor-2"]
