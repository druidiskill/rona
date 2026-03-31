from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta


@dataclass(slots=True)
class AdminBookingsListResult:
    status: str
    text: str
    events: list[dict]


@dataclass(slots=True)
class AdminBookingDetailResult:
    status: str
    text: str
    chat_target_user_id: str | None = None


@dataclass(slots=True)
class AdminBookingSearchResult:
    status: str
    text: str
    events: list[dict]


def _build_admin_period_bookings_text(title: str, events: list[dict], *, include_date: bool = False) -> str:
    text = f"📅 <b>{title}</b>\n\n"
    for event in events:
        start = event.get("start")
        if not start:
            continue
        summary = event.get("summary", "Без названия")
        if include_date:
            text += f"🕐 {start.strftime('%d.%m %H:%M')} — {summary}\n"
        else:
            text += f"🕐 {start.strftime('%H:%M')} — {summary}\n\n"
    return text


async def load_admin_period_bookings(
    *,
    title: str,
    empty_text: str,
    period_start: datetime,
    period_end: datetime,
    is_calendar_available,
    list_events,
    max_results: int = 250,
    include_date: bool = False,
) -> AdminBookingsListResult:
    if not is_calendar_available():
        return AdminBookingsListResult(
            status="calendar_unavailable",
            text=(
                f"📅 <b>{title}</b>\n\n"
                "Google Calendar недоступен. Проверьте настройки и токены."
            ),
            events=[],
        )

    try:
        events = await list_events(period_start, period_end, max_results=max_results)
    except Exception:
        return AdminBookingsListResult(
            status="load_error",
            text=(
                f"📅 <b>{title}</b>\n\n"
                "Не удалось получить данные из календаря."
            ),
            events=[],
        )

    visible_events = [event for event in events if event.get("start")]
    if not visible_events:
        return AdminBookingsListResult(
            status="empty",
            text=f"📅 <b>{title}</b>\n\n{empty_text}",
            events=[],
        )

    return AdminBookingsListResult(
        status="ok",
        text=_build_admin_period_bookings_text(title, visible_events, include_date=include_date),
        events=visible_events,
    )


async def load_admin_future_bookings(*, is_calendar_available, list_events) -> AdminBookingsListResult:
    if not is_calendar_available():
        return AdminBookingsListResult(
            status="calendar_unavailable",
            text=(
                "📅 <b>Бронирования</b>\n\n"
                "Google Calendar недоступен. Проверьте настройки и токены."
            ),
            events=[],
        )

    period_start = datetime.now()
    period_end = period_start + timedelta(days=365)
    try:
        events = await list_events(period_start, period_end, max_results=250)
    except Exception:
        return AdminBookingsListResult(
            status="load_error",
            text=(
                "📅 <b>Бронирования</b>\n\n"
                "Не удалось получить данные из календаря."
            ),
            events=[],
        )

    future_events = [event for event in events if event.get("start")]
    if not future_events:
        return AdminBookingsListResult(
            status="empty",
            text=(
                "📅 <b>Бронирования</b>\n\n"
                "Будущих бронирований нет."
            ),
            events=[],
        )

    return AdminBookingsListResult(
        status="ok",
        text=(
            "📅 <b>Будущие бронирования</b>\n\n"
            "Выберите бронирование для просмотра деталей:"
        ),
        events=future_events,
    )


async def load_admin_booking_detail(
    *,
    event_id: str,
    is_calendar_available,
    get_event,
    extract_contact_details,
    normalize_phone,
    client_repo,
) -> AdminBookingDetailResult:
    if not is_calendar_available():
        return AdminBookingDetailResult(
            status="calendar_unavailable",
            text="Google Calendar недоступен",
        )

    try:
        raw_event = await get_event(event_id)
    except Exception:
        return AdminBookingDetailResult(
            status="load_error",
            text="Не удалось получить бронирование",
        )

    if not raw_event:
        return AdminBookingDetailResult(
            status="not_found",
            text="Не удалось получить бронирование",
        )

    summary = raw_event.get("summary", "Без названия")
    description = raw_event.get("description", "")
    start_raw = raw_event.get("start", {})
    end_raw = raw_event.get("end", {})
    start = start_raw.get("dateTime") or start_raw.get("date")
    end = end_raw.get("dateTime") or end_raw.get("date")

    start_dt = None
    end_dt = None
    try:
        if start and "T" in start:
            start_dt = datetime.fromisoformat(start)
        if end and "T" in end:
            end_dt = datetime.fromisoformat(end)
    except Exception:
        pass

    contact = extract_contact_details(description)

    chat_target_user_id = contact.get("telegram_id")
    if not chat_target_user_id:
        try:
            phone_norm = normalize_phone(contact.get("phone"))
            db_client = None
            if phone_norm:
                db_client = await client_repo.get_by_phone(phone_norm)
            if (not db_client) and contact.get("email"):
                clients = await client_repo.get_all() if hasattr(client_repo, "get_all") else []
                email_lc = contact["email"].strip().lower()
                for client in clients:
                    if client.email and client.email.strip().lower() == email_lc:
                        db_client = client
                        break
            if db_client and db_client.telegram_id:
                chat_target_user_id = str(db_client.telegram_id)
        except Exception:
            pass

    text = "📋 <b>Информация о бронировании</b>\n\n"
    text += f"🎯 <b>Услуга:</b> {summary}\n"
    if start_dt:
        text += f"📅 <b>Дата:</b> {start_dt.strftime('%d.%m.%Y')}\n"
        text += f"🕒 <b>Время:</b> {start_dt.strftime('%H:%M')}"
        if end_dt:
            text += f" - {end_dt.strftime('%H:%M')}"
        text += "\n"

    text += "\n📞 <b>Данные для связи</b>\n"
    text += f"👤 <b>Клиент:</b> {contact['name'] or 'Не указан'}\n"
    text += f"📱 <b>Телефон:</b> {contact['phone'] or 'Не указан'}\n"
    text += f"📧 <b>Email:</b> {contact['email'] or 'Не указан'}\n"
    if not chat_target_user_id:
        text += (
            "⚠️ <i>Для этого бронирования внутренний чат недоступен: "
            "не найден Telegram ID клиента.</i>\n"
        )

    return AdminBookingDetailResult(
        status="ok",
        text=text,
        chat_target_user_id=chat_target_user_id,
    )


async def cancel_admin_booking_event(*, event_id: str, is_calendar_available, list_events, delete_event) -> str:
    if not is_calendar_available():
        return "calendar_unavailable"

    now = datetime.now()
    period_start = now - timedelta(days=30)
    period_end = now + timedelta(days=365)

    try:
        try:
            all_events = await list_events(period_start, period_end, max_results=250)
            marker = f"Связано с событием: {event_id}"
            linked_events = [
                event for event in all_events
                if marker in (event.get("description") or "")
                and "Service ID: 9" in (event.get("description") or "")
            ]
            for linked in linked_events:
                linked_id = linked.get("id")
                if linked_id:
                    await delete_event(linked_id)
        except Exception:
            pass

        await delete_event(event_id)
        return "ok"
    except Exception:
        return "delete_error"


async def search_admin_bookings(
    *,
    query: str,
    is_calendar_available,
    list_events,
) -> AdminBookingSearchResult:
    normalized_query = query.strip()
    if len(normalized_query) < 2:
        return AdminBookingSearchResult(
            status="validation_error",
            text="❌ Введите минимум 2 символа для поиска.",
            events=[],
        )

    if not is_calendar_available():
        return AdminBookingSearchResult(
            status="calendar_unavailable",
            text="Google Calendar недоступен. Проверьте настройки и токены.",
            events=[],
        )

    now = datetime.now()
    period_start = now - timedelta(days=30)
    period_end = now + timedelta(days=180)

    try:
        events = await list_events(
            period_start,
            period_end,
            query=normalized_query,
            max_results=30,
        )
    except Exception:
        return AdminBookingSearchResult(
            status="load_error",
            text="❌ Ошибка поиска в календаре. Попробуйте позже.",
            events=[],
        )

    visible_events = [event for event in events if event.get("start")]
    if not visible_events:
        return AdminBookingSearchResult(
            status="empty",
            text=f"🔍 По запросу <b>{normalized_query}</b> ничего не найдено.",
            events=[],
        )

    text = f"🔍 <b>Результаты поиска: {normalized_query}</b>\n\n"
    for event in visible_events:
        start = event.get("start")
        summary = event.get("summary", "Без названия")
        text += f"🕐 {start.strftime('%d.%m %H:%M')} — {summary}\n"

    return AdminBookingSearchResult(
        status="ok",
        text=text,
        events=visible_events,
    )
