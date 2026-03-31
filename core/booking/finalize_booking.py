from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Awaitable, Callable

from core.booking.calendar_event import CalendarCreateResult, create_booking_calendar_event
from core.booking.presentation import build_booking_summary


@dataclass
class FinalizeBookingResult:
    summary: dict
    calendar_result: CalendarCreateResult


async def finalize_booking(
    *,
    booking_data: dict,
    service_name: str,
    service_id: int,
    date_display: str,
    time_range: str,
    duration_minutes: int,
    event_start: datetime,
    event_end: datetime,
    calendar_available: bool,
    calendar_service_cls,
    calendar_description: str | None = None,
    sync_client: Callable[[], Awaitable[None]] | None = None,
) -> FinalizeBookingResult:
    summary = build_booking_summary(
        booking_data=booking_data,
        service_name=service_name,
        service_id=service_id,
        date_display=date_display,
        time_range=time_range,
        duration_minutes=duration_minutes,
    )

    if calendar_description:
        calendar_result = await create_booking_calendar_event(
            calendar_available=calendar_available,
            calendar_service_cls=calendar_service_cls,
            title=service_name,
            description=calendar_description,
            start_time=event_start,
            end_time=event_end,
        )
    else:
        calendar_result = CalendarCreateResult(created=False)

    if sync_client:
        await sync_client()

    return FinalizeBookingResult(summary=summary, calendar_result=calendar_result)
