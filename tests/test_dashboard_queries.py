from __future__ import annotations

from datetime import UTC, datetime

from fake_like_detector.dashboard.queries import DashboardRepository
from fake_like_detector.domain import MetricSnapshot, PageRecord, PostRecord
from fake_like_detector.storage.db import create_engine_and_session
from fake_like_detector.storage.repository import Repository


def test_dashboard_distinguishes_zero_from_unavailable() -> None:
    _, factory = create_engine_and_session("sqlite+pysqlite:///:memory:")
    repository = Repository(factory)
    at = datetime(2026, 1, 1, tzinfo=UTC)
    repository.upsert_page(PageRecord(id="page", name="Page"))
    repository.upsert_post(PostRecord(id="post", page_id="page", created_at=at))
    repository.add_snapshot(MetricSnapshot(post_id="post", collected_at=at, reactions=0, comments=None, shares=0, available_fields=frozenset({"reactions", "shares"})))

    view = DashboardRepository(repository).posts()[0]
    health = DashboardRepository(repository).data_health()
    assert view.reactions == "0"
    assert view.comments == "Not available"
    assert view.shares == "0"
    assert health.comments_coverage == 0
    assert health.reactions_coverage == 1
