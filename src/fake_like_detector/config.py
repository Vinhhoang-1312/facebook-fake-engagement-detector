from __future__ import annotations

from typing import Literal

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime configuration loaded from FLED_* variables and an optional .env file."""

    model_config = SettingsConfigDict(
        env_prefix="FLED_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    provider: Literal["mock", "meta"] = "mock"
    database_url: str = "sqlite:///fake_like_detector.db"
    meta_page_id: str | None = None
    meta_page_access_token: SecretStr | None = None
    meta_graph_api_version: str | None = None

    def validate_live(self) -> None:
        if self.provider != "meta":
            return
        missing: list[str] = []
        if not self.meta_page_id:
            missing.append("FLED_META_PAGE_ID")
        if self.meta_page_access_token is None or not self.meta_page_access_token.get_secret_value():
            missing.append("FLED_META_PAGE_ACCESS_TOKEN")
        if not self.meta_graph_api_version:
            missing.append("FLED_META_GRAPH_API_VERSION")
        if missing:
            raise ValueError("Missing live configuration: " + ", ".join(missing))
