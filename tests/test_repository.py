from __future__ import annotations

from datetime import UTC, datetime, timedelta

from fake_like_detector.domain import MetricSnapshot, PageRecord, PostRecord
from fake_like_detector.storage.db import create_engine_and_session
from fake_like_detector.storage.repository import Repository


def make_repo() -> Repository:
    _, session_factory = create_engine_and_session("sqlite+pysqlite:///:memory:")
    return Repository(session_factory)


def test_snapshot_roundtrip_is_idempotent_and_preserves_none_vs_zero() -> None:
    repo = make_repo()
    now = datetime(2026, 1, 1, tzinfo=UTC)
    repo.upsert_page(PageRecord(id="p", name="Page"))
    repo.upsert_post(PostRecord(id="x", page_id="p", created_at=now, media_type="photo"))
    snapshot = MetricSnapshot(
        post_id="x", collected_at=now, reactions=0, comments=3, shares=None,
        available_fields=frozenset({"reactions", "comments"}),
    )
    assert repo.add_snapshot(snapshot) is True
    assert repo.add_snapshot(snapshot) is False
    older = snapshot.model_copy(update={"collected_at": now - timedelta(hours=1)})
    assert repo.add_snapshot(older) is True

    rows = repo.snapshots_for_post("x")
    assert [row.collected_at for row in rows] == [older.collected_at, now]
    assert rows[-1].reactions == 0
    assert rows[-1].shares is None
    assert rows[-1].available_fields == frozenset({"reactions", "comments"})

