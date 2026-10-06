from __future__ import annotations

from datetime import UTC, datetime

from fake_like_detector.collection import collect_page
from fake_like_detector.providers.mock import MockProvider
from fake_like_detector.storage.db import create_engine_and_session
from fake_like_detector.storage.repository import Repository


def test_mock_collection_is_repeatable_and_idempotent() -> None:
    _, factory = create_engine_and_session("sqlite+pysqlite:///:memory:")
    repo = Repository(factory)
    provider = MockProvider.demo()
    at = datetime(2026, 1, 2, tzinfo=UTC)
    first = collect_page(provider, repo, "demo-page", at)
    second = collect_page(provider, repo, "demo-page", at)
    assert first.posts_seen >= 9
    assert first.snapshots_added == first.posts_seen
    assert second.snapshots_added == 0

