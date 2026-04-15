import logging
from aiogram import Dispatcher, F
from aiogram.types import CallbackQuery, Message, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from datetime import datetime, timedelta, date

from app.interfaces.messenger.tg.keyboards import (
    TIME_SELECTION_PAGE_SIZE,
    get_booking_form_keyboard,
    get_booking_other_keyboard,
    get_main_menu_keyboard,
    get_date_selection_keyboard,
    get_time_selection_keyboard,
    get_time_selection_total_pages,
    get_duration_selection_keyboard,
)
from app.interfaces.messenger.tg.states import BookingStates
from app.core.modules.booking.availability import (
    build_default_time_slots as svc_build_default_time_slots,
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
    build_telegram_booking_admin_notification,
    build_telegram_booking_admin_notification_for_vk,
)
from app.core.modules.booking.create_booking import sync_telegram_booking_client
from app.core.modules.booking.error_texts import (
    build_comment_validation_error,
    build_discount_code_validation_error,
    build_duration_invalid_step_error,
    build_duration_too_large_error,
    build_duration_too_small_error,
    build_email_validation_error,
    build_guests_validation_error,
    build_name_validation_error,
    build_phone_validation_error,
)
from app.core.modules.booking.form_data import (
    build_db_prefilled_fields,
    build_initial_booking_data,
    merge_booking_data,
    resolve_booking_service_name,
)
from app.core.modules.booking.form_fields import get_missing_booking_field_labels
from app.core.modules.booking.form_prompts import (
    build_comment_prompt,
    build_discount_code_prompt,
    build_duration_prompt,
    build_email_prompt,
    build_guests_count_prompt,
    build_last_name_prompt,
    build_name_prompt,
    build_phone_prompt,
)
from app.core.modules.booking.form_render import build_booking_form_text, build_booking_other_text
from app.core.modules.booking.selection_texts import (
    build_choose_extras_text,
    build_date_selection_text,
    build_duration_hint,
    build_no_slots_text,
    build_pick_date_first_text,
    build_time_selection_text,
)
from app.core.modules.booking.presentation import (
    build_booking_summary,
    build_telegram_calendar_description,
    build_telegram_confirmation_text,
)
from app.core.modules.booking.use_case import create_booking_use_case
from app.core.modules.booking.validation import (
    normalize_and_format_phone,
    parse_positive_int,
    validate_comment,
    validate_discount_code,
    validate_duration_minutes,
    validate_guests_count,
    validate_optional_email,
    validate_person_name,
)
from app.interfaces.messenger.tg.services.booking_formatters import (
    format_booking_date as svc_format_booking_date,
    format_booking_time_range as svc_format_booking_time_range,
    format_booking_guests as svc_format_booking_guests,
    format_extras_display as svc_format_extras_display,
)
from app.interfaces.messenger.tg.services.admin_notifications import send_telegram_admin_notification
from app.interfaces.messenger.vk.services.admin_notifications import send_vk_admin_notification
from app.integrations.local.db import extra_service_repo, service_repo

logger = logging.getLogger(__name__)

# Опциональный импорт Google Calendar
try:
    from app.integrations.local.calendar.service import GoogleCalendarService
    CALENDAR_AVAILABLE = True
    logger.info("Google Calendar импортирован успешно")
except ImportError as e:
    GoogleCalendarService = None
    CALENDAR_AVAILABLE = False
    logger.warning("Google Calendar недоступен: %s", e)
    logger.info("Установите зависимости: pip install google-api-python-client google-auth-httplib2 google-auth-oauthlib")

def _normalize_min_duration_minutes(raw_value: int | None) -> int:
    return core_normalize_min_duration_minutes(raw_value)


def _get_min_duration_from_state(data: dict) -> int:
    return _normalize_min_duration_minutes(data.get("min_duration_minutes", 60))


def _normalize_max_guests(raw_value: int | None) -> int:
    return core_normalize_max_guests(raw_value)


def _get_max_guests_from_state(data: dict) -> int:
    return _normalize_max_guests(data.get("max_num_clients", 1))


def _build_default_time_slots(duration_minutes: int = 60, all_day: bool = False) -> list[dict]:
    return svc_build_default_time_slots(duration_minutes=duration_minutes, all_day=all_day)

async def _get_time_slots_for_date(
    target_date: date,
    service_id: int,
    service_name: str | None,
    duration_minutes: int = 60,
    all_day: bool = False,
) -> tuple[list[dict], bool, str | None]:
    return await svc_get_time_slots_for_date(
        target_date=target_date,
        service_id=service_id,
        service_name=service_name,
        duration_minutes=duration_minutes,
        all_day=all_day,
    )


async def _is_booking_available(
    target_date: date,
    start_time: datetime,
    duration_minutes: int,
    service_id: int,
    service_name: str | None,
) -> tuple[bool, str | None]:
    return await svc_is_booking_available(
        target_date=target_date,
        start_time=start_time,
        duration_minutes=duration_minutes,
        service_id=service_id,
        service_name=service_name,
    )

def _format_booking_date(date_value) -> str:
    return svc_format_booking_date(date_value)


def _format_booking_time_range(time_value, duration_minutes: int) -> str:
    return svc_format_booking_time_range(time_value, duration_minutes)


def _format_booking_guests(guests_value) -> str:
    return svc_format_booking_guests(guests_value)


def _format_extras_display(extras: list, extra_labels: dict | None = None) -> str:
    return svc_format_extras_display(extras, extra_labels)

def _format_full_name(booking_data: dict) -> str:
    return core_format_full_name(booking_data)


def _format_optional_booking_value(value: str | None) -> str:
    return core_format_optional_text(value)


def _normalize_stored_phone(phone: str | None) -> str | None:
    return core_normalize_phone10(phone)


def _get_back_to_booking_form_keyboard(service_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🔙 Назад", callback_data=f"booking_back_from_time_{service_id}")]
        ]
    )


def _build_booking_form_text(service_name: str, booking_data: dict, state_data: dict) -> str:
    duration_minutes = booking_data.get("duration") or _get_min_duration_from_state(state_data)
    date_display = _format_booking_date(booking_data.get("date"))
    time_display = _format_booking_time_range(booking_data.get("time"), duration_minutes)
    guests_display = _format_booking_guests(booking_data.get("guests_count"))
    email_display = booking_data.get("email") or "Не указан"
    extras_display = _format_extras_display(booking_data.get("extras", []), booking_data.get("extra_labels"))
    return build_booking_form_text(
        service_name=service_name,
        date_display=date_display,
        time_display=time_display,
        name_display=booking_data.get("name") or "Не указано",
        last_name_display=booking_data.get("last_name") or "Не указано",
        phone_display=booking_data.get("phone") or "Не указан",
        discount_code_display=_format_optional_booking_value(booking_data.get("discount_code")),
        comment_display=_format_optional_booking_value(booking_data.get("comment")),
        guests_display=guests_display,
        duration_display=f"{duration_minutes} мин.",
        extras_display=extras_display,
        email_display=email_display,
        required_mark="‼️",
        optional_mark="⚪",
        instruction_text="Выберите параметр для заполнения:",
        bold=True,
        discount_code_mark="🏷️",
        comment_mark="💬",
        duration_mark="⏰",
        extras_mark="➕",
        email_mark="📧",
        db_prefilled_fields=booking_data.get("db_prefilled_fields", []),
    )


def _build_booking_other_menu_text(service_name: str, booking_data: dict) -> str:
    extras_display = _format_extras_display(booking_data.get("extras", []), booking_data.get("extra_labels"))
    return build_booking_other_text(
        service_name=service_name,
        name_display=booking_data.get("name") or "Не указано",
        last_name_display=booking_data.get("last_name") or "Не указано",
        phone_display=booking_data.get("phone") or "Не указан",
        discount_code_display=_format_optional_booking_value(booking_data.get("discount_code")),
        comment_display=_format_optional_booking_value(booking_data.get("comment")),
        extras_display=extras_display,
        email_display=booking_data.get("email") or "Не указан",
        optional_mark="⚪",
        instruction_text="Выберите параметр для заполнения:",
        bold=True,
        discount_code_mark="🏷️",
        comment_mark="💬",
        extras_mark="➕",
        email_mark="📧",
        db_prefilled_fields=booking_data.get("db_prefilled_fields", []),
    )


async def _render_booking_form_message(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    service_id = data.get("service_id")
    if not service_id:
        return
    booking_data = data.get("booking_data", {})
    service_name = resolve_booking_service_name(data, booking_data)
    text = _build_booking_form_text(service_name, booking_data, data)
    await message.answer(
        text,
        reply_markup=get_booking_form_keyboard(service_id, booking_data),
        parse_mode="HTML",
    )


async def _update_booking_data_and_show_form(message: Message, state: FSMContext, **updates) -> None:
    data = await state.get_data()
    booking_data = merge_booking_data(
        data.get("booking_data", {}),
        state_service_name=data.get("service_name", ""),
        updates=updates,
    )
    await state.update_data(booking_data=booking_data)
    await state.set_state(BookingStates.filling_form)
    await _render_booking_form_message(message, state)


async def start_booking(callback: CallbackQuery, state: FSMContext):
    """Начало бронирования."""
    service_id = int(callback.data.split("_")[2])
    service = await service_repo.get_by_id(service_id)
    
    if not service:
        await callback.answer("Услуга не найдена", show_alert=True)
        return
    min_duration = _normalize_min_duration_minutes(service.min_duration_minutes)
    max_guests = _normalize_max_guests(service.max_num_clients)
    
    from app.integrations.local.db import client_repo
    telegram_id = callback.from_user.id
    existing_client = await client_repo.get_by_telegram_id(telegram_id)

    normalized_phone = _normalize_stored_phone(existing_client.phone if existing_client else None)
    if existing_client:
        phone_display = None
        if normalized_phone:
            phone_display = f"+7 {normalized_phone[:3]} {normalized_phone[3:6]} {normalized_phone[6:8]} {normalized_phone[8:10]}"

        booking_data = build_initial_booking_data(
            service_id=service_id,
            service_name=service.name,
            max_num_clients=max_guests,
            min_duration_minutes=min_duration,
            name=existing_client.name,
            last_name=getattr(existing_client, "last_name", None),
            phone=phone_display,
            email=existing_client.email,
            discount_code=getattr(existing_client, "discount_code", None),
            db_prefilled_fields=build_db_prefilled_fields(
                name=existing_client.name,
                last_name=getattr(existing_client, "last_name", None),
                phone=normalized_phone,
                discount_code=getattr(existing_client, "discount_code", None),
            ),
        )
        await state.update_data(
            service_id=service_id,
            service_name=service.name,
            min_duration_minutes=min_duration,
            max_num_clients=max_guests,
            booking_data=booking_data,
        )
    else:
        booking_data = build_initial_booking_data(
            service_id=service_id,
            service_name=service.name,
            max_num_clients=max_guests,
            min_duration_minutes=min_duration,
        )
        await state.update_data(
            service_id=service_id,
            service_name=service.name,
            min_duration_minutes=min_duration,
            max_num_clients=max_guests,
            booking_data=booking_data,
        )
    await state.set_state(BookingStates.filling_form)
    
    await show_booking_form(callback, state)

async def show_booking_form(callback: CallbackQuery, state: FSMContext):
    """Показ формы бронирования."""
    data = await state.get_data()
    booking_data = data.get('booking_data', {})
    service_name = booking_data.get('service_name') or data.get('service_name', '')
    service_id = data.get('service_id')
    text = _build_booking_form_text(service_name, booking_data, data)

    if service_id is None:
        await callback.answer("Ошибка: ID услуги не найден", show_alert=True)
        return
    
    try:
        await callback.message.edit_text(
            text,
            reply_markup=get_booking_form_keyboard(service_id, booking_data),
            parse_mode="HTML"
        )
    except Exception:
        try:
            await callback.message.delete()
        except Exception:
            pass
        await callback.message.answer(
            text,
            reply_markup=get_booking_form_keyboard(service_id, booking_data),
            parse_mode="HTML"
        )


async def _show_time_selection_for_date(
    callback: CallbackQuery,
    state: FSMContext,
    *,
    service_id: int,
    selected_date: str,
    page: int = 0,
) -> None:
    data = await state.get_data()
    booking_data = data.get("booking_data", {})
    booking_data["date"] = selected_date
    if "service_name" not in booking_data:
        booking_data["service_name"] = data.get("service_name", "")
    await state.update_data(booking_data=booking_data)

    try:
        selected_date_obj = datetime.strptime(selected_date, "%Y-%m-%d").date()
        service_name = booking_data.get("service_name") or data.get("service_name")
        duration_minutes = booking_data.get("duration") or _get_min_duration_from_state(data)
        is_all_day = bool(booking_data.get("is_all_day"))
        time_slots, used_calendar, calendar_error = await _get_time_slots_for_date(
            selected_date_obj, service_id, service_name, duration_minutes, all_day=is_all_day
        )

        if not time_slots and used_calendar:
            await callback.message.edit_text(
                build_no_slots_text(date_display=selected_date_obj.strftime("%d.%m.%Y"), html=True),
                reply_markup=get_booking_form_keyboard(service_id, booking_data),
                parse_mode="HTML",
            )
            return

        if calendar_error:
            await callback.answer("Не удалось получить данные календаря. Показаны резервные слоты.")

        await state.update_data(time_slots=time_slots)
        duration_hint = build_duration_hint(
            is_all_day=is_all_day,
            min_duration=int(_get_min_duration_from_state(data)),
            selected_duration=duration_minutes,
        )
        total_pages = get_time_selection_total_pages(time_slots, page_size=TIME_SELECTION_PAGE_SIZE)
        page = max(0, min(page, total_pages - 1))
        text = build_time_selection_text(
            date_display=selected_date_obj.strftime("%d.%m.%Y"),
            html=True,
            duration_hint=duration_hint,
        )
        if total_pages > 1:
            text = f"{text}\n\nСтраница {page + 1} из {total_pages}"
        await callback.message.edit_text(
            text,
            reply_markup=get_time_selection_keyboard(service_id, time_slots, selected_date, page=page),
            parse_mode="HTML",
        )
    except Exception as e:
        print(f"Ошибка выбора времени: {e}")
        await callback.message.edit_text(
            "⚠️ <b>Не удалось получить доступные слоты</b>\n\n"
            "Пожалуйста, попробуйте позже или выберите другую дату.",
            reply_markup=get_booking_form_keyboard(service_id, booking_data),
            parse_mode="HTML",
        )

async def select_date(callback: CallbackQuery, state: FSMContext):
    """Выбор даты бронирования."""
    parts = callback.data.split("_")
    if len(parts) < 3:
        await callback.answer("Ошибка в данных", show_alert=True)
        return
    
    service_id = int(parts[2])
    
    await callback.message.edit_text(
        build_date_selection_text(html=True),
        reply_markup=get_date_selection_keyboard(service_id),
        parse_mode="HTML"
    )

async def select_time(callback: CallbackQuery, state: FSMContext):
    """Выбор времени бронирования."""
    parts = callback.data.split("_")
    
    if len(parts) < 3:
        await callback.answer("Ошибка в данных", show_alert=True)
        return
    
    if parts[2] == 'None' or parts[2] == 'null':
        await callback.answer("Ошибка: некорректный ID услуги", show_alert=True)
        return
    
    service_id = int(parts[2])
    
    # �������� ������ �� ���������
    data = await state.get_data()
    booking_data = data.get('booking_data', {})
    selected_date = booking_data.get('date')
    
    if not selected_date:
        await callback.answer(build_pick_date_first_text(html=True), show_alert=True)
        return
    
    await _show_time_selection_for_date(
        callback,
        state,
        service_id=service_id,
        selected_date=selected_date,
        page=0,
    )

async def date_prev_week(callback: CallbackQuery, state: FSMContext):
    """Переключение на предыдущую неделю."""
    parts = callback.data.split("_")
    service_id = int(parts[3])
    week_offset = int(parts[4])
    
    await callback.message.edit_text(
        build_date_selection_text(html=True),
        reply_markup=get_date_selection_keyboard(service_id, week_offset),
        parse_mode="HTML"
    )

async def date_next_week(callback: CallbackQuery, state: FSMContext):
    """Переключение на следующую неделю."""
    parts = callback.data.split("_")
    service_id = int(parts[3])
    week_offset = int(parts[4])
    
    await callback.message.edit_text(
        build_date_selection_text(html=True),
        reply_markup=get_date_selection_keyboard(service_id, week_offset),
        parse_mode="HTML"
    )

async def confirm_date_selection(callback: CallbackQuery, state: FSMContext):
    """Подтверждение выбранной даты."""
    parts = callback.data.split("_")
    service_id = int(parts[2])
    selected_date = parts[3]  # YYYY-MM-DD format

    await _show_time_selection_for_date(
        callback,
        state,
        service_id=service_id,
        selected_date=selected_date,
        page=0,
    )

async def time_page(callback: CallbackQuery, state: FSMContext):
    """Переключение страниц со слотами времени."""
    parts = callback.data.split("_")
    service_id = int(parts[2])
    selected_date = parts[3]
    page = int(parts[4])

    await _show_time_selection_for_date(
        callback,
        state,
        service_id=service_id,
        selected_date=selected_date,
        page=page,
    )

async def time_prev_date(callback: CallbackQuery, state: FSMContext):
    """Сдвиг выбора времени на предыдущую дату."""
    parts = callback.data.split("_")
    service_id = int(parts[3])
    prev_date = parts[4]  # YYYY-MM-DD format
    
    await _show_time_selection_for_date(
        callback,
        state,
        service_id=service_id,
        selected_date=prev_date,
        page=0,
    )

async def time_next_date(callback: CallbackQuery, state: FSMContext):
    """Сдвиг выбора времени на следующую дату."""
    parts = callback.data.split("_")
    service_id = int(parts[3])
    next_date = parts[4]  # YYYY-MM-DD format
    
    await _show_time_selection_for_date(
        callback,
        state,
        service_id=service_id,
        selected_date=next_date,
        page=0,
    )

async def confirm_time_selection(callback: CallbackQuery, state: FSMContext):
    """Подтверждение выбранного времени."""
    parts = callback.data.split("_")
    service_id = int(parts[2])
    time_index = int(parts[3])
    
    # �������� ������ �� ���������
    data = await state.get_data()
    booking_data = data.get('booking_data', {})
    time_slots = data.get('time_slots', [])
    
    # �������� ��������� ����� �� ��������� ������
    is_all_day = bool(booking_data.get('is_all_day'))
    if time_index < len(time_slots):
        selected_slot = time_slots[time_index]
        selected_time = f"{selected_slot['start_time'].strftime('%H:%M')} - {selected_slot['end_time'].strftime('%H:%M')}"
    else:
        duration_minutes = booking_data.get('duration') or _get_min_duration_from_state(data)
        end_fallback = (datetime.strptime("09:00", "%H:%M") + timedelta(minutes=duration_minutes)).strftime("%H:%M")
        selected_time = f"09:00 - {end_fallback}"
    
    # ��������� ��������� ����� � ���������
    data = await state.get_data()
    booking_data = data.get('booking_data', {})
    booking_data['time'] = selected_time
    if is_all_day and booking_data.get('date'):
        try:
            selected_date = datetime.strptime(booking_data['date'], "%Y-%m-%d").date()
            start_str = selected_time.split(" - ")[0].strip()
            start_dt = datetime.combine(selected_date, datetime.strptime(start_str, "%H:%M").time())
            end_dt = datetime.combine(selected_date, datetime.strptime("21:00", "%H:%M").time())
            duration_minutes = int((end_dt - start_dt).total_seconds() // 60)
            booking_data['duration'] = duration_minutes
            booking_data['time'] = f"{start_dt.strftime('%H:%M')} - {end_dt.strftime('%H:%M')}"
        except Exception as e:
            print(f"Ошибка пересчета режима 'весь день': {e}")
    if 'service_name' not in booking_data:
        booking_data['service_name'] = data.get('service_name', '')
    await state.update_data(booking_data=booking_data)
    
    await show_booking_form(callback, state)

async def back_from_date_selection(callback: CallbackQuery, state: FSMContext):
    """Возврат из выбора даты к форме бронирования."""
    await show_booking_form(callback, state)

async def back_from_time_selection(callback: CallbackQuery, state: FSMContext):
    """Возврат из выбора времени к форме бронирования."""
    await show_booking_form(callback, state)


async def show_booking_other_menu(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    booking_data = data.get("booking_data", {})
    service_name = booking_data.get("service_name") or data.get("service_name", "")
    await callback.message.edit_text(
        _build_booking_other_menu_text(service_name, booking_data),
        reply_markup=get_booking_other_keyboard(int(data["service_id"]), booking_data),
        parse_mode="HTML",
    )


async def back_from_other_selection(callback: CallbackQuery, state: FSMContext):
    await show_booking_form(callback, state)

async def start_name_input(callback: CallbackQuery, state: FSMContext):
    """Запрос имени клиента."""
    await state.set_state(BookingStates.entering_name)
    await callback.message.edit_text(
        build_name_prompt(html=True),
        parse_mode="HTML"
    )

async def process_name_input(message: Message, state: FSMContext):
    """Обработка введённого имени."""
    name, error_code = validate_person_name(message.text or "")

    if error_code == "too_short":
        await message.answer(
            build_name_validation_error(field_label="Имя", html=True),
            parse_mode="HTML"
        )
        return

    if error_code == "invalid_chars":
        await message.answer(
            "⚠️ <b>Имя содержит недопустимые символы</b>\n\n"
            "Имя должно содержать только буквы, пробелы и дефисы.\n"
            "Пример: Анна, Анна-Мария, Мария Анна",
            parse_mode="HTML"
        )
        return
    
    data = await state.get_data()
    await _update_booking_data_and_show_form(message, state, name=name)

async def start_last_name_input(callback: CallbackQuery, state: FSMContext):
    """Запрос фамилии клиента."""
    parts = callback.data.split("_")
    service_id = int(parts[3]) if len(parts) > 3 else int(parts[2])

    await state.set_state(BookingStates.entering_last_name)
    await callback.message.edit_text(
        build_last_name_prompt(html=True),
        parse_mode="HTML",
        reply_markup=_get_back_to_booking_form_keyboard(service_id),
    )

async def process_last_name_input(message: Message, state: FSMContext):
    """Обработка введённой фамилии."""
    last_name, error_code = validate_person_name(message.text or "")
    data = await state.get_data()
    service_id = data.get("service_id")
    back_keyboard = _get_back_to_booking_form_keyboard(service_id) if service_id else None

    if error_code == "too_short":
        await message.answer(
            build_name_validation_error(field_label="Фамилия", html=True),
            parse_mode="HTML",
            reply_markup=back_keyboard,
        )
        return

    if error_code == "invalid_chars":
        await message.answer(
            "⚠️ <b>Фамилия содержит недопустимые символы</b>\n\n"
            "Фамилия должна содержать только буквы, пробелы и дефисы.\n"
            "Пример: Иванова, Петрова-Сидорова",
            parse_mode="HTML",
            reply_markup=back_keyboard,
        )
        return

    await _update_booking_data_and_show_form(message, state, last_name=last_name)

async def start_phone_input(callback: CallbackQuery, state: FSMContext):
    """Запрос номера телефона."""
    await state.set_state(BookingStates.entering_phone)
    await callback.message.edit_text(
        build_phone_prompt(html=True),
        parse_mode="HTML"
    )

async def process_phone_input(message: Message, state: FSMContext):
    """Обработка введённого телефона."""
    formatted_phone = normalize_and_format_phone(message.text or "")

    if not formatted_phone:
        await message.answer(
            build_phone_validation_error(html=True),
            parse_mode="HTML"
        )
        return
    
    await _update_booking_data_and_show_form(message, state, phone=formatted_phone)

async def start_discount_code_input(callback: CallbackQuery, state: FSMContext):
    """Запрос кода для скидки."""
    parts = callback.data.split("_")
    service_id = int(parts[2])
    await state.set_state(BookingStates.entering_discount_code)
    await callback.message.edit_text(
        build_discount_code_prompt(html=True, back_label="Назад"),
        parse_mode="HTML"
        ,
        reply_markup=_get_back_to_booking_form_keyboard(service_id),
    )


async def process_discount_code_input(message: Message, state: FSMContext):
    """Обработка скидочного кода."""
    discount_code, error_code = validate_discount_code(message.text or "")
    if error_code == "too_long":
        await message.answer(
            build_discount_code_validation_error(max_length=100, html=True),
            parse_mode="HTML"
        )
        return

    await _update_booking_data_and_show_form(message, state, discount_code=discount_code)


async def start_comment_input(callback: CallbackQuery, state: FSMContext):
    """Запрос комментария к бронированию."""
    parts = callback.data.split("_")
    service_id = int(parts[2])
    await state.set_state(BookingStates.entering_comment)
    await callback.message.edit_text(
        build_comment_prompt(html=True, back_label="Назад"),
        parse_mode="HTML"
        ,
        reply_markup=_get_back_to_booking_form_keyboard(service_id),
    )


async def process_comment_input(message: Message, state: FSMContext):
    """Обработка комментария к бронированию."""
    comment, error_code = validate_comment(message.text or "")
    if error_code == "too_long":
        await message.answer(
            build_comment_validation_error(max_length=500, html=True),
            parse_mode="HTML"
        )
        return

    await _update_booking_data_and_show_form(message, state, comment=comment)

async def start_guests_count_input(callback: CallbackQuery, state: FSMContext):
    """Запрос количества гостей."""
    data = await state.get_data()
    max_guests = _get_max_guests_from_state(data)
    await state.set_state(BookingStates.entering_guests_count)
    await callback.message.edit_text(
        build_guests_count_prompt(max_guests=max_guests, html=True),
        parse_mode="HTML"
    )

async def process_guests_count_input(message: Message, state: FSMContext):
    """Обработка количества гостей."""
    guests_count, error_code = parse_positive_int(message.text or "")

    if error_code == "not_integer":
        await message.answer(
            "⚠️ <b>Введите число</b>\n\n"
            "Пожалуйста, укажите количество гостей цифрами.\n"
            "Пример: 2, 4, 6",
            parse_mode="HTML"
        )
        return

    if error_code == "not_positive":
        await message.answer(
            "⚠️ <b>Количество гостей должно быть больше 0</b>\n\n"
            "Пожалуйста, введите корректное количество гостей.\n"
            "Пример: 1, 2, 4",
            parse_mode="HTML"
        )
        return
    
    data = await state.get_data()
    service_id = data.get('service_id')
    max_guests = _get_max_guests_from_state(data)
    if service_id:
        service = await service_repo.get_by_id(service_id)
        if service:
            max_guests = _normalize_max_guests(service.max_num_clients)
            await state.update_data(max_num_clients=max_guests)

    if validate_guests_count(int(guests_count), max_guests=max_guests) == "too_many":
        await message.answer(
            build_guests_validation_error(max_guests=max_guests, html=True),
            parse_mode="HTML"
        )
        return
    
    await _update_booking_data_and_show_form(message, state, guests_count=guests_count)

async def start_duration_input(callback: CallbackQuery, state: FSMContext):
    """Выбор продолжительности бронирования."""
    parts = callback.data.split("_")
    service_id = int(parts[2])

    from app.integrations.local.db import service_repo

    service = await service_repo.get_by_id(service_id)
    
    if service:
        min_duration = _normalize_min_duration_minutes(service.min_duration_minutes)
        await state.update_data(min_duration_minutes=min_duration)
    else:
        min_duration = _get_min_duration_from_state(await state.get_data())
    
    await state.set_state(BookingStates.filling_form)
    await callback.message.edit_text(
        build_duration_prompt(min_duration=min_duration, html=True, detailed=True),
        reply_markup=get_duration_selection_keyboard(service_id, min_duration),
        parse_mode="HTML"
    )

async def select_duration_option(callback: CallbackQuery, state: FSMContext):
    """Выбор продолжительности через inline-кнопки."""
    parts = callback.data.split("_")
    if len(parts) < 5:
        await callback.answer("Ошибка в данных", show_alert=True)
        return

    try:
        duration = int(parts[4])
    except ValueError:
        await callback.answer("Некорректная длительность", show_alert=True)
        return
    is_all_day = duration == 720

    data = await state.get_data()
    service_id = data.get('service_id')
    if not service_id:
        await callback.answer("Ошибка: ID услуги не найден", show_alert=True)
        return

    if validate_duration_minutes(duration, min_duration=1) == "too_large":
        await callback.answer("Максимум: весь день", show_alert=True)
        return

    if validate_duration_minutes(duration, min_duration=1) == "invalid_step":
        await callback.answer("Длительность должна быть кратна 60 минутам", show_alert=True)
        return

    service = await service_repo.get_by_id(service_id)
    min_duration = _get_min_duration_from_state(data)
    if service:
        min_duration = _normalize_min_duration_minutes(service.min_duration_minutes)
        await state.update_data(min_duration_minutes=min_duration)
    if validate_duration_minutes(duration, min_duration=min_duration) == "too_small":
        await callback.answer(
            f"Минимальная продолжительность: {min_duration} мин.",
            show_alert=True
        )
        return

    booking_data = data.get('booking_data', {})
    if booking_data.get('date') and booking_data.get('time'):
        try:
            selected_date = datetime.strptime(booking_data['date'], "%Y-%m-%d").date()
            start_time_str = booking_data['time'].split(' - ')[0]
            start_time = datetime.strptime(start_time_str, "%H:%M").time()
            start_dt = datetime.combine(selected_date, start_time)
            service_name = booking_data.get('service_name') or data.get('service_name', '')
            duration_for_check = duration
            if is_all_day:
                end_all_day = datetime.combine(selected_date, datetime.strptime("21:00", "%H:%M").time())
                duration_for_check = int((end_all_day - start_dt).total_seconds() // 60)
                if duration_for_check < min_duration:
                    await callback.answer(
                        "Для режима 'весь день' время начала слишком позднее.",
                        show_alert=True
                    )
                    return
            ok, reason = await _is_booking_available(
                selected_date,
                start_dt,
                duration_for_check,
                service_id,
                service_name,
            )
            if not ok:
                await callback.answer(
                    "Выбранная длительность недоступна для этого времени.",
                    show_alert=True
                )
                return
        except Exception as e:
            print(f"Ошибка проверки доступности длительности: {e}")

    booking_data['is_all_day'] = is_all_day
    if is_all_day and booking_data.get('date') and booking_data.get('time'):
        selected_date = datetime.strptime(booking_data['date'], "%Y-%m-%d").date()
        start_time_str = booking_data['time'].split(' - ')[0]
        start_time = datetime.strptime(start_time_str, "%H:%M").time()
        start_dt = datetime.combine(selected_date, start_time)
        end_all_day = datetime.combine(selected_date, datetime.strptime("21:00", "%H:%M").time())
        duration = int((end_all_day - start_dt).total_seconds() // 60)
        booking_data['duration'] = duration
        booking_data['time'] = f"{start_dt.strftime('%H:%M')} - {end_all_day.strftime('%H:%M')}"
    else:
        booking_data['duration'] = duration
    if 'service_name' not in booking_data:
        booking_data['service_name'] = data.get('service_name', '')
    await state.update_data(booking_data=booking_data)
    await state.set_state(BookingStates.filling_form)
    await show_booking_form(callback, state)

async def process_duration_input(message: Message, state: FSMContext):
    """Обработка продолжительности, введенной текстом."""
    duration, error_code = parse_positive_int(message.text or "")

    if error_code == "not_integer":
        await message.answer(
            "⚠️ <b>Введите число</b>\n\n"
            "Пожалуйста, укажите продолжительность в минутах.\n"
            "Пример: 60, 120, 180",
            parse_mode="HTML"
        )
        return

    if error_code == "not_positive":
        await message.answer(
            "⚠️ <b>Введите число</b>\n\n"
            "Пожалуйста, укажите продолжительность в минутах.\n"
            "Пример: 60, 120, 180",
            parse_mode="HTML"
        )
        return

    if validate_duration_minutes(int(duration), min_duration=1) == "too_large":
        await message.answer(
            build_duration_too_large_error(html=True),
            parse_mode="HTML"
        )
        return

    if validate_duration_minutes(int(duration), min_duration=1) == "invalid_step":
        await message.answer(
            build_duration_invalid_step_error(html=True),
            parse_mode="HTML"
        )
        return

    data = await state.get_data()
    service_id = data.get('service_id')

    if service_id:
        service = await service_repo.get_by_id(service_id)
        min_duration = _get_min_duration_from_state(data)
        if service:
            min_duration = _normalize_min_duration_minutes(service.min_duration_minutes)
            await state.update_data(min_duration_minutes=min_duration)
        if validate_duration_minutes(int(duration), min_duration=min_duration) == "too_small":
            await message.answer(
                build_duration_too_small_error(min_duration=min_duration, html=True),
                parse_mode="HTML"
            )
            return

    booking_data = data.get('booking_data', {})
    if booking_data.get('date') and booking_data.get('time'):
        try:
            selected_date = datetime.strptime(booking_data['date'], "%Y-%m-%d").date()
            start_time_str = booking_data['time'].split(' - ')[0]
            start_time = datetime.strptime(start_time_str, "%H:%M").time()
            start_dt = datetime.combine(selected_date, start_time)
            service_name = booking_data.get('service_name') or data.get('service_name', '')
            ok, reason = await _is_booking_available(
                selected_date,
                start_dt,
                duration,
                service_id or 0,
                service_name,
            )
            if not ok:
                await message.answer(
                    "⚠️ <b>Выбранная длительность недоступна</b>\n\n"
                    f"{reason}\n"
                    "Пожалуйста, выберите другую длительность или время.",
                    reply_markup=get_booking_form_keyboard(service_id, booking_data),
                    parse_mode="HTML"
                )
                return
        except Exception as e:
            print(f"Ошибка проверки длительности: {e}")

    booking_data['duration'] = duration
    booking_data['is_all_day'] = False
    if 'service_name' not in booking_data:
        booking_data['service_name'] = data.get('service_name', '')
    await state.update_data(booking_data=booking_data)

    await state.set_state(BookingStates.filling_form)

    if service_id:
        data = await state.get_data()
        booking_data = data.get('booking_data', {})
        service_name = booking_data.get('service_name') or data.get('service_name', '')
        text = _build_booking_form_text(service_name, booking_data, data)

        await message.answer(
            text,
            reply_markup=get_booking_form_keyboard(service_id, booking_data),
            parse_mode="HTML"
        )
async def start_email_input(callback: CallbackQuery, state: FSMContext):
    """Запрос e-mail."""
    await state.set_state(BookingStates.entering_email)
    await callback.message.edit_text(
        build_email_prompt(html=True, skip_label="/skip"),
        parse_mode="HTML"
    )

async def process_email_input(message: Message, state: FSMContext):
    """Обработка e-mail."""
    email, error_code = validate_optional_email(
        message.text or "",
        skip_tokens={"/skip", "skip"},
    )
    if error_code == "invalid":
        await message.answer(
            build_email_validation_error(html=True, skip_label="/skip"),
            parse_mode="HTML"
        )
        return
    
    await _update_booking_data_and_show_form(message, state, email=email)

async def start_extras_input(callback: CallbackQuery, state: FSMContext):
    """Выбор дополнительных услуг."""
    parts = callback.data.split("_")
    data = await state.get_data()
    
    if len(parts) >= 3 and parts[2].isdigit():
        service_id = int(parts[2])
    elif callback.data.startswith("booking_toggle_extra_"):
        service_id = int(parts[3])
    else:
        service_id = data.get('service_id')
        if not service_id:
            await callback.answer("Ошибка: ID услуги не найден", show_alert=True)
            return
    
    booking_data = data.get('booking_data', {})
    current_extras = [
        int(extra_id)
        for extra_id in booking_data.get("extras", [])
        if isinstance(extra_id, int) or (isinstance(extra_id, str) and extra_id.isdigit())
    ]
    available_extras = await extra_service_repo.get_all_active()
    extra_labels = build_extra_service_label_map(available_extras)
    booking_data["extra_labels"] = extra_labels
    await state.update_data(booking_data=booking_data)

    text = build_choose_extras_text(html=True)

    if not available_extras:
        text += "\n\nСейчас нет доступных доп. услуг."
        await state.set_state(BookingStates.selecting_extras)
        await callback.message.edit_text(
            text,
            reply_markup=InlineKeyboardMarkup(
                inline_keyboard=[[
                    InlineKeyboardButton(text="🔙 Назад", callback_data=f"booking_extras_back_{service_id}")
                ]]
            ),
            parse_mode="HTML",
        )
        return

    for extra_service in available_extras:
        label = build_extra_service_booking_label(extra_service)
        status = "✅" if extra_service.id in current_extras else "▫️"
        text += f"{status} {label}\n"

    text += "\nНажмите на кнопку ниже, чтобы добавить или убрать услугу."

    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

    keyboard = []
    for extra_service in available_extras:
        is_selected = extra_service.id in current_extras
        button_text = f"{'✅' if is_selected else '➕'} {extra_service.name}"
        action = "remove" if is_selected else "add"
        keyboard.append([
            InlineKeyboardButton(
                text=button_text,
                callback_data=f"booking_toggle_extra_{service_id}_{extra_service.id}_{action}"
            )
        ])

    keyboard.append([
        InlineKeyboardButton(
            text="✅ Готово",
            callback_data=f"booking_extras_done_{service_id}"
        )
    ])
    keyboard.append([
        InlineKeyboardButton(
            text="🔙 Назад",
            callback_data=f"booking_extras_back_{service_id}"
        )
    ])
    
    await state.set_state(BookingStates.selecting_extras)
    await callback.message.edit_text(
        text,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard),
        parse_mode="HTML"
    )

async def toggle_extra_service(callback: CallbackQuery, state: FSMContext):
    """������������ �������������� ������"""
    parts = callback.data.split("_")
    service_id = int(parts[3])
    extra_id = int(parts[4])
    action = parts[5]  # "add" or "remove"
    
    data = await state.get_data()
    booking_data = data.get('booking_data', {})
    extras = [
        int(item)
        for item in booking_data.get("extras", [])
        if isinstance(item, int) or (isinstance(item, str) and item.isdigit())
    ]
    
    if action == "add" and extra_id not in extras:
        extras.append(extra_id)
    elif action == "remove" and extra_id in extras:
        extras.remove(extra_id)
    
    booking_data['extras'] = extras
    # ��������� service_name ���� ��� ��� ��� � booking_data
    if 'service_name' not in booking_data:
        booking_data['service_name'] = data.get('service_name', '')
    await state.update_data(booking_data=booking_data)
    
    # ��������� ���������
    await start_extras_input(callback, state)

async def extras_done(callback: CallbackQuery, state: FSMContext):
    """���������� ������ �������������� �����"""
    parts = callback.data.split("_")
    service_id = int(parts[3])
    
    # ������������ � ����� ������������
    await state.set_state(BookingStates.filling_form)
    await show_booking_form(callback, state)

async def back_from_extras(callback: CallbackQuery, state: FSMContext):
    """������� �� ������ �������������� �����"""
    parts = callback.data.split("_")
    service_id = int(parts[3])  # booking_extras_back_{service_id}
    
    # ������������ � ����� ������������
    await state.set_state(BookingStates.filling_form)
    await show_booking_form(callback, state)

async def confirm_booking(callback: CallbackQuery, state: FSMContext):
    """Подтверждение бронирования."""
    parts = callback.data.split("_")
    service_id = int(parts[2])
    telegram_id = callback.from_user.id
    
    data = await state.get_data()
    booking_data = data.get('booking_data', {})
    service_name = booking_data.get('service_name') or data.get('service_name', '')

    missing_names = get_missing_booking_field_labels(booking_data)

    service = await service_repo.get_by_id(service_id)
    if service and booking_data.get('guests_count'):
        max_guests = _normalize_max_guests(service.max_num_clients)
        if int(booking_data['guests_count']) > max_guests:
            await callback.answer(
                f"Максимальная вместимость этой услуги: {max_guests} чел.",
                show_alert=True
            )
            return
    
    if missing_names:
        await callback.answer("Не все поля заполнены", show_alert=True)
        await callback.message.answer(
            f"⚠️ <b>Не все поля заполнены</b>\n\n"
            f"Заполните: {', '.join(missing_names)}",
            parse_mode="HTML"
        )
        return
    
    selected_date = datetime.strptime(booking_data['date'], "%Y-%m-%d").date()
    selected_time_str = booking_data['time'].split(' - ')[0]
    selected_time = datetime.strptime(selected_time_str, "%H:%M").time()
    selected_datetime = datetime.combine(selected_date, selected_time)
    duration_minutes = booking_data.get('duration') or _get_min_duration_from_state(data)
    end_datetime = selected_datetime + timedelta(minutes=duration_minutes)
    time_range_display = f"{selected_datetime.strftime('%H:%M')} - {end_datetime.strftime('%H:%M')}"
    
    if CALENDAR_AVAILABLE and GoogleCalendarService:
        try:
            calendar_service = GoogleCalendarService()
            
            ok, reason = await _is_booking_available(
                selected_date,
                selected_datetime,
                duration_minutes,
                service_id,
                service_name,
            )
            if not ok:
                await callback.answer(
                    "⚠️ <b>Это время уже недоступно</b>\n\n"
                    f"{reason}\n"
                    "Пожалуйста, выберите другое время для бронирования.",
                    show_alert=True
                )
                return
        except Exception as e:
            print(f"Ошибка проверки доступности времени: {e}")
            await callback.answer(
                "Не удалось проверить доступность времени. Продолжаем бронирование."
            )
    
    event_start = selected_datetime
    event_end = event_start + timedelta(minutes=duration_minutes)
    username = callback.from_user.username
    telegram_link = f"https://t.me/{username}" if username else "не указан"
    preview_summary = build_booking_summary(
        booking_data=booking_data,
        service_name=service_name,
        service_id=service_id,
        date_display=selected_date.strftime('%d.%m.%Y'),
        time_range=time_range_display,
        duration_minutes=duration_minutes,
    )

    if CALENDAR_AVAILABLE and GoogleCalendarService:
        print(f"[CALENDAR] Попытка создания события в календаре для {_format_full_name(booking_data)}")
        print(f"[CALENDAR] Создание события: {event_start} - {event_end}")
        print("[CALENDAR] Вызов calendar_service.create_event...")
    else:
        print(f"[WARNING] Календарь недоступен. CALENDAR_AVAILABLE={CALENDAR_AVAILABLE}, GoogleCalendarService={GoogleCalendarService}")

    async def _sync_client() -> None:
        from app.integrations.local.db import client_repo
        await sync_telegram_booking_client(
            client_repo=client_repo,
            telegram_id=telegram_id,
            booking_data=booking_data,
        )

    phone_display = booking_data['phone']
    phone_html = f"<code>{phone_display}</code>"

    try:
        use_case_result = await create_booking_use_case(
            booking_data=booking_data,
            service_name=service_name,
            service_id=service_id,
            date_display=selected_date.strftime('%d.%m.%Y'),
            time_range=time_range_display,
            duration_minutes=duration_minutes,
            event_start=event_start,
            event_end=event_end,
            calendar_available=CALENDAR_AVAILABLE,
            calendar_service_cls=GoogleCalendarService,
            calendar_description=build_telegram_calendar_description(preview_summary, telegram_link=telegram_link),
            sync_client=_sync_client,
            admin_notification_builder=lambda summary: build_telegram_booking_admin_notification(
                summary=summary,
                phone_html=phone_html,
                telegram_id=telegram_id,
                username=username,
            ),
        )
        summary = use_case_result.summary
        calendar_result = use_case_result.finalize_result.calendar_result
        notification = use_case_result.admin_notification
        vk_notification = build_telegram_booking_admin_notification_for_vk(
            summary=summary,
            telegram_id=telegram_id,
            username=username,
        )
        if calendar_result.created:
            print(f"[CALENDAR] Событие успешно создано в календаре: {calendar_result.payload.get('htmlLink', 'N/A')}")
        elif calendar_result.error:
            print(f"[ERROR] Ошибка создания события в календаре: {calendar_result.error}")
            print(f"[ERROR] Тип ошибки: {type(calendar_result.error).__name__ if calendar_result.error else 'unknown'}")
    except Exception as e:
        print(f"Ошибка финализации бронирования: {e}")
        summary = preview_summary
        notification = build_telegram_booking_admin_notification(
            summary=summary,
            phone_html=phone_html,
            telegram_id=telegram_id,
            username=username,
        )
        vk_notification = build_telegram_booking_admin_notification_for_vk(
            summary=summary,
            telegram_id=telegram_id,
            username=username,
        )

    try:
        await send_telegram_admin_notification(
            notification=notification,
            bot=callback.bot,
        )
    except Exception as e:
        print(f"Ошибка админского уведомления: {e}")

    try:
        await send_vk_admin_notification(notification=vk_notification)
    except Exception as e:
        print(f"Ошибка VK-уведомления администраторам: {e}")

    await callback.message.edit_text(
        build_telegram_confirmation_text(summary),
        reply_markup=get_main_menu_keyboard(),
        parse_mode="HTML"
    )

    await state.clear()
async def cancel_booking(callback: CallbackQuery, state: FSMContext):
    """Отмена бронирования."""
    await state.clear()
    await callback.message.edit_text(
        "❌ <b>Бронирование отменено</b>\n\n"
        "Вы можете начать заново в любой момент.",
        reply_markup=get_main_menu_keyboard(),
        parse_mode="HTML"
    )

def register_booking_handlers(dp: Dispatcher):
    """Регистрация обработчиков бронирования."""
    dp.callback_query.register(start_booking, F.data.startswith("book_service_"))
    dp.callback_query.register(select_date, F.data.startswith("booking_date_"))
    dp.callback_query.register(select_time, F.data.startswith("booking_time_"))
    dp.callback_query.register(date_prev_week, F.data.startswith("date_prev_week_"))
    dp.callback_query.register(date_next_week, F.data.startswith("date_next_week_"))
    dp.callback_query.register(confirm_date_selection, F.data.startswith("select_date_"))
    dp.callback_query.register(time_page, F.data.startswith("time_page_"))
    dp.callback_query.register(time_prev_date, F.data.startswith("time_prev_date_"))
    dp.callback_query.register(time_next_date, F.data.startswith("time_next_date_"))
    dp.callback_query.register(confirm_time_selection, F.data.startswith("select_time_"))
    dp.callback_query.register(back_from_date_selection, F.data.startswith("booking_back_from_date_"))
    dp.callback_query.register(back_from_time_selection, F.data.startswith("booking_back_from_time_"))
    dp.callback_query.register(show_booking_other_menu, F.data.startswith("booking_other_"))
    dp.callback_query.register(back_from_other_selection, F.data.startswith("booking_back_from_other_"))
    dp.callback_query.register(start_name_input, F.data.startswith("booking_name_"))
    dp.message.register(process_name_input, BookingStates.entering_name)
    dp.callback_query.register(start_last_name_input, F.data.startswith("booking_last_name_"))
    dp.message.register(process_last_name_input, BookingStates.entering_last_name)
    dp.callback_query.register(start_phone_input, F.data.startswith("booking_phone_"))
    dp.message.register(process_phone_input, BookingStates.entering_phone)
    dp.callback_query.register(start_discount_code_input, F.data.startswith("booking_discount_"))
    dp.message.register(process_discount_code_input, BookingStates.entering_discount_code)
    dp.callback_query.register(start_comment_input, F.data.startswith("booking_comment_"))
    dp.message.register(process_comment_input, BookingStates.entering_comment)
    dp.callback_query.register(start_guests_count_input, F.data.startswith("booking_guests_"))
    dp.message.register(process_guests_count_input, BookingStates.entering_guests_count)
    dp.callback_query.register(start_duration_input, F.data.startswith("booking_duration_"))
    dp.callback_query.register(select_duration_option, F.data.startswith("booking_set_duration_"))
    dp.message.register(process_duration_input, BookingStates.entering_duration)
    dp.callback_query.register(start_email_input, F.data.startswith("booking_email_"))
    dp.message.register(process_email_input, BookingStates.entering_email)
    # Обработчики extras должны регистрироваться раньше общего booking_extras_.
    dp.callback_query.register(toggle_extra_service, F.data.startswith("booking_toggle_extra_"))
    dp.callback_query.register(extras_done, F.data.startswith("booking_extras_done_"))
    dp.callback_query.register(back_from_extras, F.data.startswith("booking_extras_back_"))
    dp.callback_query.register(start_extras_input, F.data.startswith("booking_extras_"))
    dp.callback_query.register(confirm_booking, F.data.startswith("booking_confirm_"))
    dp.callback_query.register(cancel_booking, F.data.startswith("booking_cancel_"))

