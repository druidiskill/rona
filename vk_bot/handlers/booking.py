from __future__ import annotations

from datetime import datetime, timedelta
from enum import Enum

from vkbottle import BaseStateGroup, Keyboard, KeyboardButtonColor, Text
from vkbottle.bot import Bot, Message

from config import ADMIN_IDS_VK
from database import client_repo, service_repo
from database.models import Client
from telegram_bot.services.booking_calendar import (
    get_time_slots_for_date as svc_get_time_slots_for_date,
    is_booking_available as svc_is_booking_available,
)
from telegram_bot.services.booking_formatters import (
    format_booking_date,
    format_booking_time_range,
    format_booking_guests,
    format_extras_display,
)
from vk_bot.keyboards import get_main_menu_keyboard

try:
    from google_calendar.calendar_service import GoogleCalendarService

    CALENDAR_AVAILABLE = True
except Exception:
    GoogleCalendarService = None
    CALENDAR_AVAILABLE = False


class VkBookingState(BaseStateGroup, Enum):
    filling_form = "filling_form"
    entering_name = "entering_name"
    entering_phone = "entering_phone"
    entering_email = "entering_email"


def _parse_admin_ids(value: str) -> set[int]:
    return {int(x.strip()) for x in value.split(",") if x.strip().isdigit()}


ADMIN_IDS = _parse_admin_ids(ADMIN_IDS_VK)


def _normalize_min_duration_minutes(raw_value: int | None) -> int:
    min_duration = int(raw_value or 60)
    if min_duration < 60:
        min_duration = 60
    if min_duration % 60 != 0:
        min_duration = ((min_duration // 60) + 1) * 60
    return min_duration


def _normalize_max_guests(raw_value: int | None) -> int:
    max_guests = int(raw_value or 1)
    return max(1, max_guests)


def _normalize_phone(phone: str) -> str | None:
    digits = "".join(ch for ch in str(phone) if ch.isdigit())
    if len(digits) == 11 and digits.startswith(("7", "8")):
        digits = digits[1:]
    if len(digits) != 10:
        return None
    return digits


def _format_phone_display(phone10: str | None) -> str:
    if not phone10 or len(phone10) != 10:
        return "Не указан"
    return f"+7 {phone10[:3]} {phone10[3:6]} {phone10[6:8]} {phone10[8:10]}"


def get_services_booking_keyboard(services: list) -> str:
    kb = Keyboard(one_time=False, inline=False)
    for service in services:
        kb.add(
            Text(
                f"📸 {service.name}",
                payload={"a": "bk_service", "sid": service.id},
            ),
            color=KeyboardButtonColor.PRIMARY,
        ).row()
    kb.add(Text("🏠 Главное меню"), color=KeyboardButtonColor.SECONDARY)
    return kb.get_json()


def _get_form_keyboard(service_id: int, booking_data: dict) -> str:
    kb = Keyboard(one_time=False, inline=False)
    req_color = lambda ok: KeyboardButtonColor.POSITIVE if ok else KeyboardButtonColor.NEGATIVE

    date_ok = bool(booking_data.get("date"))
    time_ok = bool(booking_data.get("time"))
    name_ok = bool(booking_data.get("name"))
    phone_ok = bool(booking_data.get("phone"))
    guests_ok = bool(booking_data.get("guests_count"))
    email_ok = bool(booking_data.get("email"))
    duration_set = bool(booking_data.get("duration"))
    extras_set = bool(booking_data.get("extras"))

    kb.add(Text("📅 Дата", payload={"a": "bk_date", "sid": service_id}), color=req_color(date_ok)).row()
    kb.add(Text("🕒 Время", payload={"a": "bk_time", "sid": service_id}), color=req_color(time_ok)).row()
    kb.add(Text("👤 Имя", payload={"a": "bk_name", "sid": service_id}), color=req_color(name_ok))
    kb.add(Text("📱 Телефон", payload={"a": "bk_phone", "sid": service_id}), color=req_color(phone_ok)).row()
    kb.add(Text("👥 Гости", payload={"a": "bk_guests", "sid": service_id}), color=req_color(guests_ok))
    kb.add(
        Text("⏰ Длительность", payload={"a": "bk_duration", "sid": service_id}),
        color=KeyboardButtonColor.PRIMARY if duration_set else KeyboardButtonColor.SECONDARY,
    ).row()
    kb.add(
        Text("➕ Доп. услуги", payload={"a": "bk_extras", "sid": service_id}),
        color=KeyboardButtonColor.PRIMARY if extras_set else KeyboardButtonColor.SECONDARY,
    )
    kb.add(
        Text("📧 E-mail", payload={"a": "bk_email", "sid": service_id}),
        color=KeyboardButtonColor.PRIMARY if email_ok else KeyboardButtonColor.SECONDARY,
    ).row()
    kb.add(Text("✅ Подтвердить", payload={"a": "bk_confirm", "sid": service_id}), color=KeyboardButtonColor.POSITIVE).row()
    kb.add(Text("❌ Отменить", payload={"a": "bk_cancel"}), color=KeyboardButtonColor.NEGATIVE)
    kb.add(Text("🏠 Главное меню"), color=KeyboardButtonColor.SECONDARY)
    return kb.get_json()


def _get_date_keyboard(service_id: int, week_offset: int) -> str:
    kb = Keyboard(one_time=False, inline=False)
    today = datetime.now().date()
    start_date = today + timedelta(days=week_offset * 7)
    for i in range(7):
        d = start_date + timedelta(days=i)
        lbl = d.strftime("%d.%m.%Y")
        kb.add(
            Text(
                f"📅 {lbl}",
                payload={"a": "bk_date_set", "sid": service_id, "d": d.strftime("%Y-%m-%d")},
            ),
            color=KeyboardButtonColor.PRIMARY,
        ).row()
    kb.add(Text("⬅️ Неделя", payload={"a": "bk_date_week", "sid": service_id, "w": week_offset - 1}), color=KeyboardButtonColor.SECONDARY)
    kb.add(Text("➡️ Неделя", payload={"a": "bk_date_week", "sid": service_id, "w": week_offset + 1}), color=KeyboardButtonColor.SECONDARY).row()
    kb.add(Text("↩️ К форме", payload={"a": "bk_back_form", "sid": service_id}), color=KeyboardButtonColor.SECONDARY)
    return kb.get_json()


def _get_duration_keyboard(service_id: int, min_duration_minutes: int = 60) -> str:
    kb = Keyboard(one_time=False, inline=False)
    min_duration = _normalize_min_duration_minutes(min_duration_minutes)
    for hours in range(min_duration // 60, 9):
        kb.add(
            Text(
                f"{hours} ч",
                payload={"a": "bk_duration_set", "sid": service_id, "m": hours * 60},
            ),
            color=KeyboardButtonColor.PRIMARY,
        )
        if hours % 2 == 1:
            kb.row()
    kb.row().add(
        Text("Весь день", payload={"a": "bk_duration_set", "sid": service_id, "m": 720}),
        color=KeyboardButtonColor.PRIMARY,
    ).row()
    kb.add(Text("↩️ К форме", payload={"a": "bk_back_form", "sid": service_id}), color=KeyboardButtonColor.SECONDARY)
    return kb.get_json()


def _get_guests_keyboard(service_id: int, max_guests: int = 1) -> str:
    kb = Keyboard(one_time=False, inline=False)
    max_allowed = _normalize_max_guests(max_guests)
    for i in range(1, max_allowed + 1):
        kb.add(Text(str(i), payload={"a": "bk_guests_set", "sid": service_id, "g": i}), color=KeyboardButtonColor.PRIMARY)
        if i % 5 == 0:
            kb.row()
    kb.add(Text("↩️ К форме", payload={"a": "bk_back_form", "sid": service_id}), color=KeyboardButtonColor.SECONDARY)
    return kb.get_json()


def _get_extras_keyboard(service_id: int, selected: list[str]) -> str:
    items = [
        ("photographer", "📸 Фотограф 11 500₽"),
        ("makeuproom", "💄 Гримерка 200/250₽/ч"),
        ("fireplace", "🔥 Розжиг камина 400₽"),
        ("rental", "🧺 Прокат 200₽"),
    ]
    kb = Keyboard(one_time=False, inline=False)
    for key, label in items:
        mark = "✅ " if key in selected else ""
        kb.add(
            Text(
                f"{mark}{label}",
                payload={"a": "bk_extra_toggle", "sid": service_id, "x": key},
            ),
            color=KeyboardButtonColor.PRIMARY,
        ).row()
    kb.add(Text("Готово", payload={"a": "bk_back_form", "sid": service_id}), color=KeyboardButtonColor.POSITIVE)
    return kb.get_json()


def _get_time_keyboard(service_id: int, date_value: str, slots: list[dict], page: int = 0) -> str:
    page_size = 8
    total = len(slots)
    total_pages = max(1, (total + page_size - 1) // page_size)
    page = max(0, min(page, total_pages - 1))
    start_idx = page * page_size
    end_idx = min(start_idx + page_size, total)

    kb = Keyboard(one_time=False, inline=False)
    for slot in slots[start_idx:end_idx]:
        s = slot["start"]
        e = slot["end"]
        kb.add(
            Text(
                f"🕒 {s} - {e}",
                payload={"a": "bk_time_set", "sid": service_id, "d": date_value, "s": s, "e": e},
            ),
            color=KeyboardButtonColor.PRIMARY,
        ).row()
    if total_pages > 1:
        if page > 0:
            kb.add(
                Text(
                    "⬅️",
                    payload={"a": "bk_time_page", "sid": service_id, "d": date_value, "p": page - 1},
                ),
                color=KeyboardButtonColor.SECONDARY,
            )
        if page < total_pages - 1:
            kb.add(
                Text(
                    "➡️",
                    payload={"a": "bk_time_page", "sid": service_id, "d": date_value, "p": page + 1},
                ),
                color=KeyboardButtonColor.SECONDARY,
            )
        kb.row()
    kb.add(Text("↩️ К форме", payload={"a": "bk_back_form", "sid": service_id}), color=KeyboardButtonColor.SECONDARY)
    return kb.get_json()


async def _set_state(bot: Bot, message: Message, state: VkBookingState, booking_data: dict):
    await bot.state_dispenser.set(message.peer_id, state, booking_data=booking_data)


async def _clear_state(bot: Bot, message: Message):
    await bot.state_dispenser.delete(message.peer_id)


def _get_booking_data(message: Message) -> dict:
    if message.state_peer and message.state_peer.payload:
        return dict(message.state_peer.payload.get("booking_data", {}))
    return {}


async def _show_form(bot: Bot, message: Message, booking_data: dict):
    service_id = int(booking_data["service_id"])
    service_name = booking_data.get("service_name", "")
    duration_minutes = int(booking_data.get("duration") or 60)

    req_mark = lambda ok: "🟢" if ok else "🔴"
    date_ok = bool(booking_data.get("date"))
    time_ok = bool(booking_data.get("time"))
    name_ok = bool(booking_data.get("name"))
    phone_ok = bool(booking_data.get("phone"))
    guests_ok = bool(booking_data.get("guests_count"))

    text = f"📝 Бронирование услуги: {service_name}\n\n"
    text += "📋 Заполните данные для бронирования:\n\n"
    text += f"{req_mark(date_ok)} Дата: {format_booking_date(booking_data.get('date'))}\n"
    text += f"{req_mark(time_ok)} Время: {format_booking_time_range(booking_data.get('time'), duration_minutes)}\n"
    text += f"{req_mark(name_ok)} Имя: {booking_data.get('name') or 'Не указано'}\n"
    text += f"{req_mark(phone_ok)} Номер телефона: {booking_data.get('phone') or 'Не указан'}\n"
    text += f"{req_mark(guests_ok)} Количество гостей: {format_booking_guests(booking_data.get('guests_count'))}\n"
    text += f"⚪ Продолжительность: {duration_minutes} мин.\n"
    text += f"⚪ Доп. услуги: {format_extras_display(booking_data.get('extras', []))}\n"
    text += f"⚪ E-mail: {booking_data.get('email') or 'Не указан'}\n\n"
    text += "Выберите параметр:"

    await _set_state(bot, message, VkBookingState.filling_form, booking_data)
    await message.answer(text, keyboard=_get_form_keyboard(service_id, booking_data))


async def _load_or_create_vk_client(vk_id: int) -> Client:
    client = await client_repo.get_by_vk_id(vk_id)
    if client:
        return client
    client_id = await client_repo.create(Client(vk_id=vk_id, name="Пользователь"))
    return await client_repo.get_by_id(client_id)


def register_booking_handlers(bot: Bot):
    @bot.on.message(payload_contains={"a": "bk_service"})
    async def booking_start(message: Message):
        payload = message.get_payload_json() or {}
        service_id = int(payload.get("sid"))
        service = await service_repo.get_by_id(service_id)
        if not service:
            await message.answer("Услуга не найдена.")
            return

        client = await _load_or_create_vk_client(message.from_id)
        phone_display = _format_phone_display(client.phone) if client and client.phone else None
        booking_data = {
            "service_id": service_id,
            "service_name": service.name,
            "max_num_clients": _normalize_max_guests(service.max_num_clients),
            "date": None,
            "time": None,
            "name": client.name if client else None,
            "phone": phone_display,
            "guests_count": None,
            "duration": _normalize_min_duration_minutes(service.min_duration_minutes),
            "is_all_day": False,
            "extras": [],
            "email": client.email if client else None,
        }
        await _show_form(bot, message, booking_data)

    @bot.on.message(payload_contains={"a": "bk_back_form"}, state=VkBookingState.filling_form)
    @bot.on.message(text="↩️ К форме", state=VkBookingState.filling_form)
    async def booking_back_form(message: Message):
        await _show_form(bot, message, _get_booking_data(message))

    @bot.on.message(payload_contains={"a": "bk_date"}, state=VkBookingState.filling_form)
    @bot.on.message(text="📅 Дата", state=VkBookingState.filling_form)
    async def booking_date(message: Message):
        data = _get_booking_data(message)
        await message.answer(
            "📅 Выберите дату:",
            keyboard=_get_date_keyboard(int(data["service_id"]), 0),
        )

    @bot.on.message(payload_contains={"a": "bk_date_week"}, state=VkBookingState.filling_form)
    async def booking_date_week(message: Message):
        payload = message.get_payload_json() or {}
        sid = int(payload.get("sid"))
        week = int(payload.get("w", 0))
        await message.answer("📅 Выберите дату:", keyboard=_get_date_keyboard(sid, week))

    @bot.on.message(payload_contains={"a": "bk_date_set"}, state=VkBookingState.filling_form)
    async def booking_date_set(message: Message):
        payload = message.get_payload_json() or {}
        data = _get_booking_data(message)
        data["date"] = payload.get("d")
        await _show_form(bot, message, data)

    @bot.on.message(payload_contains={"a": "bk_time"}, state=VkBookingState.filling_form)
    @bot.on.message(text="🕒 Время", state=VkBookingState.filling_form)
    async def booking_time(message: Message):
        data = _get_booking_data(message)
        if not data.get("date"):
            await message.answer("Сначала выберите дату.")
            return

        service_id = int(data["service_id"])
        service_name = data.get("service_name")
        selected_date = datetime.strptime(data["date"], "%Y-%m-%d").date()
        duration = int(data.get("duration") or 60)
        is_all_day = bool(data.get("is_all_day"))
        slots, _, _ = await svc_get_time_slots_for_date(
            target_date=selected_date,
            service_id=service_id,
            service_name=service_name,
            duration_minutes=duration,
            all_day=is_all_day,
        )
        normalized_slots = [
            {"start": slot["start_time"].strftime("%H:%M"), "end": slot["end_time"].strftime("%H:%M")}
            for slot in slots
        ]
        if not normalized_slots:
            await message.answer("На выбранную дату нет свободных слотов.")
            return
        await message.answer(
            f"🕒 Выберите время на {selected_date.strftime('%d.%m.%Y')}:",
            keyboard=_get_time_keyboard(service_id, data["date"], normalized_slots, page=0),
        )

    @bot.on.message(payload_contains={"a": "bk_time_page"}, state=VkBookingState.filling_form)
    async def booking_time_page(message: Message):
        payload = message.get_payload_json() or {}
        data = _get_booking_data(message)
        service_id = int(payload.get("sid"))
        date_value = payload.get("d") or data.get("date")
        page = int(payload.get("p", 0))
        if not date_value:
            await message.answer("Сначала выберите дату.")
            return

        service_name = data.get("service_name")
        selected_date = datetime.strptime(date_value, "%Y-%m-%d").date()
        duration = int(data.get("duration") or 60)
        is_all_day = bool(data.get("is_all_day"))
        slots, _, _ = await svc_get_time_slots_for_date(
            target_date=selected_date,
            service_id=service_id,
            service_name=service_name,
            duration_minutes=duration,
            all_day=is_all_day,
        )
        normalized_slots = [
            {"start": slot["start_time"].strftime("%H:%M"), "end": slot["end_time"].strftime("%H:%M")}
            for slot in slots
        ]
        if not normalized_slots:
            await message.answer("На выбранную дату нет свободных слотов.")
            return
        await message.answer(
            f"🕒 Выберите время на {selected_date.strftime('%d.%m.%Y')}:",
            keyboard=_get_time_keyboard(service_id, date_value, normalized_slots, page=page),
        )

    @bot.on.message(payload_contains={"a": "bk_time_set"}, state=VkBookingState.filling_form)
    async def booking_time_set(message: Message):
        payload = message.get_payload_json() or {}
        data = _get_booking_data(message)
        s = payload.get("s")
        e = payload.get("e")
        data["time"] = f"{s} - {e}"
        if data.get("is_all_day") and data.get("date"):
            selected_date = datetime.strptime(data["date"], "%Y-%m-%d").date()
            start_dt = datetime.combine(selected_date, datetime.strptime(s, "%H:%M").time())
            end_dt = datetime.combine(selected_date, datetime.strptime("21:00", "%H:%M").time())
            data["duration"] = int((end_dt - start_dt).total_seconds() // 60)
            data["time"] = f"{s} - 21:00"
        await _show_form(bot, message, data)

    @bot.on.message(payload_contains={"a": "bk_duration"}, state=VkBookingState.filling_form)
    @bot.on.message(text="⏰ Длительность", state=VkBookingState.filling_form)
    async def booking_duration(message: Message):
        data = _get_booking_data(message)
        service = await service_repo.get_by_id(int(data["service_id"]))
        min_duration = _normalize_min_duration_minutes(service.min_duration_minutes if service else 60)
        await message.answer(
            "⏰ Выберите продолжительность:",
            keyboard=_get_duration_keyboard(int(data["service_id"]), min_duration),
        )

    @bot.on.message(payload_contains={"a": "bk_duration_set"}, state=VkBookingState.filling_form)
    async def booking_duration_set(message: Message):
        payload = message.get_payload_json() or {}
        data = _get_booking_data(message)
        service = await service_repo.get_by_id(int(data["service_id"]))
        min_duration = _normalize_min_duration_minutes(service.min_duration_minutes if service else 60)
        duration = int(payload.get("m", min_duration))
        if duration < min_duration:
            await message.answer(f"Минимальная продолжительность: {min_duration} мин.")
            return
        data["is_all_day"] = duration == 720
        if data["is_all_day"] and data.get("date") and data.get("time"):
            s = data["time"].split(" - ")[0]
            selected_date = datetime.strptime(data["date"], "%Y-%m-%d").date()
            start_dt = datetime.combine(selected_date, datetime.strptime(s, "%H:%M").time())
            end_dt = datetime.combine(selected_date, datetime.strptime("21:00", "%H:%M").time())
            data["duration"] = int((end_dt - start_dt).total_seconds() // 60)
            data["time"] = f"{s} - 21:00"
        else:
            data["duration"] = duration
        await _show_form(bot, message, data)

    @bot.on.message(payload_contains={"a": "bk_guests"}, state=VkBookingState.filling_form)
    @bot.on.message(text="👥 Гости", state=VkBookingState.filling_form)
    async def booking_guests(message: Message):
        data = _get_booking_data(message)
        service = await service_repo.get_by_id(int(data["service_id"]))
        max_guests = _normalize_max_guests(service.max_num_clients if service else data.get("max_num_clients", 1))
        data["max_num_clients"] = max_guests
        await _set_state(bot, message, VkBookingState.filling_form, data)
        await message.answer("👥 Выберите количество гостей:", keyboard=_get_guests_keyboard(int(data["service_id"]), max_guests))

    @bot.on.message(payload_contains={"a": "bk_guests_set"}, state=VkBookingState.filling_form)
    async def booking_guests_set(message: Message):
        payload = message.get_payload_json() or {}
        data = _get_booking_data(message)
        service = await service_repo.get_by_id(int(data["service_id"]))
        max_guests = _normalize_max_guests(service.max_num_clients if service else data.get("max_num_clients", 1))
        data["max_num_clients"] = max_guests
        guests_count = int(payload.get("g"))
        if guests_count > max_guests:
            await message.answer(f"Максимальная вместимость этой услуги: {max_guests} чел.")
            return
        data["guests_count"] = guests_count
        await _show_form(bot, message, data)

    @bot.on.message(payload_contains={"a": "bk_extras"}, state=VkBookingState.filling_form)
    @bot.on.message(text="➕ Доп. услуги", state=VkBookingState.filling_form)
    async def booking_extras(message: Message):
        data = _get_booking_data(message)
        await message.answer(
            "➕ Выберите дополнительные услуги:",
            keyboard=_get_extras_keyboard(int(data["service_id"]), data.get("extras", [])),
        )

    @bot.on.message(payload_contains={"a": "bk_extra_toggle"}, state=VkBookingState.filling_form)
    async def booking_extra_toggle(message: Message):
        payload = message.get_payload_json() or {}
        data = _get_booking_data(message)
        extra = payload.get("x")
        extras = list(data.get("extras", []))
        if extra in extras:
            extras.remove(extra)
        else:
            extras.append(extra)
        data["extras"] = extras
        await _set_state(bot, message, VkBookingState.filling_form, data)
        await message.answer(
            "➕ Выберите дополнительные услуги:",
            keyboard=_get_extras_keyboard(int(data["service_id"]), extras),
        )

    @bot.on.message(payload_contains={"a": "bk_name"}, state=VkBookingState.filling_form)
    @bot.on.message(text="👤 Имя", state=VkBookingState.filling_form)
    async def booking_name(message: Message):
        data = _get_booking_data(message)
        await _set_state(bot, message, VkBookingState.entering_name, data)
        await message.answer("👤 Введите имя:")

    @bot.on.message(state=VkBookingState.entering_name)
    async def booking_name_input(message: Message):
        data = _get_booking_data(message)
        name = (message.text or "").strip()
        if len(name) < 2 or not name.replace(" ", "").replace("-", "").isalpha():
            await message.answer("Имя должно содержать только буквы и быть длиннее 1 символа.")
            return
        data["name"] = name
        await _show_form(bot, message, data)

    @bot.on.message(payload_contains={"a": "bk_phone"}, state=VkBookingState.filling_form)
    @bot.on.message(text="📱 Телефон", state=VkBookingState.filling_form)
    async def booking_phone(message: Message):
        data = _get_booking_data(message)
        await _set_state(bot, message, VkBookingState.entering_phone, data)
        await message.answer("📱 Введите телефон (например +7 911 123 45 67):")

    @bot.on.message(state=VkBookingState.entering_phone)
    async def booking_phone_input(message: Message):
        data = _get_booking_data(message)
        phone10 = _normalize_phone((message.text or "").strip())
        if not phone10:
            await message.answer("Некорректный формат телефона. Введите 10 цифр номера.")
            return
        data["phone"] = _format_phone_display(phone10)
        await _show_form(bot, message, data)

    @bot.on.message(payload_contains={"a": "bk_email"}, state=VkBookingState.filling_form)
    @bot.on.message(text="📧 E-mail", state=VkBookingState.filling_form)
    async def booking_email(message: Message):
        data = _get_booking_data(message)
        await _set_state(bot, message, VkBookingState.entering_email, data)
        await message.answer("📧 Введите e-mail (или '-' чтобы пропустить):")

    @bot.on.message(state=VkBookingState.entering_email)
    async def booking_email_input(message: Message):
        data = _get_booking_data(message)
        email = (message.text or "").strip()
        if email == "-":
            data["email"] = None
            await _show_form(bot, message, data)
            return
        if "@" not in email or "." not in email:
            await message.answer("Некорректный e-mail. Введите корректный адрес или '-' для пропуска.")
            return
        data["email"] = email
        await _show_form(bot, message, data)

    @bot.on.message(payload_contains={"a": "bk_confirm"}, state=VkBookingState.filling_form)
    @bot.on.message(text="✅ Подтвердить", state=VkBookingState.filling_form)
    async def booking_confirm(message: Message):
        data = _get_booking_data(message)
        required = ["date", "time", "name", "phone", "guests_count"]
        missing = [k for k in required if not data.get(k)]
        if missing:
            await message.answer("Не все поля заполнены. Заполните форму до конца.")
            return

        service_id = int(data["service_id"])
        service = await service_repo.get_by_id(service_id)
        if service and int(data.get("guests_count") or 0) > _normalize_max_guests(service.max_num_clients):
            await message.answer(f"Максимальная вместимость этой услуги: {_normalize_max_guests(service.max_num_clients)} чел.")
            return
        service_name = data.get("service_name", "")
        selected_date = datetime.strptime(data["date"], "%Y-%m-%d").date()
        start_str = data["time"].split(" - ")[0]
        start_time = datetime.strptime(start_str, "%H:%M").time()
        start_dt = datetime.combine(selected_date, start_time)
        duration = int(data.get("duration") or 60)
        ok, reason = await svc_is_booking_available(
            target_date=selected_date,
            start_time=start_dt,
            duration_minutes=duration,
            service_id=service_id,
            service_name=service_name,
        )
        if not ok:
            await message.answer(f"❌ Время недоступно: {reason}")
            return

        event_start = start_dt
        event_end = event_start + timedelta(minutes=duration)

        created = False
        if CALENDAR_AVAILABLE and GoogleCalendarService:
            try:
                calendar_service = GoogleCalendarService()
                extras = data.get("extras", [])
                extras_text = []
                if "photographer" in extras:
                    extras_text.append("Фотограф")
                if "makeuproom" in extras:
                    extras_text.append("Гримерка")
                if "fireplace" in extras:
                    extras_text.append("Розжиг камина")
                if "rental" in extras:
                    extras_text.append("Прокат: халат и полотенце")
                extras_display = ", ".join(extras_text) if extras_text else "Нет"

                event_description = (
                    f"<b>Кто забронировал</b>\n{data['name']}\n"
                    f"email: {data.get('email') or 'не указан'}\n"
                    f"{data['phone']}\n"
                    f"VK ID: {message.from_id}\n\n"
                    f"<b>Какой зал вы хотите забронировать?</b>\n{service_name}\n\n"
                    f"Service ID: {service_id}\n\n"
                    f"<b>Какое количество гостей планируется?</b>\n{data['guests_count']}\n\n"
                    f"<b>Дополнительные услуги:</b>\n{extras_display}"
                )
                result = await calendar_service.create_event(
                    title=service_name,
                    description=event_description,
                    start_time=event_start,
                    end_time=event_end,
                )
                created = True

                if service_id != 9:
                    try:
                        extra_service = await service_repo.get_by_id(9)
                        extra_name = extra_service.name if extra_service else "Доп. услуга"
                        extra_start = event_start - timedelta(hours=1)
                        extra_end = event_start
                        await calendar_service.create_event(
                            title=f"{extra_name}: {service_name}",
                            description=(
                                f"<b>Доп. услуга</b>\n"
                                f"Для бронирования: {service_name}\n"
                                f"Service ID: 9\n"
                                f"Linked Service ID: {service_id}\n"
                                f"Связано с событием: {result.get('id', 'unknown')}\n"
                            ),
                            start_time=extra_start,
                            end_time=extra_end,
                        )
                    except Exception:
                        pass
            except Exception as e:
                await message.answer(f"⚠️ Не удалось создать событие в календаре: {e}")

        # Обновляем клиента в БД
        client = await _load_or_create_vk_client(message.from_id)
        client.name = data["name"]
        client.email = data.get("email")
        phone10 = _normalize_phone(data["phone"])
        if phone10:
            client.phone = phone10
        await client_repo.update(client)

        time_range = f"{event_start.strftime('%H:%M')} - {event_end.strftime('%H:%M')}"
        text = (
            "✅ Бронирование подтверждено!\n\n"
            f"📅 Дата: {event_start.strftime('%d.%m.%Y')}\n"
            f"🕒 Время: {time_range}\n"
            f"👤 Клиент: {data['name']}\n"
            f"📱 Телефон: {data['phone']}\n"
            f"👥 Гостей: {data['guests_count']}\n"
            f"⏰ Продолжительность: {duration} мин.\n"
            f"🎯 Услуга: {service_name}\n"
            + ("📅 Событие создано в календаре\n" if created else "")
        )
        await _clear_state(bot, message)
        await message.answer(
            text,
            keyboard=get_main_menu_keyboard(is_admin=message.from_id in ADMIN_IDS),
        )

    @bot.on.message(payload_contains={"a": "bk_cancel"})
    @bot.on.message(text="❌ Отменить")
    async def booking_cancel(message: Message):
        await _clear_state(bot, message)
        await message.answer("❌ Бронирование отменено.")
