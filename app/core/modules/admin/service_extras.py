"""Common helpers for selecting extra services in admin flows."""

from __future__ import annotations

from typing import Iterable


def get_active_extra_services(services: Iterable, exclude_service_id: int | None = None) -> list:
    """Return active services available for extras selection."""
    return [
        service
        for service in services
        if getattr(service, "is_active", False)
        and (exclude_service_id is None or getattr(service, "id", None) != exclude_service_id)
    ]


def toggle_extra_service(selected_ids: Iterable[int], service_id: int) -> tuple[list[int], bool]:
    """Toggle service id in selection and return updated ids plus added/removed flag."""
    updated = list(selected_ids)
    if service_id in updated:
        updated.remove(service_id)
        return updated, False
    updated.append(service_id)
    return updated, True


def format_selected_extras(service_ids: Iterable[int], services: Iterable) -> str:
    """Return human readable selected extras summary."""
    selected = {service_id for service_id in service_ids}
    names = [service.name for service in services if getattr(service, "id", None) in selected]
    return ", ".join(names) if names else "Не выбрано"
