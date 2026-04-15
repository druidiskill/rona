from __future__ import annotations

from typing import Iterable


def build_extra_service_booking_label(extra_service) -> str:
    name = str(getattr(extra_service, "name", "") or "").strip()
    price_text = str(getattr(extra_service, "price_text", "") or "").strip()
    if not price_text:
        return name
    return f"{name} ({price_text})"


def build_extra_service_label_map(extra_services: Iterable) -> dict[str, str]:
    return {
        str(int(getattr(extra_service, "id"))): str(getattr(extra_service, "name", "") or "").strip()
        for extra_service in extra_services
        if getattr(extra_service, "id", None) is not None
    }


def format_extra_labels(extras: Iterable, extra_labels: dict | None = None) -> str:
    items = list(extras or [])
    if not items:
        return "Нет"

    labels = extra_labels or {}
    formatted: list[str] = []
    for item in items:
        if isinstance(item, int):
            formatted.append(labels.get(str(item), labels.get(item, str(item))))
            continue
        if isinstance(item, str) and item.isdigit():
            formatted.append(labels.get(item, labels.get(int(item), item)))
            continue
        formatted.append(labels.get(item, str(item)) if isinstance(labels, dict) else str(item))
    return ", ".join(formatted)


def has_extra_named(extras: Iterable, extra_labels: dict | None, needle: str) -> bool:
    lowered = needle.strip().lower()
    labels_text = format_extra_labels(extras, extra_labels)
    return lowered in labels_text.lower()
