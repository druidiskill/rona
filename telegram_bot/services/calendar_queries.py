from datetime import datetime

from database import client_repo
from telegram_bot.services.contact_utils import format_phone_for_search

try:
    from google_calendar.calendar_service import GoogleCalendarService
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
    return calendar_service._service.events().get(
        calendarId=calendar_service.calendar_id,
        eventId=event_id,
    ).execute()


async def delete_event(event_id: str) -> bool:
    if not is_calendar_available():
        return False
    calendar_service = GoogleCalendarService()
    calendar_service._service.events().delete(
        calendarId=calendar_service.calendar_id,
        eventId=event_id,
    ).execute()
    return True


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
