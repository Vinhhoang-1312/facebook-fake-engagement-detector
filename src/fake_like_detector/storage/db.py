from __future__ import annotations

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from fake_like_detector.storage.models import Base


def create_engine_and_session(database_url: str) -> tuple[Engine, sessionmaker[Session]]:
    kwargs: dict[str, object] = {"future": True}
    if database_url.startswith("sqlite"):
        kwargs["connect_args"] = {"check_same_thread": False}
    if ":memory:" in database_url:
        kwargs["poolclass"] = StaticPool
    engine = create_engine(database_url, **kwargs)
    Base.metadata.create_all(engine)
    return engine, sessionmaker(engine, expire_on_commit=False)

