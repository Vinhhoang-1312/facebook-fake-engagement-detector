from __future__ import annotations

from collections.abc import Iterator
from datetime import UTC, datetime

from fake_like_detector.domain import MetricSnapshot, PageRecord, PostRecord


class MockProvider:
    def __init__(self, page: PageRecord, posts: tuple[PostRecord, ...], epoch: datetime) -> None:
        self.page = page
        self.posts = posts
        self.epoch = epoch

    @classmethod
    def demo(cls) -> MockProvider:
        epoch = datetime(2026, 1, 1, tzinfo=UTC)
        posts = tuple(
            PostRecord(id=f"organic-{index}", page_id="demo-page", created_at=epoch, media_type="photo", paid_status="organic", message=f"Organic example {index}")
            for index in range(9)
        ) + (
            PostRecord(id="burst", page_id="demo-page", created_at=epoch, media_type="photo", paid_status="organic", message="Synthetic burst example"),
        )
        return cls(PageRecord(id="demo-page", name="Demo Page", followers_count=31_000), posts, epoch)

    def fetch_page(self, page_id: str) -> PageRecord:
        if page_id != self.page.id:
            raise ValueError(f"Unknown mock page: {page_id}")
        return self.page

    def iter_posts(self, page_id: str, since: datetime | None) -> Iterator[PostRecord]:
        for post in self.posts:
            if since is None or post.created_at >= since:
                yield post

    def fetch_snapshot(self, post_id: str, collected_at: datetime) -> MetricSnapshot:
        elapsed_hours = max(0, int((collected_at - self.epoch).total_seconds() // 3600))
        if post_id == "burst":
            reactions = 90 + (900 if elapsed_hours >= 1 else 0)
            comments = 2
            shares = 1
        else:
            index = int(post_id.rsplit("-", 1)[-1])
            reactions = 80 + index + elapsed_hours * (5 + index)
            comments = 8 + index % 3
            shares = 3 + index % 2
        return MetricSnapshot(post_id=post_id, collected_at=collected_at, reactions=reactions, comments=comments, shares=shares, views=None, available_fields=frozenset({"reactions", "comments", "shares"}))

