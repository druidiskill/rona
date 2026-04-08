from datetime import datetime, timedelta

from vkbottle.bot import Bot, Message

from app.integrations.local.db import client_service, service_repo
from app.interfaces.messenger.tg.services.calendar_queries import (
    delete_event,
    get_user_calendar_events_by_vk_id,
    is_calendar_available,
    list_events,
)
from app.interfaces.messenger.vk.auth import is_vk_admin_id
from app.interfaces.messenger.vk.handlers.booking import get_services_booking_keyboard
from app.interfaces.messenger.vk.handlers.help import forward_question_to_vk_admins, send_faq_list
from app.interfaces.messenger.vk.keyboards import (
    get_active_booking_actions_keyboard,
    get_active_bookings_keyboard,
    get_back_to_main_keyboard,
    get_booking_history_keyboard,
    get_main_menu_keyboard,
    get_my_bookings_keyboard,
)
def _normalize_text(text: str | None) -> str:
    if not text:
        return ""
    return " ".join(text.strip().lower().split())


def _strip_leading_emoji(text: str) -> str:
    # Для кнопок вида "🏠 Главное меню" или "📸 Услуги"
    if not text:
        return text
    parts = text.split(" ", 1)
    if len(parts) == 2 and len(parts[0]) <= 3:
        return parts[1]
    return text


async def _send_main_menu(message: Message):
    vk_first_name = "Пользователь"
    try:
        user = await message.get_user()
        if getattr(user, "first_name", None):
            vk_first_name = str(user.first_name).strip()
    except Exception:
        pass

    client = await client_service.get_or_create_client(
        vk_id=message.from_id,
        name=vk_first_name,
    )
    greeting_name = vk_first_name
    if client and client.name and client.name.strip() and client.name != "Пользователь":
        greeting_name = client.name.strip()
    elif client and vk_first_name != "Пользователь" and client.name != vk_first_name:
        client.name = vk_first_name
        await client_service.client_repo.update(client)

    is_admin = await is_vk_admin_id(message.from_id)
    text = (
        "🎉 Добро пожаловать в фотостудию!\n\n"
        f"Привет, {greeting_name}! 👋\n\n"
        "Выберите действие в меню ниже:"
    )
    await message.answer(text, keyboard=get_main_menu_keyboard(is_admin=is_admin))


async def _send_services(message: Message):
    services = await service_repo.get_all_active()
    if not services:
        await message.answer(
            "📸 Сейчас нет доступных услуг.",
            keyboard=get_back_to_main_keyboard(is_admin=await is_vk_admin_id(message.from_id)),
        )
        return

    lines = ["📸 Наши услуги:\n"]
    for service in services:
        lines.append(f"• {service.name} — от {service.price_min}₽")
    lines.append("\nВыберите услугу кнопкой ниже:")
    await message.answer("\n".join(lines), keyboard=get_services_booking_keyboard(services))


def _paginate_events(events: list[dict], page: int, page_size: int = 6) -> tuple[list[dict], int, int]:
    total = len(events)
    total_pages = max(1, (total + page_size - 1) // page_size)
    page = max(0, min(page, total_pages - 1))
    start = page * page_size
    end = start + page_size
    return events[start:end], total_pages, page


async def _get_vk_user_bookings(message: Message, *, history: bool) -> tuple[list[dict] | None, str | None]:
    if not is_calendar_available():
        return None, "calendar_unavailable"

    now = datetime.now()
    return await get_user_calendar_events_by_vk_id(
        vk_id=message.from_id,
        period_start=now - timedelta(days=180) if history else now,
        period_end=now if history else now + timedelta(days=90),
    )


async def _send_my_bookings_menu(message: Message):
    await message.answer(
        "📅 Мои бронирования\n\nВыберите раздел:",
        keyboard=get_my_bookings_keyboard(),
    )


async def _send_active_bookings(message: Message, page: int = 0):
    events, error_code = await _get_vk_user_bookings(message, history=False)
    if error_code == "calendar_unavailable":
        await message.answer(
            "Google Calendar недоступен. Проверьте настройки.",
            keyboard=get_back_to_main_keyboard(is_admin=await is_vk_admin_id(message.from_id)),
        )
        return
    if not events:
        await message.answer(
            "📅 Активные бронирования\n\nУ вас пока нет активных бронирований.",
            keyboard=get_my_bookings_keyboard(),
        )
        return

    page_items, total_pages, page = _paginate_events(events, page)
    text_lines = ["📅 Активные бронирования\n", "Выберите бронирование кнопкой ниже:\n"]
    for event in page_items:
        start = event.get("start")
        summary = event.get("summary") or "Без названия"
        if not start:
            continue
        text_lines.append(f"• {start.strftime('%d.%m.%Y %H:%M')} — {summary}")
    if total_pages > 1:
        text_lines.append(f"\nСтраница {page + 1} из {total_pages}")
    await message.answer(
        "\n".join(text_lines),
        keyboard=get_active_bookings_keyboard(page_items, page, total_pages),
    )


async def _send_booking_history(message: Message, page: int = 0):
    events, error_code = await _get_vk_user_bookings(message, history=True)
    if error_code == "calendar_unavailable":
        await message.answer(
            "Google Calendar недоступен. Проверьте настройки.",
            keyboard=get_back_to_main_keyboard(is_admin=await is_vk_admin_id(message.from_id)),
        )
        return
    if not events:
        await message.answer(
            "🕘 История бронирований\n\nИстория пока пуста.",
            keyboard=get_my_bookings_keyboard(),
        )
        return

    page_items, total_pages, page = _paginate_events(events, page)
    text_lines = ["🕘 История бронирований\n"]
    for event in page_items:
        start = event.get("start")
        summary = event.get("summary") or "Без названия"
        if not start:
            continue
        text_lines.append(f"• {start.strftime('%d.%m.%Y %H:%M')} — {summary}")
    if total_pages > 1:
        text_lines.append(f"\nСтраница {page + 1} из {total_pages}")

    await message.answer(
        "\n".join(text_lines),
        keyboard=get_booking_history_keyboard(page, total_pages),
    )


async def _send_active_booking_detail(message: Message, event_id: str, page: int = 0):
    events, error_code = await _get_vk_user_bookings(message, history=False)
    if error_code == "calendar_unavailable":
        await message.answer(
            "Google Calendar недоступен. Проверьте настройки.",
            keyboard=get_back_to_main_keyboard(is_admin=await is_vk_admin_id(message.from_id)),
        )
        return
    event = next((item for item in (events or []) if item.get("id") == event_id), None)
    if not event:
        await message.answer(
            "Бронирование не найдено.",
            keyboard=get_my_bookings_keyboard(),
        )
        return

    start = event.get("start")
    end = event.get("end")
    summary = event.get("summary") or "Без названия"
    lines = ["✏️ Управление бронированием\n"]
    lines.append(f"🎯 Услуга: {summary}")
    if start:
        lines.append(f"📅 Дата: {start.strftime('%d.%m.%Y')}")
        time_line = f"🕒 Время: {start.strftime('%H:%M')}"
        if end:
            time_line += f" - {end.strftime('%H:%M')}"
        lines.append(time_line)

    await message.answer(
        "\n".join(lines),
        keyboard=get_active_booking_actions_keyboard(event_id, page),
    )


async def _cancel_active_booking(message: Message, event_id: str):
    events, error_code = await _get_vk_user_bookings(message, history=False)
    if error_code == "calendar_unavailable":
        await message.answer(
            "Google Calendar недоступен. Проверьте настройки.",
            keyboard=get_back_to_main_keyboard(is_admin=await is_vk_admin_id(message.from_id)),
        )
        return
    event = next((item for item in (events or []) if item.get("id") == event_id), None)
    if not event:
        await message.answer("Бронирование не найдено.", keyboard=get_my_bookings_keyboard())
        return

    now = datetime.now()
    period_start = now
    period_end = now + timedelta(days=90)
    try:
        all_events = await list_events(period_start, period_end)
        marker = f"Связано с событием: {event_id}"
        linked_events = [
            item for item in all_events
            if marker in (item.get("description") or "")
            and "Service ID: 9" in (item.get("description") or "")
        ]
        for linked in linked_events:
            linked_id = linked.get("id")
            if linked_id:
                await delete_event(linked_id)
        await delete_event(event_id)
    except Exception:
        await message.answer("Не удалось отменить бронирование.", keyboard=get_my_bookings_keyboard())
        return

    await message.answer(
        "✅ Бронирование отменено.",
        keyboard=get_my_bookings_keyboard(),
    )


async def _send_contacts(message: Message):
    await message.answer(
        "📞 Контакты:\n\n"
        "📍 Адрес: улица Володи Дубинина, 3, Санкт-Петербург\n"
        "🌐 Сайт: https://innasuvorova.ru/rona_photostudio\n"
        "✉️ Email: rona.photostudio.petergof@gmail.com\n"
        "🕒 Время работы: с 9:00 до 21:00 по предварительному бронированию",
        keyboard=get_back_to_main_keyboard(is_admin=await is_vk_admin_id(message.from_id)),
    )


async def _send_help(message: Message):
    await send_faq_list(message, page=0)


def register_start_handlers(bot: Bot):
    @bot.on.message(payload_contains={"a": "mb_menu"})
    async def my_bookings_menu(message: Message):
        await _send_my_bookings_menu(message)

    @bot.on.message(payload_contains={"a": "mb_active"})
    async def my_active_bookings(message: Message):
        payload = message.get_payload_json() or {}
        await _send_active_bookings(message, page=int(payload.get("p", 0)))

    @bot.on.message(payload_contains={"a": "mb_history"})
    async def my_booking_history(message: Message):
        payload = message.get_payload_json() or {}
        await _send_booking_history(message, page=int(payload.get("p", 0)))

    @bot.on.message(payload_contains={"a": "mb_open"})
    async def my_booking_open(message: Message):
        payload = message.get_payload_json() or {}
        await _send_active_booking_detail(
            message,
            event_id=str(payload.get("id") or ""),
            page=int(payload.get("p", 0)),
        )

    @bot.on.message(payload_contains={"a": "mb_cancel"})
    async def my_booking_cancel(message: Message):
        payload = message.get_payload_json() or {}
        await _cancel_active_booking(message, event_id=str(payload.get("id") or ""))

    @bot.on.message(payload_contains={"a": "mb_back"})
    async def my_bookings_back(message: Message):
        await _send_main_menu(message)

    @bot.on.message()
    async def main_router(message: Message):
        text = _normalize_text(message.text)
        text_wo_emoji = _normalize_text(_strip_leading_emoji(text))

        start_commands = {"/start", "start", "начать", "меню", "главное меню"}
        if text in start_commands or text_wo_emoji in start_commands:
            await _send_main_menu(message)
            return

        if text == "услуги" or text_wo_emoji == "услуги":
            await _send_services(message)
            return

        if text == "мои бронирования" or text_wo_emoji == "мои бронирования":
            await _send_my_bookings_menu(message)
            return

        if text == "контакты" or text_wo_emoji == "контакты":
            await _send_contacts(message)
            return

        if text == "помощь" or text_wo_emoji == "помощь":
            await _send_help(message)
            return

        forwarded = await forward_question_to_vk_admins(message)
        if forwarded:
            await message.answer(
                "Дождитесь ответа администратора",
                keyboard=get_main_menu_keyboard(is_admin=await is_vk_admin_id(message.from_id)),
            )
            return

        await message.answer(
            "⁉️ Если хотите задать вопрос Администратору:\n"
            "Главное меню -> Помощь -> Связаться с администратором\n"
            "Затем введи свой вопрос",
            keyboard=get_main_menu_keyboard(is_admin=await is_vk_admin_id(message.from_id)),
        )
