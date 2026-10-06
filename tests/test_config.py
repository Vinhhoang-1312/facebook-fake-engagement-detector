from __future__ import annotations

import pytest

from fake_like_detector.config import Settings
from fake_like_detector.security import redact_secrets


def test_mock_settings_need_no_token() -> None:
    settings = Settings(provider="mock", database_url="sqlite:///test.db")
    settings.validate_live()


def test_meta_settings_require_page_id_token_and_version() -> None:
    settings = Settings(provider="meta", database_url="sqlite:///test.db")

    with pytest.raises(ValueError) as exc_info:
        settings.validate_live()

    message = str(exc_info.value)
    assert "META_PAGE_ID" in message
    assert "META_PAGE_ACCESS_TOKEN" in message
    assert "META_GRAPH_API_VERSION" in message


def test_redaction_removes_bearer_query_and_raw_token() -> None:
    token = "EAAG-secret-token"
    text = (
        f"Authorization: Bearer {token}; "
        f"https://graph.facebook.com/posts?access_token={token}; raw={token}"
    )

    redacted = redact_secrets(text, [token])

    assert token not in redacted
    assert "Bearer [REDACTED]" in redacted
    assert "access_token=[REDACTED]" in redacted
