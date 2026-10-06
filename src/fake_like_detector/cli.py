from __future__ import annotations

import subprocess
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

import httpx
import typer

from fake_like_detector.collection import collect_page
from fake_like_detector.config import Settings
from fake_like_detector.detection.service import AssessmentService
from fake_like_detector.providers.base import PageDataProvider
from fake_like_detector.providers.meta import MetaGraphProvider
from fake_like_detector.providers.mock import MockProvider
from fake_like_detector.storage.db import create_engine_and_session
from fake_like_detector.storage.repository import Repository

app = typer.Typer(help="Detect explainable anomalies in authorized Facebook Page engagement data.")


def _repository(settings: Settings) -> Repository:
    _, factory = create_engine_and_session(settings.database_url)
    return Repository(factory)


@app.command("init-db")
def init_db() -> None:
    settings = Settings()
    _repository(settings)
    typer.echo("Database initialized.")


@app.command()
def demo() -> None:
    settings = Settings()
    repository = _repository(settings)
    provider = MockProvider.demo()
    start = provider.epoch
    first = collect_page(provider, repository, provider.page.id, start)
    second = collect_page(provider, repository, provider.page.id, start + timedelta(hours=1))
    typer.echo(f"Collected {first.snapshots_added + second.snapshots_added} snapshots ({second.snapshots_added} new in second run).")
    service = AssessmentService(repository)
    for post in repository.list_posts():
        assessment = service.assess_post(post.id, start + timedelta(hours=2))
        typer.echo(f"{post.id}: {assessment.level} score={assessment.score:.3f} confidence={assessment.confidence:.3f}")


@app.command()
def analyze() -> None:
    settings = Settings()
    repository = _repository(settings)
    service = AssessmentService(repository)
    posts = repository.list_posts()
    if not posts:
        typer.echo("No data. Run demo or collect first.")
        raise typer.Exit(1)
    typer.echo("Risk is anomaly evidence, not fake-account percentage.")
    for post in posts:
        assessment = service.assess_post(post.id, datetime.now(UTC))
        typer.echo(f"{post.id}: {assessment.level} score={assessment.score:.3f} coverage={assessment.coverage:.2f}")


@app.command()
def collect(at: str | None = typer.Option(None, help="UTC ISO timestamp")) -> None:
    settings = Settings()
    repository = _repository(settings)
    collected_at = datetime.fromisoformat(at) if at else datetime.now(UTC)
    if collected_at.tzinfo is None:
        collected_at = collected_at.replace(tzinfo=UTC)
    provider: PageDataProvider
    if settings.provider == "mock":
        provider = MockProvider.demo()
        page_id = provider.page.id
    else:
        settings.validate_live()
        assert settings.meta_page_id and settings.meta_page_access_token and settings.meta_graph_api_version
        provider = MetaGraphProvider(httpx.Client(timeout=30), settings.meta_page_id, settings.meta_page_access_token, settings.meta_graph_api_version)
        page_id = settings.meta_page_id
    summary = collect_page(provider, repository, page_id, collected_at)
    typer.echo(f"{summary.status}: posts={summary.posts_seen}, new_snapshots={summary.snapshots_added}")


@app.command("audit-fields")
def audit_fields() -> None:
    settings = Settings()
    settings.validate_live()
    assert settings.meta_page_id and settings.meta_page_access_token and settings.meta_graph_api_version
    with httpx.Client(timeout=30) as client:
        report = MetaGraphProvider(client, settings.meta_page_id, settings.meta_page_access_token, settings.meta_graph_api_version).audit_fields()
    typer.echo(f"Accessible: {', '.join(report.accessible) or 'none'}")
    typer.echo(f"Unavailable: {', '.join(report.unavailable) or 'none'}")


@app.command()
def serve() -> None:
    app_path = Path(__file__).parent / "dashboard" / "app.py"
    raise typer.Exit(subprocess.call([sys.executable, "-m", "streamlit", "run", str(app_path)]))


if __name__ == "__main__":
    app()
