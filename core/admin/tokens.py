from __future__ import annotations

import hashlib


_ADMIN_BOOKING_TOKEN_MAP: dict[str, tuple[str, int]] = {}


def register_admin_booking_token(user_id: int, event_id: str) -> str:
    token_source = f"{user_id}:{event_id}"
    token = hashlib.sha1(token_source.encode("utf-8")).hexdigest()[:12]
    _ADMIN_BOOKING_TOKEN_MAP[token] = (event_id, user_id)
    return token


def resolve_admin_booking_token(token_or_event_id: str, user_id: int) -> tuple[str | None, str | None]:
    entry = _ADMIN_BOOKING_TOKEN_MAP.get(token_or_event_id)
    if entry:
        mapped_event_id, mapped_user_id = entry
        if mapped_user_id != user_id:
            return None, "access_denied"
        return mapped_event_id, None

    if len(token_or_event_id) <= 16 and token_or_event_id.isalnum():
        return None, "stale"
    return token_or_event_id, None
