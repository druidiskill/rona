from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any


@dataclass
class CalendarCreateResult:
    created: bool
    payload: dict[str, Any] | None = None
    error: Exception | None = None


async def create_booking_calendar_event(
    *,
    calendar_available: bool,
    calendar_service_cls,
    title: str,
    description: str,
    start_time: datetime,
    end_time: datetime,
) -> CalendarCreateResult:
    if not calendar_available or not calendar_service_cls:
        return CalendarCreateResult(created=False)

    try:
        calendar_service = calendar_service_cls()
        payload = await calendar_service.create_event(
            title=title,
            description=description,
            start_time=start_time,
            end_time=end_time,
        )
        return CalendarCreateResult(created=True, payload=payload)
    except Exception as exc:
        return CalendarCreateResult(created=False, error=exc)
