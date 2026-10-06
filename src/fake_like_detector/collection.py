from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from fake_like_detector.domain import CollectionRun
from fake_like_detector.providers.base import PageDataProvider, ProviderError
from fake_like_detector.security import redact_secrets
from fake_like_detector.storage.repository import Repository


@dataclass(frozen=True)
class CollectionSummary:
    run_id: str
    posts_seen: int
    snapshots_added: int
    status: str


def collect_page(provider: PageDataProvider, repository: Repository, page_id: str, collected_at: datetime) -> CollectionSummary:
    run = CollectionRun(page_id=page_id, started_at=collected_at)
    repository.save_collection_run(run)
    posts_seen = 0
    snapshots_added = 0
    try:
        repository.upsert_page(provider.fetch_page(page_id))
        for post in provider.iter_posts(page_id, None):
            posts_seen += 1
            repository.upsert_post(post)
            if repository.add_snapshot(provider.fetch_snapshot(post.id, collected_at)):
                snapshots_added += 1
        final = run.model_copy(update={"completed_at": collected_at, "status": "success", "posts_seen": posts_seen, "snapshots_added": snapshots_added})
        repository.save_collection_run(final)
        return CollectionSummary(run.run_id, posts_seen, snapshots_added, "success")
    except (ProviderError, ValueError) as exc:
        final = run.model_copy(update={"completed_at": collected_at, "status": "failed", "posts_seen": posts_seen, "snapshots_added": snapshots_added, "error": redact_secrets(str(exc))})
        repository.save_collection_run(final)
        raise
