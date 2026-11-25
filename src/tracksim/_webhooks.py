"""Webhook signature verification."""

from __future__ import annotations

import hashlib
import hmac
import json
from collections.abc import Mapping
from typing import Any


def verify_webhook_signature(
    payload: bytes | str | Mapping[str, Any],
    signature: str | None,
    secret: str,
) -> bool:
    """Return ``True`` if ``signature`` matches the webhook ``payload``.

    Args:
        payload: The request body, raw (``bytes``/``str``) or already parsed.
        signature: The value of the ``tracksim-signature`` header.
        secret: The signing secret shown when the webhook was created.
    """
    if not signature or not secret:
        return False
    if isinstance(payload, (bytes, str)):
        try:
            payload = json.loads(payload)
        except ValueError:
            return False
    # TrackSim signs json.dumps() of the parsed body with Python's default
    # separators, so re-serialise instead of hashing the raw bytes.
    message = json.dumps(payload).encode()
    expected = hmac.new(secret.encode(), message, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature.strip().lower())
