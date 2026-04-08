from __future__ import annotations

import html
import re
from datetime import datetime, timedelta
from enum import Enum

from vkbottle import BaseStateGroup
from vkbottle.bot import Bot, Message

from app.core.modules.admin.bookings import (
    cancel_admin_booking_event,
    load_admin_booking_detail,
    load_admin_future_bookings,
    load_admin_period_bookings,
    search_admin_bookings,
)
from app.core.modules.admin.overview import (
    build_admin_admins_text,
    build_admin_clients_text,
    build_admin_services_text,
)
from app.core.modules.admin.tokens import register_admin_booking_token, resolve_admin_booking_token
from app.core.modules.support.admin_faq import (
    build_admin_faq_detail_text,
    build_admin_faq_keyboard_items,
    build_admin_faq_overview_text,
    validate_admin_faq_answer,
    validate_admin_faq_question,
)
from app.core.modules.support.admin_faq_use_case import (
    create_admin_faq_entry,
    delete_admin_faq_entry,
    get_admin_faq_entry,
    toggle_admin_faq_active,
    update_admin_faq_answer,
    update_admin_faq_question,
)
from app.integrations.local.db import admin_repo, client_repo, faq_repo, service_repo
from app.interfaces.messenger.tg.services.calendar_queries import (
    delete_event as svc_delete_event,
    get_event as svc_get_event,
    is_calendar_available,
    list_events as svc_list_events,
)
from app.interfaces.messenger.tg.services.contact_utils import (
    extract_booking_contact_details,
    format_phone_plus7,
    normalize_phone,
)
from app.interfaces.messenger.vk.auth import is_vk_admin_id
from app.interfaces.messenger.vk.keyboards import (
    get_admin_booking_detail_keyboard,
    get_admin_bookings_keyboard,
    get_admin_faq_detail_keyboard,
    get_admin_faq_list_keyboard,
    get_admin_future_bookings_keyboard,
    get_admin_help_keyboard,
    get_admin_keyboard,
    get_admin_service_detail_keyboard,
    get_admin_services_keyboard,
    get_admin_services_list_keyboard,
    get_main_menu_keyboard,
)
ADMIN_FUTURE_BOOKINGS_PAGE_SIZE = 6


class VkAdminState(BaseStateGroup, Enum):
    waiting_for_booking_search_query = "waiting_for_booking_search_query"
    waiting_for_faq_question = "waiting_for_faq_question"
    waiting_for_faq_answer = "waiting_for_faq_answer"
    waiting_for_faq_edit_question = "waiting_for_faq_edit_question"
    waiting_for_faq_edit_answer = "waiting_for_faq_edit_answer"


def _plain(text: str) -> str:
    no_tags = re.sub(r"<[^>]+>", "", text or "")
    return html.unescape(no_tags).strip()


async def _is_admin(message: Message) -> bool:
    return await is_vk_admin_id(message.from_id)


def _state_payload(message: Message) -> dict:
    if message.state_peer and message.state_peer.payload:
        return dict(message.state_peer.payload)
    return {}


async def _deny(message: Message) -> None:
    await message.answer("У вас нет прав администратора.", keyboard=get_main_menu_keyboard(is_admin=False))


async def _show_admin_panel(message: Message) -> None:
    await message.answer(
        "🔧 Админ-панель\n\nВыберите действие:",
        keyboard=get_admin_keyboard(),
    )


async def _show_admin_help(message: Message) -> None:
    faqs = await faq_repo.get_all()
    items = build_admin_faq_keyboard_items(faqs)
    await message.answer(
        _plain(build_admin_faq_overview_text(faqs)),
        keyboard=get_admin_faq_list_keyboard(items),
    )


async def _show_admin_services(message: Message) -> None:
    services = await service_repo.get_all()
    await message.answer(
        _plain(build_admin_services_text(services)),
        keyboard=get_admin_services_keyboard(),
    )


async def _show_admin_services_list(message: Message) -> None:
    services = await service_repo.get_all()
    if not services:
        await message.answer("Услуг пока нет.", keyboard=get_admin_services_keyboard())
        return
    await message.answer(
        "📸 Выберите услугу:",
        keyboard=get_admin_services_list_keyboard(services),
    )


async def _show_admin_service_detail(message: Message, service_id: int) -> None:
    service = await service_repo.get_by_id(service_id)
    if not service:
        await message.answer("Услуга не найдена.", keyboard=get_admin_services_keyboard())
        return

    status = "✅ Активна" if service.is_active else "❌ Неактивна"
    text = (
        "📸 Услуга\n\n"
        f"Название: {service.name}\n"
        f"Описание: {service.description or 'Не указано'}\n"
        f"Цена (будни): {service.price_min}₽\n"
        f"Цена (выходные): {service.price_min_weekend}₽\n"
        f"Макс. клиентов: {service.max_num_clients}\n"
        f"Мин. длительность: {service.min_duration_minutes} мин.\n"
        f"Шаг длительности: {service.duration_step_minutes} мин.\n"
        f"Статус: {status}"
    )
    await message.answer(
        text,
        keyboard=get_admin_service_detail_keyboard(service_id, service.is_active),
    )


async def _toggle_admin_service(message: Message, service_id: int) -> None:
    service = await service_repo.get_by_id(service_id)
    if not service:
        await message.answer("Услуга не найдена.", keyboard=get_admin_services_keyboard())
        return

    service.is_active = not service.is_active
    await service_repo.update(service)
    await _show_admin_service_detail(message, service_id)


async def _show_admin_clients(message: Message) -> None:
    clients = await client_repo.get_all() if hasattr(client_repo, "get_all") else []
    client_rows: list[dict] = []
    for client in clients[:5]:
        client_rows.append(
            {
                "name": client.name,
                "telegram_label": str(client.telegram_id) if client.telegram_id else None,
                "phone_display": format_phone_plus7(client.phone) if client.phone else None,
            }
        )
    await message.answer(
        _plain(build_admin_clients_text(client_rows)),
        keyboard=get_admin_keyboard(),
    )


async def _show_admin_admins(message: Message) -> None:
    admins = await admin_repo.get_all()
    admin_rows: list[dict] = []
    for admin in admins:
        admin_rows.append(
            {
                "id": admin.id,
                "telegram_label": str(admin.telegram_id) if admin.telegram_id else "Не указан",
                "vk_label": admin.vk_id or "Не указан",
                "is_active": admin.is_active,
            }
        )
    await message.answer(
        _plain(build_admin_admins_text(admin_rows)),
        keyboard=get_admin_keyboard(),
    )


async def _show_admin_bookings_menu(message: Message) -> None:
    await message.answer(
        "📅 Управление бронированиями\n\nВыберите раздел:",
        keyboard=get_admin_bookings_keyboard(),
    )


def _paginate_events(events: list[dict], page: int, page_size: int) -> tuple[list[dict], int, int]:
    total = len(events)
    total_pages = max(1, (total + page_size - 1) // page_size)
    page = max(0, min(page, total_pages - 1))
    start = page * page_size
    end = start + page_size
    return events[start:end], total_pages, page


def _build_admin_future_bookings_page_text(page_events: list[dict], page: int, total_pages: int) -> str:
    lines = [
        "📅 Будущие бронирования",
        "",
        "Выберите бронирование для просмотра деталей:",
        "",
    ]
    for event in page_events:
        start = event.get("start")
        if not start:
            continue
        summary = event.get("summary", "Без названия")
        lines.append(f"🕐 {start.strftime('%d.%m %H:%M')} — {summary}")
    if total_pages > 1:
        lines.extend(["", f"Страница {page + 1} из {total_pages}"])
    return "\n".join(lines)


async def _show_admin_future_bookings(message: Message, page: int = 0, notice: str | None = None) -> None:
    result = await load_admin_future_bookings(
        is_calendar_available=is_calendar_available,
        list_events=svc_list_events,
    )
    if result.status != "ok":
        text = _plain(result.text)
        if notice:
            text = f"{notice}\n\n{text}"
        await message.answer(text, keyboard=get_admin_keyboard())
        return

    page_events, total_pages, page = _paginate_events(
        result.events,
        page,
        ADMIN_FUTURE_BOOKINGS_PAGE_SIZE,
    )
    text = _build_admin_future_bookings_page_text(page_events, page, total_pages)
    if notice:
        text = f"{notice}\n\n{text}"
    await message.answer(
        text,
        keyboard=get_admin_future_bookings_keyboard(
            page_events,
            message.from_id,
            register_admin_booking_token,
            page=page,
            total_pages=total_pages,
        ),
    )


async def _show_admin_period_bookings(message: Message, period: str) -> None:
    now = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    if period == "today":
        result = await load_admin_period_bookings(
            title=f"Бронирования на сегодня ({now.strftime('%d.%m.%Y')})",
            empty_text="На сегодня бронирований нет.",
            period_start=now,
            period_end=now + timedelta(days=1),
            is_calendar_available=is_calendar_available,
            list_events=svc_list_events,
        )
    elif period == "tomorrow":
        tomorrow = now + timedelta(days=1)
        result = await load_admin_period_bookings(
            title=f"Бронирования на завтра ({tomorrow.strftime('%d.%m.%Y')})",
            empty_text="На завтра бронирований нет.",
            period_start=tomorrow,
            period_end=tomorrow + timedelta(days=1),
            is_calendar_available=is_calendar_available,
            list_events=svc_list_events,
        )
    else:
        result = await load_admin_period_bookings(
            title="Бронирования на неделю",
            empty_text="На ближайшие 7 дней бронирований нет.",
            period_start=now,
            period_end=now + timedelta(days=7),
            is_calendar_available=is_calendar_available,
            list_events=svc_list_events,
            max_results=100,
            include_date=True,
        )

    await message.answer(_plain(result.text), keyboard=get_admin_bookings_keyboard())


async def _show_admin_booking_detail(message: Message, token: str, page: int = 0) -> None:
    event_id, err = resolve_admin_booking_token(token, message.from_id)
    if err == "access_denied":
        await message.answer("Нет доступа к этой записи.", keyboard=get_admin_bookings_keyboard())
        return
    if err == "stale" or not event_id:
        await message.answer("Список устарел, откройте заново.", keyboard=get_admin_bookings_keyboard())
        return

    result = await load_admin_booking_detail(
        event_id=event_id,
        is_calendar_available=is_calendar_available,
        get_event=svc_get_event,
        extract_contact_details=extract_booking_contact_details,
        normalize_phone=normalize_phone,
        client_repo=client_repo,
    )
    if result.status != "ok":
        await message.answer(_plain(result.text), keyboard=get_admin_bookings_keyboard())
        return

    booking_token = register_admin_booking_token(message.from_id, event_id)
    await message.answer(
        _plain(result.text),
        keyboard=get_admin_booking_detail_keyboard(booking_token, page),
    )


async def _cancel_admin_booking(message: Message, token: str, page: int = 0) -> None:
    event_id, err = resolve_admin_booking_token(token, message.from_id)
    if err == "access_denied":
        await message.answer("Нет доступа к этой записи.", keyboard=get_admin_bookings_keyboard())
        return
    if err == "stale" or not event_id:
        await message.answer("Список устарел, откройте заново.", keyboard=get_admin_bookings_keyboard())
        return

    result = await cancel_admin_booking_event(
        event_id=event_id,
        is_calendar_available=is_calendar_available,
        list_events=svc_list_events,
        delete_event=svc_delete_event,
    )
    if result == "calendar_unavailable":
        await message.answer("Календарь недоступен.", keyboard=get_admin_bookings_keyboard())
        return
    if result != "ok":
        await message.answer("Не удалось отменить бронирование.", keyboard=get_admin_bookings_keyboard())
        return

    await _show_admin_future_bookings(message, page=page, notice="✅ Бронирование отменено.")


def register_admin_handlers(bot: Bot) -> None:
    @bot.on.message(text="🔧 Админ-панель")
    @bot.on.message(payload_contains={"a": "adm_panel"})
    async def admin_panel_entry(message: Message):
        if not await _is_admin(message):
            await _deny(message)
            return
        await bot.state_dispenser.delete(message.peer_id)
        await _show_admin_panel(message)

    @bot.on.message(payload_contains={"a": "adm_back_main"})
    async def admin_back_main(message: Message):
        await bot.state_dispenser.delete(message.peer_id)
        await message.answer(
            "🏠 Главное меню\n\nВыберите действие:",
            keyboard=get_main_menu_keyboard(is_admin=await _is_admin(message)),
        )

    @bot.on.message(payload_contains={"a": "adm_services"})
    async def admin_services(message: Message):
        if not await _is_admin(message):
            await _deny(message)
            return
        await bot.state_dispenser.delete(message.peer_id)
        await _show_admin_services(message)

    @bot.on.message(payload_contains={"a": "adm_services_list"})
    async def admin_services_list(message: Message):
        if not await _is_admin(message):
            await _deny(message)
            return
        await bot.state_dispenser.delete(message.peer_id)
        await _show_admin_services_list(message)

    @bot.on.message(payload_contains={"a": "adm_service_open"})
    async def admin_service_open(message: Message):
        if not await _is_admin(message):
            await _deny(message)
            return
        await bot.state_dispenser.delete(message.peer_id)
        payload = message.get_payload_json() or {}
        await _show_admin_service_detail(message, int(payload.get("id", 0)))

    @bot.on.message(payload_contains={"a": "adm_service_toggle"})
    async def admin_service_toggle(message: Message):
        if not await _is_admin(message):
            await _deny(message)
            return
        payload = message.get_payload_json() or {}
        await _toggle_admin_service(message, int(payload.get("id", 0)))

    @bot.on.message(payload_contains={"a": "adm_clients"})
    async def admin_clients(message: Message):
        if not await _is_admin(message):
            await _deny(message)
            return
        await bot.state_dispenser.delete(message.peer_id)
        await _show_admin_clients(message)

    @bot.on.message(payload_contains={"a": "adm_admins"})
    async def admin_admins(message: Message):
        if not await _is_admin(message):
            await _deny(message)
            return
        await bot.state_dispenser.delete(message.peer_id)
        await _show_admin_admins(message)

    @bot.on.message(payload_contains={"a": "adm_bookings_menu"})
    async def admin_bookings_menu(message: Message):
        if not await _is_admin(message):
            await _deny(message)
            return
        await bot.state_dispenser.delete(message.peer_id)
        await _show_admin_bookings_menu(message)

    @bot.on.message(payload_contains={"a": "adm_bookings"})
    async def admin_bookings(message: Message):
        if not await _is_admin(message):
            await _deny(message)
            return
        await bot.state_dispenser.delete(message.peer_id)
        payload = message.get_payload_json() or {}
        await _show_admin_future_bookings(message, page=int(payload.get("p", 0)))

    @bot.on.message(payload_contains={"a": "adm_day"})
    async def admin_bookings_period(message: Message):
        if not await _is_admin(message):
            await _deny(message)
            return
        await bot.state_dispenser.delete(message.peer_id)
        payload = message.get_payload_json() or {}
        await _show_admin_period_bookings(message, str(payload.get("d") or "today"))

    @bot.on.message(payload_contains={"a": "adm_booking_open"})
    async def admin_booking_open(message: Message):
        if not await _is_admin(message):
            await _deny(message)
            return
        payload = message.get_payload_json() or {}
        await _show_admin_booking_detail(message, str(payload.get("t") or ""), page=int(payload.get("p", 0)))

    @bot.on.message(payload_contains={"a": "adm_booking_cancel"})
    async def admin_booking_cancel(message: Message):
        if not await _is_admin(message):
            await _deny(message)
            return
        payload = message.get_payload_json() or {}
        await _cancel_admin_booking(message, str(payload.get("t") or ""), page=int(payload.get("p", 0)))

    @bot.on.message(payload_contains={"a": "adm_booking_search"})
    async def admin_booking_search(message: Message):
        if not await _is_admin(message):
            await _deny(message)
            return
        await bot.state_dispenser.set(message.peer_id, VkAdminState.waiting_for_booking_search_query)
        await message.answer(
            "🔍 Поиск бронирований\n\nВведите текст для поиска.",
            keyboard=get_admin_bookings_keyboard(),
        )

    @bot.on.message(state=VkAdminState.waiting_for_booking_search_query)
    async def admin_booking_search_input(message: Message):
        if not await _is_admin(message):
            await _deny(message)
            return
        await bot.state_dispenser.delete(message.peer_id)
        result = await search_admin_bookings(
            query=message.text or "",
            is_calendar_available=is_calendar_available,
            list_events=svc_list_events,
        )
        await message.answer(_plain(result.text), keyboard=get_admin_bookings_keyboard())

    @bot.on.message(payload_contains={"a": "adm_help"})
    async def admin_help(message: Message):
        if not await _is_admin(message):
            await _deny(message)
            return
        await bot.state_dispenser.delete(message.peer_id)
        await _show_admin_help(message)

    @bot.on.message(payload_contains={"a": "adm_faq_open"})
    async def admin_faq_open(message: Message):
        if not await _is_admin(message):
            await _deny(message)
            return
        payload = message.get_payload_json() or {}
        faq_id = int(payload.get("id", 0))
        entry = await get_admin_faq_entry(faq_repo, faq_id)
        if not entry:
            await message.answer("FAQ не найден.", keyboard=get_admin_help_keyboard())
            return
        await message.answer(
            _plain(build_admin_faq_detail_text(entry)),
            keyboard=get_admin_faq_detail_keyboard(faq_id, entry.is_active),
        )

    @bot.on.message(payload_contains={"a": "adm_faq_add"})
    async def admin_faq_add(message: Message):
        if not await _is_admin(message):
            await _deny(message)
            return
        await bot.state_dispenser.set(message.peer_id, VkAdminState.waiting_for_faq_question)
        await message.answer("✍️ Введите вопрос для FAQ:", keyboard=get_admin_help_keyboard())

    @bot.on.message(state=VkAdminState.waiting_for_faq_question)
    async def admin_faq_question_input(message: Message):
        if not await _is_admin(message):
            await _deny(message)
            return
        question = (message.text or "").strip()
        error = validate_admin_faq_question(question)
        if error:
            await message.answer(_plain(error), keyboard=get_admin_help_keyboard())
            return
        await bot.state_dispenser.set(
            message.peer_id,
            VkAdminState.waiting_for_faq_answer,
            faq_question=question,
        )
        await message.answer("✍️ Введите ответ для FAQ:", keyboard=get_admin_help_keyboard())

    @bot.on.message(state=VkAdminState.waiting_for_faq_answer)
    async def admin_faq_answer_input(message: Message):
        if not await _is_admin(message):
            await _deny(message)
            return
        answer = (message.text or "").strip()
        error = validate_admin_faq_answer(answer)
        if error:
            await message.answer(_plain(error), keyboard=get_admin_help_keyboard())
            return
        payload = _state_payload(message)
        question = str(payload.get("faq_question") or "").strip()
        await create_admin_faq_entry(faq_repo, question=question, answer=answer)
        await bot.state_dispenser.delete(message.peer_id)
        await _show_admin_help(message)

    @bot.on.message(payload_contains={"a": "adm_faq_edit_q"})
    async def admin_faq_edit_question(message: Message):
        if not await _is_admin(message):
            await _deny(message)
            return
        payload = message.get_payload_json() or {}
        faq_id = int(payload.get("id", 0))
        await bot.state_dispenser.set(
            message.peer_id,
            VkAdminState.waiting_for_faq_edit_question,
            faq_id=faq_id,
        )
        await message.answer("✍️ Введите новый вопрос:", keyboard=get_admin_help_keyboard())

    @bot.on.message(state=VkAdminState.waiting_for_faq_edit_question)
    async def admin_faq_edit_question_input(message: Message):
        if not await _is_admin(message):
            await _deny(message)
            return
        question = (message.text or "").strip()
        error = validate_admin_faq_question(question)
        if error:
            await message.answer(_plain(error), keyboard=get_admin_help_keyboard())
            return
        payload = _state_payload(message)
        faq_id = int(payload.get("faq_id", 0))
        entry = await update_admin_faq_question(faq_repo, faq_id=faq_id, question=question)
        await bot.state_dispenser.delete(message.peer_id)
        if not entry:
            await message.answer("FAQ не найден.", keyboard=get_admin_help_keyboard())
            return
        await message.answer(
            _plain(build_admin_faq_detail_text(entry)),
            keyboard=get_admin_faq_detail_keyboard(faq_id, entry.is_active),
        )

    @bot.on.message(payload_contains={"a": "adm_faq_edit_a"})
    async def admin_faq_edit_answer(message: Message):
        if not await _is_admin(message):
            await _deny(message)
            return
        payload = message.get_payload_json() or {}
        faq_id = int(payload.get("id", 0))
        await bot.state_dispenser.set(
            message.peer_id,
            VkAdminState.waiting_for_faq_edit_answer,
            faq_id=faq_id,
        )
        await message.answer("✍️ Введите новый ответ:", keyboard=get_admin_help_keyboard())

    @bot.on.message(state=VkAdminState.waiting_for_faq_edit_answer)
    async def admin_faq_edit_answer_input(message: Message):
        if not await _is_admin(message):
            await _deny(message)
            return
        answer = (message.text or "").strip()
        error = validate_admin_faq_answer(answer)
        if error:
            await message.answer(_plain(error), keyboard=get_admin_help_keyboard())
            return
        payload = _state_payload(message)
        faq_id = int(payload.get("faq_id", 0))
        entry = await update_admin_faq_answer(faq_repo, faq_id=faq_id, answer=answer)
        await bot.state_dispenser.delete(message.peer_id)
        if not entry:
            await message.answer("FAQ не найден.", keyboard=get_admin_help_keyboard())
            return
        await message.answer(
            _plain(build_admin_faq_detail_text(entry)),
            keyboard=get_admin_faq_detail_keyboard(faq_id, entry.is_active),
        )

    @bot.on.message(payload_contains={"a": "adm_faq_toggle"})
    async def admin_faq_toggle(message: Message):
        if not await _is_admin(message):
            await _deny(message)
            return
        payload = message.get_payload_json() or {}
        faq_id = int(payload.get("id", 0))
        entry = await toggle_admin_faq_active(faq_repo, faq_id)
        if not entry:
            await message.answer("FAQ не найден.", keyboard=get_admin_help_keyboard())
            return
        await message.answer(
            _plain(build_admin_faq_detail_text(entry)),
            keyboard=get_admin_faq_detail_keyboard(faq_id, entry.is_active),
        )

    @bot.on.message(payload_contains={"a": "adm_faq_delete"})
    async def admin_faq_delete(message: Message):
        if not await _is_admin(message):
            await _deny(message)
            return
        payload = message.get_payload_json() or {}
        faq_id = int(payload.get("id", 0))
        await delete_admin_faq_entry(faq_repo, faq_id)
        await _show_admin_help(message)
