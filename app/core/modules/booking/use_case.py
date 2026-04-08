from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Awaitable, Callable

from app.core.modules.booking.finalize_booking import FinalizeBookingResult, finalize_booking


@dataclass
class CreateBookingUseCaseResult:
    summary: dict
    finalize_result: FinalizeBookingResult
    admin_notification: Any = None


async def create_booking_use_case(
    *,
    booking_data: dict,
    service_name: str,
    service_id: int,
    date_display: str,
    time_range: str,
    duration_minutes: int,
    event_start,
    event_end,
    calendar_available: bool,
    calendar_service_cls,
    calendar_description: str | None = None,
    sync_client: Callable[[], Awaitable[None]] | None = None,
    admin_notification_builder: Callable[[dict], Any] | None = None,
) -> CreateBookingUseCaseResult:
    finalize_result = await finalize_booking(
        booking_data=booking_data,
        service_name=service_name,
        service_id=service_id,
        date_display=date_display,
        time_range=time_range,
        duration_minutes=duration_minutes,
        event_start=event_start,
        event_end=event_end,
        calendar_available=calendar_available,
        calendar_service_cls=calendar_service_cls,
        calendar_description=calendar_description,
        sync_client=sync_client,
    )
    summary = finalize_result.summary
    admin_notification = admin_notification_builder(summary) if admin_notification_builder else None
    return CreateBookingUseCaseResult(
        summary=summary,
        finalize_result=finalize_result,
        admin_notification=admin_notification,
    )
