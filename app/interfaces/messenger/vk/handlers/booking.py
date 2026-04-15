from __future__ import annotations

from datetime import datetime, timedelta
from enum import Enum

from vkbottle import BaseStateGroup, Keyboard, KeyboardButtonColor, Text
from vkbottle.bot import Bot, Message

from config import TELEGRAM_BOT_TOKEN
from app.core.modules.booking.availability import (
    get_time_slots_for_date as svc_get_time_slots_for_date,
    is_booking_available as svc_is_booking_available,
)
from app.core.modules.booking.extra_services import (
    build_extra_service_booking_label,
    build_extra_service_label_map,
)
from app.core.modules.booking.common import (
    format_full_name as core_format_full_name,
    format_optional_text as core_format_optional_text,
    normalize_max_guests as core_normalize_max_guests,
    normalize_min_duration_minutes as core_normalize_min_duration_minutes,
    normalize_phone10 as core_normalize_phone10,
)
from app.core.modules.booking.admin_notifications import (
    build_vk_booking_admin_notification,
    build_vk_booking_admin_notification_for_telegram,
)
from app.core.modules.booking.create_booking import (
    get_or_create_vk_client,
    sync_vk_booking_client,
)
from app.core.modules.booking.error_texts import (
    build_comment_validation_error,
    build_discount_code_validation_error,
    build_duration_too_small_error,
    build_email_validation_error,
    build_guests_validation_error,
    build_name_validation_error,
    build_phone_validation_error,
)
from app.core.modules.booking.form_data import build_db_prefilled_fields, build_initial_booking_data, merge_booking_data
from app.core.modules.booking.form_config import get_booking_field_label
from app.core.modules.booking.form_fields import get_booking_misc_fields, get_booking_required_menu_fields, get_missing_booking_fields
from app.core.modules.booking.form_prompts import (
    build_comment_prompt,
    build_discount_code_prompt,
    build_duration_prompt,
    build_email_prompt,
    build_last_name_prompt,
    build_name_prompt,
    build_phone_prompt,
)
from app.core.modules.booking.form_render import build_booking_form_text, build_booking_other_text
from app.core.modules.booking.selection_texts import (
    build_choose_extras_text,
    build_choose_guests_text,
    build_date_selection_text,
    build_no_slots_text,
    build_pick_date_first_text,
    build_time_selection_text,
)
from app.core.modules.booking.presentation import (
    build_booking_summary,
    build_vk_calendar_description,
    build_vk_confirmation_text,
)
from app.core.modules.booking.use_case import create_booking_use_case
from app.core.modules.booking.validation import (
    normalize_and_format_phone,
    validate_duration_minutes,
    validate_guests_count,
    validate_comment,
    validate_discount_code,
    validate_optional_email,
    validate_person_name,
)
from app.core.modules.services.details import build_service_details_text
from app.integrations.local.db import client_repo, extra_service_repo, service_repo
from app.integrations.local.db.models import Client
from app.interfaces.messenger.tg.services.booking_formatters import (
    format_booking_date,
    format_booking_time_range,
    format_booking_guests,
    format_extras_display,
)
from app.interfaces.messenger.tg.services.admin_notifications import send_telegram_admin_notification
from app.interfaces.messenger.vk.auth import is_vk_admin_id
from app.interfaces.messenger.vk.keyboards import get_main_menu_keyboard
from app.interfaces.messenger.vk.services.admin_notifications import send_vk_admin_notification
from app.interfaces.messenger.vk.services.service_media import send_service_details

try:
    from app.integrations.local.calendar.service import GoogleCalendarService

    CALENDAR_AVAILABLE = True
except Exception:
    GoogleCalendarService = None
    CALENDAR_AVAILABLE = False


class VkBookingState(BaseStateGroup, Enum):
    filling_form = "filling_form"
    entering_name = "entering_name"
    entering_last_name = "entering_last_name"
    entering_phone = "entering_phone"
    entering_discount_code = "entering_discount_code"
    entering_comment = "entering_comment"
    entering_email = "entering_email"
def _normalize_min_duration_minutes(raw_value: int | None) -> int:
    return core_normalize_min_duration_minutes(raw_value)


def _normalize_max_guests(raw_value: int | None) -> int:
    return core_normalize_max_guests(raw_value)


def _build_service_details_text(service) -> str:
    return build_service_details_text(service, html=False)


def _get_service_details_keyboard(service_id: int) -> str:
    kb = Keyboard(one_time=False, inline=False)
    kb.add(
        Text("✅ Перейти к бронированию", payload={"a": "bk_service_confirm", "sid": service_id}),
        color=KeyboardButtonColor.POSITIVE,
    ).row()
    kb.add(Text("📸 Услуги"), color=KeyboardButtonColor.PRIMARY).row()
    kb.add(Text("🏠 Главное меню"), color=KeyboardButtonColor.SECONDARY)
    return kb.get_json()


async def _send_service_details(message: Message, service) -> None:
    text = _build_service_details_text(service)
    await send_service_details(
        message,
        service,
        text=text,
        keyboard=_get_service_details_keyboard(service.id),
    )


def _normalize_phone(phone: str) -> str | None:
    return core_normalize_phone10(phone)


def _format_phone_display(phone10: str | None) -> str:
    if not phone10 or len(phone10) != 10:
        return "Не указан"
    return f"+7 {phone10[:3]} {phone10[3:6]} {phone10[6:8]} {phone10[8:10]}"


def _format_full_name(data: dict) -> str:
    return core_format_full_name(data)


def _format_optional_value(value: str | None) -> str:
    return core_format_optional_text(value)


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
    required_fields = set(get_booking_required_menu_fields(booking_data))
    required_color = lambda field: KeyboardButtonColor.POSITIVE if booking_data.get(field) else KeyboardButtonColor.NEGATIVE

    date_time_ready = bool(booking_data.get("date") and booking_data.get("time"))
    kb.add(
        Text("📅 Дата и время", payload={"a": "bk_date", "sid": service_id}),
        color=KeyboardButtonColor.POSITIVE if date_time_ready else KeyboardButtonColor.NEGATIVE,
    ).row()
    kb.add(Text("👥 Гости", payload={"a": "bk_guests", "sid": service_id}), color=required_color("guests_count"))
    kb.add(Text(f"⏰ {get_booking_field_label('duration')}", payload={"a": "bk_duration", "sid": service_id}), color=required_color("duration")).row()
    for field, label, emoji in (
        ("name", get_booking_field_label("name"), "👤"),
        ("last_name", get_booking_field_label("last_name"), "🧾"),
        ("phone", "Телефон", "📱"),
        ("discount_code", get_booking_field_label("discount_code"), "🏷️"),
    ):
        if field not in required_fields:
            continue
        action = "discount" if field == "discount_code" else field
        kb.add(
            Text(f"{emoji} {label}", payload={"a": f"bk_{action}", "sid": service_id}),
            color=required_color(field),
        ).row()
    if get_booking_misc_fields(booking_data):
        kb.add(Text("⚙️ Прочее", payload={"a": "bk_other", "sid": service_id}), color=KeyboardButtonColor.SECONDARY).row()
    kb.add(Text("✅ Подтвердить", payload={"a": "bk_confirm", "sid": service_id}), color=KeyboardButtonColor.POSITIVE).row()
    kb.add(Text("❌ Отменить", payload={"a": "bk_cancel"}), color=KeyboardButtonColor.NEGATIVE)
    kb.add(Text("🏠 Главное меню"), color=KeyboardButtonColor.SECONDARY)
    return kb.get_json()


def _get_other_keyboard(service_id: int, booking_data: dict) -> str:
    kb = Keyboard(one_time=False, inline=False)
    for field, label, emoji in (
        ("name", get_booking_field_label("name"), "👤"),
        ("last_name", get_booking_field_label("last_name"), "🧾"),
        ("phone", "Телефон", "📱"),
        ("discount_code", get_booking_field_label("discount_code"), "🏷️"),
        ("comment", get_booking_field_label("comment"), "💬"),
        ("extras", get_booking_field_label("extras"), "➕"),
        ("email", get_booking_field_label("email"), "📧"),
    ):
        if field not in get_booking_misc_fields(booking_data):
            continue
        action = "discount" if field == "discount_code" else field
        kb.add(Text(f"{emoji} {label}", payload={"a": f"bk_{action}", "sid": service_id}), color=KeyboardButtonColor.PRIMARY).row()
    kb.add(Text("↩️ К форме", payload={"a": "bk_back_form", "sid": service_id}), color=KeyboardButtonColor.SECONDARY)
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


def _get_extras_keyboard(service_id: int, extra_services: list, selected: list[int]) -> str:
    kb = Keyboard(one_time=False, inline=False)
    for extra_service in extra_services:
        mark = "✅ " if extra_service.id in selected else ""
        label = build_extra_service_booking_label(extra_service)
        if len(label) > 36:
            label = f"{label[:33].rstrip()}..."
        kb.add(
            Text(
                f"{mark}{label}",
                payload={"a": "bk_extra_toggle", "sid": service_id, "x": extra_service.id},
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
        kb.add(
            Text(
                f"🕒 {s}",
                payload={"a": "bk_time_set", "sid": service_id, "d": date_value, "s": s, "e": slot["end"]},
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


def _get_time_total_pages(slots: list[dict], page_size: int = 8) -> int:
    total = len(slots)
    return max(1, (total + page_size - 1) // page_size)


def _get_back_form_keyboard(service_id: int) -> str:
    kb = Keyboard(one_time=False, inline=False)
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
    text = build_booking_form_text(
        service_name=service_name,
        date_display=format_booking_date(booking_data.get("date")),
        time_display=format_booking_time_range(booking_data.get("time"), duration_minutes),
        name_display=booking_data.get("name") or "Не указано",
        last_name_display=booking_data.get("last_name") or "Не указано",
        phone_display=booking_data.get("phone") or "Не указан",
        discount_code_display=_format_optional_value(booking_data.get("discount_code")),
        comment_display=_format_optional_value(booking_data.get("comment")),
        guests_display=format_booking_guests(booking_data.get("guests_count")),
        duration_display=f"{duration_minutes} мин.",
        extras_display=format_extras_display(booking_data.get("extras", []), booking_data.get("extra_labels")),
        email_display=booking_data.get("email") or "Не указан",
        required_mark="⚫",
        optional_mark="⚪",
        instruction_text="Выберите параметр:",
        bold=False,
        db_prefilled_fields=booking_data.get("db_prefilled_fields", []),
    )
    text = text.replace("⚫ Дата:", ("🟢" if booking_data.get("date") else "🔴") + " Дата:", 1)
    text = text.replace("⚫ Время:", ("🟢" if booking_data.get("time") else "🔴") + " Время:", 1)
    text = text.replace("⚫ Имя:", ("🟢" if booking_data.get("name") else "🔴") + " Имя:", 1)
    text = text.replace("⚫ Фамилия:", ("🟢" if booking_data.get("last_name") else "🔴") + " Фамилия:", 1)
    text = text.replace("⚫ Номер телефона:", ("🟢" if booking_data.get("phone") else "🔴") + " Номер телефона:", 1)
    text = text.replace("⚫ Количество гостей:", ("🟢" if booking_data.get("guests_count") else "🔴") + " Количество гостей:", 1)

    await _set_state(bot, message, VkBookingState.filling_form, booking_data)
    await message.answer(text, keyboard=_get_form_keyboard(service_id, booking_data))


def _build_other_text(booking_data: dict) -> str:
    return build_booking_other_text(
        service_name=booking_data.get("service_name", ""),
        name_display=booking_data.get("name") or "Не указано",
        last_name_display=booking_data.get("last_name") or "Не указано",
        phone_display=booking_data.get("phone") or "Не указан",
        discount_code_display=_format_optional_value(booking_data.get("discount_code")),
        comment_display=_format_optional_value(booking_data.get("comment")),
        extras_display=format_extras_display(booking_data.get("extras", []), booking_data.get("extra_labels")),
        email_display=booking_data.get("email") or "Не указан",
        optional_mark="⚪",
        instruction_text="Выберите параметр:",
        bold=False,
        db_prefilled_fields=booking_data.get("db_prefilled_fields", []),
    )


async def _show_time_selection_screen(bot: Bot, message: Message, data: dict, date_value: str, page: int = 0) -> None:
    service_id = int(data["service_id"])
    data["date"] = date_value
    await _set_state(bot, message, VkBookingState.filling_form, data)

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
        await message.answer(
            build_no_slots_text(date_display=selected_date.strftime("%d.%m.%Y"), html=False),
            keyboard=_get_current_form_keyboard(data),
        )
        return
    total_pages = _get_time_total_pages(normalized_slots)
    page = max(0, min(page, total_pages - 1))
    text = build_time_selection_text(date_display=selected_date.strftime("%d.%m.%Y"), html=False)
    if total_pages > 1:
        text = f"{text}\n\nСтраница {page + 1} из {total_pages}"
    await message.answer(
        text,
        keyboard=_get_time_keyboard(service_id, date_value, normalized_slots, page=page),
    )


async def _update_booking_data_and_show_form(bot: Bot, message: Message, current_data: dict, **updates) -> None:
    booking_data = merge_booking_data(
        current_data,
        state_service_name=current_data.get("service_name", ""),
        updates=updates,
    )
    await _show_form(bot, message, booking_data)


def _get_current_form_keyboard(data: dict) -> str:
    service_id = int(data["service_id"])
    return _get_form_keyboard(service_id, data)


async def _load_or_create_vk_client(vk_id: int, fallback_name: str | None = None) -> Client:
    return await get_or_create_vk_client(
        client_repo=client_repo,
        vk_id=vk_id,
        fallback_name=fallback_name,
    )


async def _get_vk_first_name(message: Message) -> str:
    try:
        user = await message.get_user()
        first_name = getattr(user, "first_name", None)
        if first_name:
            return str(first_name).strip()
    except Exception:
        pass
    return "Пользователь"


async def _get_vk_name_parts(message: Message) -> tuple[str, str]:
    try:
        user = await message.get_user()
        first_name = str(getattr(user, "first_name", "") or "").strip() or "Пользователь"
        last_name = str(getattr(user, "last_name", "") or "").strip()
        return first_name, last_name
    except Exception:
        return "Пользователь", ""


def register_booking_handlers(bot: Bot):
    @bot.on.message(payload_contains={"a": "bk_service"})
    async def booking_start(message: Message):
        payload = message.get_payload_json() or {}
        service_id = int(payload.get("sid"))
        service = await service_repo.get_by_id(service_id)
        if not service:
            await message.answer("Услуга не найдена.", keyboard=get_main_menu_keyboard(is_admin=await is_vk_admin_id(message.from_id)))
            return

        await _send_service_details(message, service)

    @bot.on.message(payload_contains={"a": "bk_service_confirm"})
    async def booking_service_confirm(message: Message):
        payload = message.get_payload_json() or {}
        service_id = int(payload.get("sid"))
        service = await service_repo.get_by_id(service_id)
        if not service:
            await message.answer("Услуга не найдена.", keyboard=get_main_menu_keyboard(is_admin=await is_vk_admin_id(message.from_id)))
            return

        vk_first_name, vk_last_name = await _get_vk_name_parts(message)
        client = await _load_or_create_vk_client(message.from_id, fallback_name=vk_first_name)
        display_name = client.name if client and client.name and client.name != "Пользователь" else vk_first_name
        display_last_name = client.last_name if client and client.last_name else vk_last_name
        phone_display = _format_phone_display(client.phone) if client and client.phone else None
        booking_data = build_initial_booking_data(
            service_id=service_id,
            service_name=service.name,
            max_num_clients=service.max_num_clients,
            min_duration_minutes=service.min_duration_minutes,
            name=display_name,
            last_name=display_last_name,
            phone=phone_display,
            email=client.email if client else None,
            discount_code=client.discount_code if client else None,
            db_prefilled_fields=build_db_prefilled_fields(
                name=(client.name if client and client.name != "Пользователь" else None),
                last_name=client.last_name if client else None,
                phone=client.phone if client else None,
                discount_code=client.discount_code if client else None,
            ),
        )
        await _show_form(bot, message, booking_data)

    @bot.on.message(payload_contains={"a": "bk_back_form"}, state=VkBookingState.filling_form)
    @bot.on.message(text="↩️ К форме", state=VkBookingState.filling_form)
    async def booking_back_form(message: Message):
        await _show_form(bot, message, _get_booking_data(message))

    @bot.on.message(payload_contains={"a": "bk_other"}, state=VkBookingState.filling_form)
    async def booking_other(message: Message):
        data = _get_booking_data(message)
        await message.answer(_build_other_text(data), keyboard=_get_other_keyboard(int(data["service_id"]), data))

    @bot.on.message(payload_contains={"a": "bk_date"}, state=VkBookingState.filling_form)
    @bot.on.message(text="📅 Дата и время", state=VkBookingState.filling_form)
    async def booking_date(message: Message):
        data = _get_booking_data(message)
        await message.answer(
            build_date_selection_text(html=False),
            keyboard=_get_date_keyboard(int(data["service_id"]), 0),
        )

    @bot.on.message(payload_contains={"a": "bk_date_week"}, state=VkBookingState.filling_form)
    async def booking_date_week(message: Message):
        payload = message.get_payload_json() or {}
        sid = int(payload.get("sid"))
        week = int(payload.get("w", 0))
        await message.answer(build_date_selection_text(html=False), keyboard=_get_date_keyboard(sid, week))

    @bot.on.message(payload_contains={"a": "bk_date_set"}, state=VkBookingState.filling_form)
    async def booking_date_set(message: Message):
        payload = message.get_payload_json() or {}
        data = _get_booking_data(message)
        await _show_time_selection_screen(bot, message, data, payload.get("d"), page=0)

    @bot.on.message(payload_contains={"a": "bk_time"}, state=VkBookingState.filling_form)
    @bot.on.message(text="🕒 Время", state=VkBookingState.filling_form)
    async def booking_time(message: Message):
        data = _get_booking_data(message)
        if not data.get("date"):
            await message.answer(build_pick_date_first_text(html=False), keyboard=_get_current_form_keyboard(data))
            return
        await _show_time_selection_screen(bot, message, data, data["date"], page=0)

    @bot.on.message(payload_contains={"a": "bk_time_page"}, state=VkBookingState.filling_form)
    async def booking_time_page(message: Message):
        payload = message.get_payload_json() or {}
        data = _get_booking_data(message)
        date_value = payload.get("d") or data.get("date")
        page = int(payload.get("p", 0))
        if not date_value:
            await message.answer(build_pick_date_first_text(html=False), keyboard=_get_current_form_keyboard(data))
            return
        await _show_time_selection_screen(bot, message, data, date_value, page=page)

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
            build_duration_prompt(min_duration=min_duration, html=False, detailed=False),
            keyboard=_get_duration_keyboard(int(data["service_id"]), min_duration),
        )

    @bot.on.message(payload_contains={"a": "bk_duration_set"}, state=VkBookingState.filling_form)
    async def booking_duration_set(message: Message):
        payload = message.get_payload_json() or {}
        data = _get_booking_data(message)
        service = await service_repo.get_by_id(int(data["service_id"]))
        min_duration = _normalize_min_duration_minutes(service.min_duration_minutes if service else 60)
        duration = int(payload.get("m", min_duration))
        if validate_duration_minutes(duration, min_duration=min_duration) == "too_small":
            await message.answer(build_duration_too_small_error(min_duration=min_duration, html=False), keyboard=_get_duration_keyboard(int(data["service_id"]), min_duration))
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
        await message.answer(build_choose_guests_text(html=False), keyboard=_get_guests_keyboard(int(data["service_id"]), max_guests))

    @bot.on.message(payload_contains={"a": "bk_guests_set"}, state=VkBookingState.filling_form)
    async def booking_guests_set(message: Message):
        payload = message.get_payload_json() or {}
        data = _get_booking_data(message)
        service = await service_repo.get_by_id(int(data["service_id"]))
        max_guests = _normalize_max_guests(service.max_num_clients if service else data.get("max_num_clients", 1))
        data["max_num_clients"] = max_guests
        guests_count = int(payload.get("g"))
        if validate_guests_count(guests_count, max_guests=max_guests) == "too_many":
            await message.answer(build_guests_validation_error(max_guests=max_guests, html=False), keyboard=_get_guests_keyboard(int(data["service_id"]), max_guests))
            return
        data["guests_count"] = guests_count
        await _show_form(bot, message, data)

    @bot.on.message(payload_contains={"a": "bk_extras"}, state=VkBookingState.filling_form)
    @bot.on.message(text="➕ Доп. услуги", state=VkBookingState.filling_form)
    async def booking_extras(message: Message):
        data = _get_booking_data(message)
        extra_services = await extra_service_repo.get_all_active()
        data["extra_labels"] = build_extra_service_label_map(extra_services)
        selected_extras = [
            int(extra_id)
            for extra_id in data.get("extras", [])
            if isinstance(extra_id, int) or (isinstance(extra_id, str) and extra_id.isdigit())
        ]
        await _set_state(bot, message, VkBookingState.filling_form, data)
        if not extra_services:
            await message.answer(
                "➕ Выберите дополнительные услуги:\n\nСейчас нет доступных доп. услуг.",
                keyboard=_get_back_form_keyboard(int(data["service_id"])),
            )
            return
        await message.answer(
            build_choose_extras_text(html=False),
            keyboard=_get_extras_keyboard(int(data["service_id"]), extra_services, selected_extras),
        )

    @bot.on.message(payload_contains={"a": "bk_extra_toggle"}, state=VkBookingState.filling_form)
    async def booking_extra_toggle(message: Message):
        payload = message.get_payload_json() or {}
        data = _get_booking_data(message)
        extra_services = await extra_service_repo.get_all_active()
        data["extra_labels"] = build_extra_service_label_map(extra_services)
        extra_id = int(payload.get("x"))
        extras = [
            int(extra)
            for extra in data.get("extras", [])
            if isinstance(extra, int) or (isinstance(extra, str) and extra.isdigit())
        ]
        if extra_id in extras:
            extras.remove(extra_id)
        else:
            extras.append(extra_id)
        data = merge_booking_data(
            data,
            state_service_name=data.get("service_name", ""),
            updates={"extras": extras, "extra_labels": data.get("extra_labels", {})},
        )
        await _set_state(bot, message, VkBookingState.filling_form, data)
        await message.answer(
            build_choose_extras_text(html=False),
            keyboard=_get_extras_keyboard(int(data["service_id"]), extra_services, extras),
        )

    @bot.on.message(payload_contains={"a": "bk_name"}, state=VkBookingState.filling_form)
    @bot.on.message(text="👤 Имя", state=VkBookingState.filling_form)
    async def booking_name(message: Message):
        data = _get_booking_data(message)
        await _set_state(bot, message, VkBookingState.entering_name, data)
        await message.answer(build_name_prompt(html=False), keyboard=_get_back_form_keyboard(int(data["service_id"])))

    @bot.on.message(state=VkBookingState.entering_name)
    async def booking_name_input(message: Message):
        data = _get_booking_data(message)
        name, error_code = validate_person_name(message.text or "")
        if error_code:
            await message.answer(build_name_validation_error(field_label="Имя", html=False), keyboard=_get_back_form_keyboard(int(data["service_id"])))
            return
        await _update_booking_data_and_show_form(bot, message, data, name=name)
    @bot.on.message(payload_contains={"a": "bk_last_name"}, state=VkBookingState.filling_form)
    @bot.on.message(text="Фамилия", state=VkBookingState.filling_form)
    async def booking_last_name(message: Message):
        data = _get_booking_data(message)
        await _set_state(bot, message, VkBookingState.entering_last_name, data)
        await message.answer(build_last_name_prompt(html=False), keyboard=_get_back_form_keyboard(int(data["service_id"])))

    @bot.on.message(state=VkBookingState.entering_last_name)
    async def booking_last_name_input(message: Message):
        data = _get_booking_data(message)
        last_name, error_code = validate_person_name(message.text or "")
        if error_code:
            await message.answer(build_name_validation_error(field_label="Фамилия", html=False), keyboard=_get_back_form_keyboard(int(data["service_id"])))
            return
        await _update_booking_data_and_show_form(bot, message, data, last_name=last_name)


    @bot.on.message(payload_contains={"a": "bk_phone"}, state=VkBookingState.filling_form)
    @bot.on.message(text="📱 Телефон", state=VkBookingState.filling_form)
    async def booking_phone(message: Message):
        data = _get_booking_data(message)
        await _set_state(bot, message, VkBookingState.entering_phone, data)
        await message.answer(build_phone_prompt(html=False), keyboard=_get_back_form_keyboard(int(data["service_id"])))

    @bot.on.message(state=VkBookingState.entering_phone)
    async def booking_phone_input(message: Message):
        data = _get_booking_data(message)
        formatted_phone = normalize_and_format_phone(message.text or "")
        if not formatted_phone:
            await message.answer(build_phone_validation_error(html=False), keyboard=_get_back_form_keyboard(int(data["service_id"])))
            return
        await _update_booking_data_and_show_form(bot, message, data, phone=formatted_phone)

    @bot.on.message(payload_contains={"a": "bk_discount"}, state=VkBookingState.filling_form)
    @bot.on.message(text="🏷️ Код для скидки", state=VkBookingState.filling_form)
    async def booking_discount(message: Message):
        data = _get_booking_data(message)
        await _set_state(bot, message, VkBookingState.entering_discount_code, data)
        await message.answer(
            build_discount_code_prompt(html=False, back_label="К форме"),
            keyboard=_get_back_form_keyboard(int(data["service_id"])),
        )

    @bot.on.message(state=VkBookingState.entering_discount_code)
    async def booking_discount_input(message: Message):
        data = _get_booking_data(message)
        discount_code, error_code = validate_discount_code(message.text or "")
        if error_code == "too_long":
            await message.answer(build_discount_code_validation_error(max_length=100, html=False), keyboard=_get_back_form_keyboard(int(data["service_id"])))
            return
        await _update_booking_data_and_show_form(bot, message, data, discount_code=discount_code)

    @bot.on.message(payload_contains={"a": "bk_comment"}, state=VkBookingState.filling_form)
    @bot.on.message(text="💬 Комментарий", state=VkBookingState.filling_form)
    async def booking_comment(message: Message):
        data = _get_booking_data(message)
        await _set_state(bot, message, VkBookingState.entering_comment, data)
        await message.answer(
            build_comment_prompt(html=False, back_label="К форме"),
            keyboard=_get_back_form_keyboard(int(data["service_id"])),
        )

    @bot.on.message(state=VkBookingState.entering_comment)
    async def booking_comment_input(message: Message):
        data = _get_booking_data(message)
        comment, error_code = validate_comment(message.text or "")
        if error_code == "too_long":
            await message.answer(build_comment_validation_error(max_length=500, html=False), keyboard=_get_back_form_keyboard(int(data["service_id"])))
            return
        await _update_booking_data_and_show_form(bot, message, data, comment=comment)

    @bot.on.message(payload_contains={"a": "bk_email"}, state=VkBookingState.filling_form)
    @bot.on.message(text="📧 E-mail", state=VkBookingState.filling_form)
    async def booking_email(message: Message):
        data = _get_booking_data(message)
        await _set_state(bot, message, VkBookingState.entering_email, data)
        await message.answer(build_email_prompt(html=False, skip_label="-"), keyboard=_get_back_form_keyboard(int(data["service_id"])))

    @bot.on.message(state=VkBookingState.entering_email)
    async def booking_email_input(message: Message):
        data = _get_booking_data(message)
        email, error_code = validate_optional_email(message.text or "", skip_tokens={"-"})
        if error_code == "invalid":
            await message.answer(build_email_validation_error(html=False, skip_label="-"), keyboard=_get_back_form_keyboard(int(data["service_id"])))
            return
        await _update_booking_data_and_show_form(bot, message, data, email=email)

    @bot.on.message(payload_contains={"a": "bk_confirm"}, state=VkBookingState.filling_form)
    @bot.on.message(text="✅ Подтвердить", state=VkBookingState.filling_form)
    async def booking_confirm(message: Message):
        data = _get_booking_data(message)
        missing = get_missing_booking_fields(data)
        if missing:
            await message.answer("Не все поля заполнены. Заполните форму до конца.", keyboard=_get_current_form_keyboard(data))
            return

        service_id = int(data["service_id"])
        service = await service_repo.get_by_id(service_id)
        if service and validate_guests_count(
            int(data.get("guests_count") or 0),
            max_guests=_normalize_max_guests(service.max_num_clients),
        ) == "too_many":
            await message.answer(build_guests_validation_error(max_guests=_normalize_max_guests(service.max_num_clients), html=False), keyboard=_get_current_form_keyboard(data))
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
            await message.answer(f"❌ Время недоступно: {reason}", keyboard=_get_current_form_keyboard(data))
            return

        event_start = start_dt
        event_end = event_start + timedelta(minutes=duration)
        time_range = f"{event_start.strftime('%H:%M')} - {event_end.strftime('%H:%M')}"
        preview_summary = build_booking_summary(
            booking_data=data,
            service_name=service_name,
            service_id=service_id,
            date_display=event_start.strftime('%d.%m.%Y'),
            time_range=time_range,
            duration_minutes=duration,
        )

        async def _sync_client() -> None:
            await sync_vk_booking_client(
                client_repo=client_repo,
                vk_id=message.from_id,
                booking_data=data,
                fallback_name=await _get_vk_first_name(message),
            )

        use_case_result = await create_booking_use_case(
            booking_data=data,
            service_name=service_name,
            service_id=service_id,
            date_display=event_start.strftime('%d.%m.%Y'),
            time_range=time_range,
            duration_minutes=duration,
            event_start=event_start,
            event_end=event_end,
            calendar_available=CALENDAR_AVAILABLE,
            calendar_service_cls=GoogleCalendarService,
            calendar_description=build_vk_calendar_description(preview_summary, vk_id=message.from_id),
            sync_client=_sync_client,
            admin_notification_builder=lambda summary: build_vk_booking_admin_notification_for_telegram(
                summary=summary,
                vk_id=message.from_id,
            ),
        )
        summary = use_case_result.summary
        notification = use_case_result.admin_notification
        vk_notification = build_vk_booking_admin_notification(
            summary=summary,
            vk_id=message.from_id,
        )
        created = use_case_result.finalize_result.calendar_result.created
        if use_case_result.finalize_result.calendar_result.error:
            await message.answer(
                f"⚠️ Не удалось создать событие в календаре: {use_case_result.finalize_result.calendar_result.error}",
                keyboard=_get_current_form_keyboard(data),
            )

        # Уведомляем администраторов в Telegram о брони из VK
        try:
            if TELEGRAM_BOT_TOKEN:
                await send_telegram_admin_notification(
                    notification=notification,
                    bot_token=TELEGRAM_BOT_TOKEN,
                )
        except Exception:
            pass

        try:
            await send_vk_admin_notification(
                notification=vk_notification,
                api=message.ctx_api,
            )
        except Exception:
            pass

        text = build_vk_confirmation_text(summary, calendar_event_created=created)
        await _clear_state(bot, message)
        await message.answer(
            text,
            keyboard=get_main_menu_keyboard(is_admin=await is_vk_admin_id(message.from_id)),
        )

    @bot.on.message(payload_contains={"a": "bk_cancel"})
    @bot.on.message(text="❌ Отменить")
    async def booking_cancel(message: Message):
        await _clear_state(bot, message)
        await message.answer("❌ Бронирование отменено.", keyboard=get_main_menu_keyboard(is_admin=await is_vk_admin_id(message.from_id)))


