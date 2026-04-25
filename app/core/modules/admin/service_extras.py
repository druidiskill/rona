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


def normalize_extra_service_ids(value) -> list[int]:
    """Normalize stored extra-service ids from CSV/int/None into a clean integer list."""
    if value is None:
        return []
    if isinstance(value, int):
        return [value] if value > 0 else []
    if isinstance(value, str):
        parts = [part.strip() for part in value.split(",") if part.strip()]
        try:
            return [int(part) for part in parts]
        except ValueError:
            return []
    return []


def serialize_extra_service_ids(extra_service_ids: Iterable[int]) -> str:
    """Serialize extra-service ids back into DB CSV format."""
    unique_ids = []
    seen: set[int] = set()
    for value in extra_service_ids:
        try:
            extra_id = int(value)
        except (TypeError, ValueError):
            continue
        if extra_id <= 0 or extra_id in seen:
            continue
        seen.add(extra_id)
        unique_ids.append(extra_id)
    return ",".join(map(str, unique_ids))


async def cleanup_deleted_extra_service(service_repo, extra_service_id: int) -> int:
    """Remove deleted extra-service id from every main service that references it."""
    affected = 0
    for service in await service_repo.get_all():
        selected_ids = normalize_extra_service_ids(getattr(service, "plus_service_ids", None))
        if extra_service_id not in selected_ids:
            continue
        service.plus_service_ids = serialize_extra_service_ids(
            current_id for current_id in selected_ids if current_id != extra_service_id
        )
        await service_repo.update(service)
        affected += 1
    return affected
