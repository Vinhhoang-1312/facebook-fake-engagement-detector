from __future__ import annotations

import re
from collections.abc import Iterable


def redact_secrets(text: str, secrets: Iterable[str] = ()) -> str:
    """Remove known tokens plus common bearer/query token representations."""

    safe = re.sub(
        r"(?i)(\bBearer\s+)[^\s;,]+",
        r"\1[REDACTED]",
        text,
    )
    safe = re.sub(
        r"(?i)([?&]access_token=)[^&#\s;,]+",
        r"\1[REDACTED]",
        safe,
    )
    for secret in sorted((value for value in secrets if value), key=len, reverse=True):
        safe = safe.replace(secret, "[REDACTED]")
    return safe
