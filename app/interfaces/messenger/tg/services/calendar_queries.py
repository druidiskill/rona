from datetime import datetime

from app.integrations.local.db import client_repo
from app.interfaces.messenger.tg.services.contact_utils import format_phone_for_search

try:
    from app.integrations.local.calendar.service import GoogleCalendarService
    CALENDAR_AVAILABLE = True
except Exception:
    GoogleCalendarService = None
    CALENDAR_AVAILABLE = False


def is_calendar_available() -> bool:
    return bool(CALENDAR_AVAILABLE and GoogleCalendarService)


async def list_events(
    period_start: datetime,
    period_end: datetime,
    max_results: int = 250,
    query: str | None = None,
) -> list[dict]:
    if not is_calendar_available():
        return []
    calendar_service = GoogleCalendarService()
    return await calendar_service.list_events(
        period_start,
        period_end,
        max_results=max_results,
        query=query,
    )


async def get_event(event_id: str) -> dict | None:
    if not is_calendar_available():
        return None
    calendar_service = GoogleCalendarService()
    return await calendar_service.get_event(event_id)


async def delete_event(event_id: str) -> bool:
    if not is_calendar_available():
        return False
    calendar_service = GoogleCalendarService()
    return await calendar_service.delete_event(event_id)


async def get_user_calendar_events_by_telegram_id(
    telegram_id: int,
    period_start: datetime,
    period_end: datetime,
) -> tuple[list[dict] | None, str | None]:
    if not is_calendar_available():
        return None, "calendar_unavailable"

    client = await client_repo.get_by_telegram_id(telegram_id)
    phone_display = format_phone_for_search(client.phone if client else None)
    if not phone_display:
        return [], None

    events = await list_events(period_start, period_end)
    user_events = [
        event for event in events
        if phone_display in (event.get("description") or "")
    ]
    return user_events, None


async def get_user_calendar_events_by_vk_id(
    vk_id: int,
    period_start: datetime,
    period_end: datetime,
) -> tuple[list[dict] | None, str | None]:
    if not is_calendar_available():
        return None, "calendar_unavailable"

    client = await client_repo.get_by_vk_id(vk_id)
    phone_display = format_phone_for_search(client.phone if client else None)
    if not phone_display:
        return [], None

    events = await list_events(period_start, period_end)
    user_events = [
        event for event in events
        if phone_display in (event.get("description") or "")
    ]
    return user_events, None
