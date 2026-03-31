from __future__ import annotations

import re

from core.booking.common import normalize_phone10


EMAIL_PATTERN = re.compile(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$")


def validate_person_name(value: str) -> tuple[str | None, str | None]:
    normalized = (value or "").strip()
    if len(normalized) < 2:
        return None, "too_short"
    if not normalized.replace(" ", "").replace("-", "").isalpha():
        return None, "invalid_chars"
    return normalized, None


def validate_discount_code(value: str, max_length: int = 100) -> tuple[str, str | None]:
    normalized = (value or "").strip()
    if len(normalized) > max_length:
        return normalized, "too_long"
    return normalized, None


def validate_comment(value: str, max_length: int = 500) -> tuple[str, str | None]:
    normalized = (value or "").strip()
    if len(normalized) > max_length:
        return normalized, "too_long"
    return normalized, None


def validate_optional_email(value: str, *, skip_tokens: set[str] | None = None) -> tuple[str | None, str | None]:
    normalized = (value or "").strip()
    skip_tokens = skip_tokens or set()
    if normalized.lower() in skip_tokens:
        return None, None
    if not EMAIL_PATTERN.match(normalized):
        return None, "invalid"
    return normalized, None


def normalize_and_format_phone(value: str) -> str | None:
    phone10 = normalize_phone10(value)
    if not phone10 or len(phone10) != 10:
        return None
    return f"+7 {phone10[:3]} {phone10[3:6]} {phone10[6:8]} {phone10[8:10]}"


def parse_positive_int(value: str) -> tuple[int | None, str | None]:
    normalized = (value or "").strip()
    try:
        parsed = int(normalized)
    except ValueError:
        return None, "not_integer"

    if parsed < 1:
        return None, "not_positive"
    return parsed, None


def validate_guests_count(guests_count: int, *, max_guests: int) -> str | None:
    if guests_count > max_guests:
        return "too_many"
    return None


def validate_duration_minutes(
    duration: int,
    *,
    min_duration: int,
    max_duration: int = 720,
    step_minutes: int = 60,
) -> str | None:
    if duration > max_duration:
        return "too_large"
    if duration % step_minutes != 0:
        return "invalid_step"
    if duration < min_duration:
        return "too_small"
    return None
