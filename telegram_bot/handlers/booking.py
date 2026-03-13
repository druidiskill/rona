from aiogram import Dispatcher, F
from aiogram.types import CallbackQuery, Message, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from datetime import datetime, timedelta, date

from telegram_bot.keyboards import (
    get_booking_form_keyboard,
    get_main_menu_keyboard,
    get_date_selection_keyboard,
    get_time_selection_keyboard,
    get_duration_selection_keyboard,
)
from telegram_bot.states import BookingStates
from telegram_bot.services.booking_calendar import (
    build_default_time_slots as svc_build_default_time_slots,
    get_time_slots_for_date as svc_get_time_slots_for_date,
    is_booking_available as svc_is_booking_available,
)
from telegram_bot.services.booking_formatters import (
    format_booking_date as svc_format_booking_date,
    format_booking_time_range as svc_format_booking_time_range,
    format_booking_guests as svc_format_booking_guests,
    format_extras_display as svc_format_extras_display,
)
from database import service_repo

# Опциональный импорт Google Calendar
try:
    from google_calendar.calendar_service import GoogleCalendarService
    CALENDAR_AVAILABLE = True
    print("[OK] Google Calendar импортирован успешно")
except ImportError as e:
    GoogleCalendarService = None
    CALENDAR_AVAILABLE = False
    print(f"[WARNING] Google Calendar недоступен: {e}")
    print("[INFO] Установите зависимости: pip install google-api-python-client google-auth-httplib2 google-auth-oauthlib")

def _normalize_min_duration_minutes(raw_value: int | None) -> int:
    min_duration = int(raw_value or 60)
    if min_duration < 60:
        min_duration = 60
    if min_duration % 60 != 0:
        min_duration = ((min_duration // 60) + 1) * 60
    return min_duration


def _get_min_duration_from_state(data: dict) -> int:
    return _normalize_min_duration_minutes(data.get("min_duration_minutes", 60))


def _normalize_max_guests(raw_value: int | None) -> int:
    max_guests = int(raw_value or 1)
    return max(1, max_guests)


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


def _format_extras_display(extras: list[str]) -> str:
    return svc_format_extras_display(extras)

def _format_full_name(booking_data: dict) -> str:
    first = (booking_data.get("name") or "").strip()
    last = (booking_data.get("last_name") or "").strip()
    full = " ".join(part for part in [first, last] if part)
    return full or "Не указано"


def _normalize_stored_phone(phone: str | None) -> str | None:
    if not phone:
        return None
    digits = "".join(ch for ch in str(phone) if ch.isdigit())
    if len(digits) == 11 and digits.startswith(("7", "8")):
        digits = digits[1:]
    return digits if len(digits) == 10 else None


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

    text = f"📝 <b>Бронирование услуги: {service_name}</b>\n\n"
    text += "📋 <b>Заполните данные для бронирования:</b>\n\n"
    text += f"‼️ <b>Дата:</b> {date_display}\n"
    text += f"‼️ <b>Время:</b> {time_display}\n"
    text += f"‼️ <b>Имя:</b> {booking_data.get('name') or 'Не указано'}\n"
    text += f"‼️ <b>Фамилия:</b> {booking_data.get('last_name') or 'Не указано'}\n"
    text += f"‼️ <b>Номер телефона:</b> {booking_data.get('phone') or 'Не указан'}\n"
    text += f"‼️ <b>Количество гостей:</b> {guests_display}\n"
    text += f"⏰ <b>Продолжительность:</b> {duration_minutes} мин.\n"
    text += f"➕ <b>Доп. услуги:</b> {_format_extras_display(booking_data.get('extras', []))}\n"
    text += f"📧 <b>E-mail:</b> {email_display}\n\n"
    text += "Выберите параметр для заполнения:"
    return text


async def start_booking(callback: CallbackQuery, state: FSMContext):
    """Начало бронирования."""
    service_id = int(callback.data.split("_")[2])
    service = await service_repo.get_by_id(service_id)
    
    if not service:
        await callback.answer("Услуга не найдена", show_alert=True)
        return
    min_duration = _normalize_min_duration_minutes(service.min_duration_minutes)
    max_guests = _normalize_max_guests(service.max_num_clients)
    
    from database import client_repo
    telegram_id = callback.from_user.id
    existing_client = await client_repo.get_by_telegram_id(telegram_id)

    normalized_phone = _normalize_stored_phone(existing_client.phone if existing_client else None)
    if existing_client and normalized_phone:
        phone_display = f"+7 {normalized_phone[:3]} {normalized_phone[3:6]} {normalized_phone[6:8]} {normalized_phone[8:10]}"
        
        await state.update_data(
            service_id=service_id,
            service_name=service.name,
            min_duration_minutes=min_duration,
            max_num_clients=max_guests,
            booking_data={
                'date': None,
                'time': None,
                'name': existing_client.name,
                'last_name': getattr(existing_client, "last_name", None),
                'phone': phone_display,
                'guests_count': None,
                'duration': min_duration,
                'is_all_day': False,
                'extras': [],
                'email': existing_client.email,
                'service_name': service.name  # ��������� �������� ������ � booking_data
            }
        )
    else:
        # ���� ������� ��� ��� � ���� ��� ��������, ��������� ������� ����������
        await state.update_data(
            service_id=service_id,
            service_name=service.name,
            min_duration_minutes=min_duration,
            max_num_clients=max_guests,
            booking_data={
                'date': None,
                'time': None,
                'name': None,
                'last_name': None,
                'phone': None,
                'guests_count': None,
                'duration': min_duration,
                'is_all_day': False,
                'extras': [],
                'email': None,
                'service_name': service.name  # ��������� �������� ������ � booking_data
            }
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

async def select_date(callback: CallbackQuery, state: FSMContext):
    """Выбор даты бронирования."""
    parts = callback.data.split("_")
    if len(parts) < 3:
        await callback.answer("Ошибка в данных", show_alert=True)
        return
    
    service_id = int(parts[2])
    
    await callback.message.edit_text(
        "📅 <b>Выберите дату:</b>\n\n"
        "Выберите подходящий день:",
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
        await callback.answer("Сначала выберите дату", show_alert=True)
        return
    
    try:
        selected_date_obj = datetime.strptime(selected_date, "%Y-%m-%d").date()
        service_name = booking_data.get('service_name') or data.get('service_name')
        duration_minutes = booking_data.get('duration') or _get_min_duration_from_state(data)
        is_all_day = bool(booking_data.get('is_all_day'))
        time_slots, used_calendar, calendar_error = await _get_time_slots_for_date(
            selected_date_obj, service_id, service_name, duration_minutes, all_day=is_all_day
        )

        if not time_slots and used_calendar:
            await callback.message.edit_text(
                f"⚠️ <b>На {selected_date_obj.strftime('%d.%m.%Y')} нет свободных слотов</b>\n\n"
                "Пожалуйста, выберите другую дату.",
                reply_markup=get_booking_form_keyboard(service_id, booking_data),
                parse_mode="HTML"
            )
            return

        if calendar_error:
            await callback.answer("Не удалось получить данные календаря. Показаны резервные слоты.")

        await state.update_data(time_slots=time_slots)
        duration_hint = "режим: весь день до 21:00" if is_all_day else f"минимум {int(_get_min_duration_from_state(data))} мин., выбрано: {duration_minutes} мин."
        await callback.message.edit_text(
            f"🕒 <b>Выберите время на {selected_date_obj.strftime('%d.%m.%Y')}</b>\n\n"
            f"Доступные слоты ({duration_hint}):",
            reply_markup=get_time_selection_keyboard(service_id, time_slots, selected_date),
            parse_mode="HTML"
        )
    except Exception as e:
        print(f"Ошибка выбора времени: {e}")
        await callback.message.edit_text(
            "⚠️ <b>Не удалось получить доступные слоты</b>\n\n"
            "Пожалуйста, попробуйте позже или выберите другую дату.",
            reply_markup=get_booking_form_keyboard(service_id, booking_data),
            parse_mode="HTML"
        )

async def date_prev_week(callback: CallbackQuery, state: FSMContext):
    """Переключение на предыдущую неделю."""
    parts = callback.data.split("_")
    service_id = int(parts[3])
    week_offset = int(parts[4])
    
    await callback.message.edit_text(
        "📅 <b>Выберите дату:</b>\n\n"
        "Выберите подходящий день:",
        reply_markup=get_date_selection_keyboard(service_id, week_offset),
        parse_mode="HTML"
    )

async def date_next_week(callback: CallbackQuery, state: FSMContext):
    """Переключение на следующую неделю."""
    parts = callback.data.split("_")
    service_id = int(parts[3])
    week_offset = int(parts[4])
    
    await callback.message.edit_text(
        "📅 <b>Выберите дату:</b>\n\n"
        "Выберите подходящий день:",
        reply_markup=get_date_selection_keyboard(service_id, week_offset),
        parse_mode="HTML"
    )

async def confirm_date_selection(callback: CallbackQuery, state: FSMContext):
    """Подтверждение выбранной даты."""
    parts = callback.data.split("_")
    service_id = int(parts[2])
    selected_date = parts[3]  # YYYY-MM-DD format
    
    data = await state.get_data()
    booking_data = data.get('booking_data', {})
    booking_data['date'] = selected_date
    if 'service_name' not in booking_data:
        booking_data['service_name'] = data.get('service_name', '')
    await state.update_data(booking_data=booking_data)
    
    await show_booking_form(callback, state)

async def time_prev_date(callback: CallbackQuery, state: FSMContext):
    """Сдвиг выбора времени на предыдущую дату."""
    parts = callback.data.split("_")
    service_id = int(parts[3])
    prev_date = parts[4]  # YYYY-MM-DD format
    
    # ��������� ��������� ���� � ���������
    data = await state.get_data()
    booking_data = data.get('booking_data', {})
    booking_data['date'] = prev_date
    # ��������� service_name ���� ��� ��� ��� � booking_data
    if 'service_name' not in booking_data:
        booking_data['service_name'] = data.get('service_name', '')
    await state.update_data(booking_data=booking_data)
    
    try:
        prev_date_obj = datetime.strptime(prev_date, "%Y-%m-%d").date()
        service_name = booking_data.get('service_name') or data.get('service_name')
        duration_minutes = booking_data.get('duration') or _get_min_duration_from_state(data)
        is_all_day = bool(booking_data.get('is_all_day'))
        time_slots, used_calendar, calendar_error = await _get_time_slots_for_date(
            prev_date_obj, service_id, service_name, duration_minutes, all_day=is_all_day
        )

        if not time_slots and used_calendar:
            await callback.message.edit_text(
                f"⚠️ <b>На {prev_date_obj.strftime('%d.%m.%Y')} нет свободных слотов</b>\n\n"
                "Пожалуйста, выберите другую дату.",
                reply_markup=get_booking_form_keyboard(service_id, booking_data),
                parse_mode="HTML"
            )
            return

        if calendar_error:
            await callback.answer("Не удалось получить данные календаря. Показаны резервные слоты.")

        await state.update_data(time_slots=time_slots)
        duration_hint = "режим: весь день до 21:00" if is_all_day else f"минимум {int(_get_min_duration_from_state(data))} мин., выбрано: {duration_minutes} мин."
        await callback.message.edit_text(
            f"🕒 <b>Выберите время на {prev_date_obj.strftime('%d.%m.%Y')}</b>\n\n"
            f"Доступные слоты ({duration_hint}):",
            reply_markup=get_time_selection_keyboard(service_id, time_slots, prev_date),
            parse_mode="HTML"
        )
    except Exception as e:
        print(f"Ошибка получения слотов для предыдущей даты: {e}")
        await callback.message.edit_text(
            "⚠️ <b>Не удалось получить доступные слоты</b>\n\n"
            "Пожалуйста, попробуйте позже или выберите другую дату.",
            reply_markup=get_booking_form_keyboard(service_id, booking_data),
            parse_mode="HTML"
        )

async def time_next_date(callback: CallbackQuery, state: FSMContext):
    """Сдвиг выбора времени на следующую дату."""
    parts = callback.data.split("_")
    service_id = int(parts[3])
    next_date = parts[4]  # YYYY-MM-DD format
    
    # ��������� ��������� ���� � ���������
    data = await state.get_data()
    booking_data = data.get('booking_data', {})
    booking_data['date'] = next_date
    # ��������� service_name ���� ��� ��� ��� � booking_data
    if 'service_name' not in booking_data:
        booking_data['service_name'] = data.get('service_name', '')
    await state.update_data(booking_data=booking_data)
    
    try:
        next_date_obj = datetime.strptime(next_date, "%Y-%m-%d").date()
        service_name = booking_data.get('service_name') or data.get('service_name')
        duration_minutes = booking_data.get('duration') or _get_min_duration_from_state(data)
        is_all_day = bool(booking_data.get('is_all_day'))
        time_slots, used_calendar, calendar_error = await _get_time_slots_for_date(
            next_date_obj, service_id, service_name, duration_minutes, all_day=is_all_day
        )

        if not time_slots and used_calendar:
            await callback.message.edit_text(
                f"⚠️ <b>На {next_date_obj.strftime('%d.%m.%Y')} нет свободных слотов</b>\n\n"
                "Пожалуйста, выберите другую дату.",
                reply_markup=get_booking_form_keyboard(service_id, booking_data),
                parse_mode="HTML"
            )
            return

        if calendar_error:
            await callback.answer("Не удалось получить данные календаря. Показаны резервные слоты.")

        await state.update_data(time_slots=time_slots)
        duration_hint = "режим: весь день до 21:00" if is_all_day else f"минимум {int(_get_min_duration_from_state(data))} мин., выбрано: {duration_minutes} мин."
        await callback.message.edit_text(
            f"🕒 <b>Выберите время на {next_date_obj.strftime('%d.%m.%Y')}</b>\n\n"
            f"Доступные слоты ({duration_hint}):",
            reply_markup=get_time_selection_keyboard(service_id, time_slots, next_date),
            parse_mode="HTML"
        )
    except Exception as e:
        print(f"Ошибка получения слотов для следующей даты: {e}")
        await callback.message.edit_text(
            "⚠️ <b>Не удалось получить доступные слоты</b>\n\n"
            "Пожалуйста, попробуйте позже или выберите другую дату.",
            reply_markup=get_booking_form_keyboard(service_id, booking_data),
            parse_mode="HTML"
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

async def start_name_input(callback: CallbackQuery, state: FSMContext):
    """Запрос имени клиента."""
    await state.set_state(BookingStates.entering_name)
    await callback.message.edit_text(
        "👤 <b>Введите ваше имя:</b>\n\n"
        "Имя должно содержать только буквы и быть длиннее 1 символа.\n"
        "Пример: Анна, Иван, Мария",
        parse_mode="HTML"
    )

async def process_name_input(message: Message, state: FSMContext):
    """Обработка введённого имени."""
    name = message.text.strip()
    
    if not name or len(name) < 2:
        await message.answer(
            "⚠️ <b>Имя указано некорректно</b>\n\n"
            "Пожалуйста, введите имя длиннее 1 символа.",
            parse_mode="HTML"
        )
        return
    
    if not name.replace(' ', '').replace('-', '').isalpha():
        await message.answer(
            "⚠️ <b>Имя содержит недопустимые символы</b>\n\n"
            "Имя должно содержать только буквы, пробелы и дефисы.\n"
            "Пример: Анна, Анна-Мария, Мария Анна",
            parse_mode="HTML"
        )
        return
    
    data = await state.get_data()
    booking_data = data.get('booking_data', {})
    booking_data['name'] = name
    if 'service_name' not in booking_data:
        booking_data['service_name'] = data.get('service_name', '')
    await state.update_data(booking_data=booking_data)
    
    await state.set_state(BookingStates.filling_form)
    
    service_id = data.get('service_id')
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

async def start_last_name_input(callback: CallbackQuery, state: FSMContext):
    """Запрос фамилии клиента."""
    parts = callback.data.split("_")
    service_id = int(parts[3]) if len(parts) > 3 else int(parts[2])

    await state.set_state(BookingStates.entering_last_name)
    await callback.message.edit_text(
        "🧾 <b>Введите вашу фамилию:</b>\n\n"
        "Фамилия должна содержать только буквы и быть длиннее 1 символа.\n"
        "Пример: Иванова, Петров, Соколова",
        parse_mode="HTML",
        reply_markup=_get_back_to_booking_form_keyboard(service_id),
    )

async def process_last_name_input(message: Message, state: FSMContext):
    """Обработка введённой фамилии."""
    last_name = (message.text or "").strip()
    data = await state.get_data()
    service_id = data.get("service_id")
    back_keyboard = _get_back_to_booking_form_keyboard(service_id) if service_id else None

    if not last_name or len(last_name) < 2:
        await message.answer(
            "⚠️ <b>Фамилия указана некорректно</b>\n\n"
            "Пожалуйста, введите фамилию длиннее 1 символа.",
            parse_mode="HTML",
            reply_markup=back_keyboard,
        )
        return

    if not last_name.replace(' ', '').replace('-', '').isalpha():
        await message.answer(
            "⚠️ <b>Фамилия содержит недопустимые символы</b>\n\n"
            "Фамилия должна содержать только буквы, пробелы и дефисы.\n"
            "Пример: Иванова, Петрова-Сидорова",
            parse_mode="HTML",
            reply_markup=back_keyboard,
        )
        return

    booking_data = data.get('booking_data', {})
    booking_data['last_name'] = last_name
    if 'service_name' not in booking_data:
        booking_data['service_name'] = data.get('service_name', '')
    await state.update_data(booking_data=booking_data)

    await state.set_state(BookingStates.filling_form)

    service_id = data.get('service_id')
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

async def start_phone_input(callback: CallbackQuery, state: FSMContext):
    """Запрос номера телефона."""
    await state.set_state(BookingStates.entering_phone)
    await callback.message.edit_text(
        "📱 <b>Введите номер телефона:</b>\n\n"
        "Номер можно указать в формате +7, 8 или просто 10 цифр.\n"
        "Пример: +7 900 123 45 67 или 8 900 123 45 67",
        parse_mode="HTML"
    )

async def process_phone_input(message: Message, state: FSMContext):
    """Обработка введённого телефона."""
    phone = message.text.strip()
    
    clean_phone = ''.join(c for c in phone if c.isdigit() or c == '+')
    
    if not phone or len(clean_phone) < 10:
        await message.answer(
            "⚠️ <b>Номер телефона указан некорректно</b>\n\n"
            "Пожалуйста, введите корректный номер телефона.\n"
            "Пример: +7 900 123 45 67",
            parse_mode="HTML"
        )
        return
    
    is_valid = False
    formatted_phone = ""
    
    if clean_phone.startswith('+7') and len(clean_phone) == 12:
        formatted_phone = f"+7 {clean_phone[2:5]} {clean_phone[5:8]} {clean_phone[8:10]} {clean_phone[10:12]}"
        is_valid = True
    elif clean_phone.startswith('8') and len(clean_phone) == 11:
        formatted_phone = f"+7 {clean_phone[1:4]} {clean_phone[4:7]} {clean_phone[7:9]} {clean_phone[9:11]}"
        is_valid = True
    elif clean_phone.startswith('7') and len(clean_phone) == 11:
        formatted_phone = f"+7 {clean_phone[1:4]} {clean_phone[4:7]} {clean_phone[7:9]} {clean_phone[9:11]}"
        is_valid = True
    elif len(clean_phone) == 10 and clean_phone.startswith('9'):
        formatted_phone = f"+7 {clean_phone[0:3]} {clean_phone[3:6]} {clean_phone[6:8]} {clean_phone[8:10]}"
        is_valid = True
    
    if not is_valid:
        await message.answer(
            "⚠️ <b>Неверный формат номера телефона</b>\n\n"
            "Пожалуйста, введите номер в одном из форматов:\n"
            "• +7 900 123 45 67\n"
            "• 8 900 123 45 67\n"
            "• 7 900 123 45 67\n"
            "• 900 123 45 67",
            parse_mode="HTML"
        )
        return
    
    data = await state.get_data()
    booking_data = data.get('booking_data', {})
    booking_data['phone'] = formatted_phone
    if 'service_name' not in booking_data:
        booking_data['service_name'] = data.get('service_name', '')
    await state.update_data(booking_data=booking_data)
    
    await state.set_state(BookingStates.filling_form)
    
    service_id = data.get('service_id')
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

async def start_guests_count_input(callback: CallbackQuery, state: FSMContext):
    """Запрос количества гостей."""
    data = await state.get_data()
    max_guests = _get_max_guests_from_state(data)
    await state.set_state(BookingStates.entering_guests_count)
    await callback.message.edit_text(
        "👥 <b>Введите количество гостей:</b>\n\n"
        "Укажите количество человек, которые будут присутствовать на съемке.\n"
        f"Максимум для этой услуги: {max_guests}.\n"
        "Пример: 2, 4, 6",
        parse_mode="HTML"
    )

async def process_guests_count_input(message: Message, state: FSMContext):
    """Обработка количества гостей."""
    guests_text = message.text.strip()
    
    try:
        guests_count = int(guests_text)
    except ValueError:
        await message.answer(
            "⚠️ <b>Введите число</b>\n\n"
            "Пожалуйста, укажите количество гостей цифрами.\n"
            "Пример: 2, 4, 6",
            parse_mode="HTML"
        )
        return
    
    if guests_count < 1:
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

    if guests_count > max_guests:
        await message.answer(
            "⚠️ <b>Слишком много гостей</b>\n\n"
            f"Максимальная вместимость этой услуги: {max_guests} чел.",
            parse_mode="HTML"
        )
        return
    
    data = await state.get_data()
    booking_data = data.get('booking_data', {})
    booking_data['guests_count'] = guests_count
    if 'service_name' not in booking_data:
        booking_data['service_name'] = data.get('service_name', '')
    await state.update_data(booking_data=booking_data)
    
    await state.set_state(BookingStates.filling_form)
    
    service_id = data.get('service_id')
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

async def start_duration_input(callback: CallbackQuery, state: FSMContext):
    """Выбор продолжительности бронирования."""
    parts = callback.data.split("_")
    service_id = int(parts[2])

    from database import service_repo
    service = await service_repo.get_by_id(service_id)
    
    if service:
        min_duration = _normalize_min_duration_minutes(service.min_duration_minutes)
        await state.update_data(min_duration_minutes=min_duration)
        duration_info = f"\n\nℹ️ <b>Важно:</b>\n• Минимальная продолжительность: {min_duration} мин.\n• Бронирование доступно шагом в 60 минут."
    else:
        min_duration = _get_min_duration_from_state(await state.get_data())
        duration_info = f"\n\nℹ️ <b>Важно:</b>\n• Минимальная продолжительность: {min_duration} мин.\n• Бронирование доступно шагом в 60 минут."
    
    await state.set_state(BookingStates.filling_form)
    await callback.message.edit_text(
        f"⏰ <b>Выберите продолжительность бронирования:</b>\n\n"
        f"Выберите подходящий вариант.{duration_info}",
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

    if duration > 720:
        await callback.answer("Максимум: весь день", show_alert=True)
        return

    if duration % 60 != 0:
        await callback.answer("Длительность должна быть кратна 60 минутам", show_alert=True)
        return

    service = await service_repo.get_by_id(service_id)
    min_duration = _get_min_duration_from_state(data)
    if service:
        min_duration = _normalize_min_duration_minutes(service.min_duration_minutes)
        await state.update_data(min_duration_minutes=min_duration)
    if duration < min_duration:
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
    duration_text = message.text.strip()

    try:
        duration = int(duration_text)
    except ValueError:
        await message.answer(
            "⚠️ <b>Введите число</b>\n\n"
            "Пожалуйста, укажите продолжительность в минутах.\n"
            "Пример: 60, 120, 180",
            parse_mode="HTML"
        )
        return

    if duration > 720:
        await message.answer(
            "⚠️ <b>Слишком большая длительность</b>\n\n"
            "Максимальная продолжительность: 720 минут (весь день).\n"
            "Если нужен особый формат, согласуйте его отдельно.",
            parse_mode="HTML"
        )
        return

    if duration % 60 != 0:
        await message.answer(
            "⚠️ <b>Длительность должна быть кратна 60 минутам</b>\n\n"
            "Допустимые значения: 60, 120, 180, 240...",
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
        if duration < min_duration:
            await message.answer(
                f"⚠️ <b>Минимальная продолжительность: {min_duration} мин.</b>\n\n"
                f"Пожалуйста, выберите длительность не меньше {min_duration} минут.",
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
        "📧 <b>Введите ваш e-mail (необязательно):</b>\n\n"
        "E-mail нужен для отправки подтверждения бронирования.\n"
        "Пример: example@mail.ru\n\n"
        "Чтобы пропустить шаг, отправьте /skip.",
        parse_mode="HTML"
    )

async def process_email_input(message: Message, state: FSMContext):
    """Обработка e-mail."""
    email_text = message.text.strip()
    
    if email_text.lower() in ['/skip', 'skip']:
        email = None
    else:
        import re
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(email_pattern, email_text):
            await message.answer(
                "⚠️ <b>Некорректный e-mail</b>\n\n"
                "Пожалуйста, введите корректный адрес электронной почты.\n"
                "Пример: example@mail.ru\n\n"
                "Чтобы пропустить шаг, отправьте /skip.",
                parse_mode="HTML"
            )
            return
        email = email_text
    
    data = await state.get_data()
    booking_data = data.get('booking_data', {})
    booking_data['email'] = email
    if 'service_name' not in booking_data:
        booking_data['service_name'] = data.get('service_name', '')
    await state.update_data(booking_data=booking_data)
    
    await state.set_state(BookingStates.filling_form)
    
    service_id = data.get('service_id')
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
    current_extras = booking_data.get('extras', [])
    
    available_extras = {
        'photographer': '📸 Фотограф (11 500 ₽: съёмка, обработка и сопровождение)',
        'makeuproom': '💄 Гримерка (200/250 ₽/час)',
        'fireplace': '🔥 Розжиг камина (400 ₽)',
        'rental': '🧺 Прокат: халат и полотенце (200 ₽)'
    }
    
    text = "➕ <b>Дополнительные услуги:</b>\n\n"
    text += "Выберите нужные опции:\n\n"
    
    for key, label in available_extras.items():
        status = "✅" if key in current_extras else "▫️"
        text += f"{status} {label}\n"
    
    text += "\nНажмите на кнопку ниже, чтобы добавить или убрать услугу."
    text += "\n\n<i>Гримерка доступна с 9:00 до 21:00 и бронируется по времени начала съемки.</i>"
    
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    
    keyboard = []
    for key, label in available_extras.items():
        is_selected = key in current_extras
        button_text = f"{'✅' if is_selected else '➕'} {label.split('(')[0].strip()}"
        action = "remove" if is_selected else "add"
        keyboard.append([
            InlineKeyboardButton(
                text=button_text,
                callback_data=f"booking_toggle_extra_{service_id}_{key}_{action}"
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
    extra_key = parts[4]
    action = parts[5]  # "add" or "remove"
    
    data = await state.get_data()
    booking_data = data.get('booking_data', {})
    extras = booking_data.get('extras', [])
    
    if action == "add" and extra_key not in extras:
        extras.append(extra_key)
    elif action == "remove" and extra_key in extras:
        extras.remove(extra_key)
    
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

    required_fields = ['date', 'time', 'name', 'last_name', 'phone', 'guests_count']
    missing_fields = []
    
    for field in required_fields:
        if not booking_data.get(field):
            missing_fields.append(field)

    service = await service_repo.get_by_id(service_id)
    if service and booking_data.get('guests_count'):
        max_guests = _normalize_max_guests(service.max_num_clients)
        if int(booking_data['guests_count']) > max_guests:
            await callback.answer(
                f"Максимальная вместимость этой услуги: {max_guests} чел.",
                show_alert=True
            )
            return
    
    if missing_fields:
        field_names = {
            'date': 'Дата',
            'time': 'Время',
            'name': 'Имя',
            'last_name': 'Фамилия',
            'phone': 'Номер телефона',
            'guests_count': 'Количество гостей'
        }
        
        missing_names = [field_names[field] for field in missing_fields]
        
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
    
    if CALENDAR_AVAILABLE and GoogleCalendarService:
        print(f"[CALENDAR] Попытка создания события в календаре для {_format_full_name(booking_data)}")
        try:
            event_start = selected_datetime
            event_end = event_start + timedelta(minutes=duration_minutes)
            
            print(f"[CALENDAR] Создание события: {event_start} - {event_end}")
            
            extras = booking_data.get('extras', [])
            need_photographer = "Да" if "photographer" in extras else "Нет"
            need_makeuproom = "Да" if "makeuproom" in extras else "Нет"
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

            username = callback.from_user.username
            telegram_link = f"https://t.me/{username}" if username else "не указан"

            event_description = f"""
<b>Кто забронировал</b>
{_format_full_name(booking_data)}
email: {booking_data.get('email', 'не указан')}
{booking_data['phone']}
Telegram: {telegram_link}

<b>Какой зал вы хотите забронировать?</b>
{service_name}

Service ID: {service_id}

<b>Какое количество гостей планируется, включая фотографа?</b>
{booking_data['guests_count']}

<b>Нужна ли гримерная за час до съемки?</b>
{need_makeuproom}

<b>Нужен ли фотограф?</b> 
{need_photographer}

<b>Дополнительные услуги:</b>
{extras_display}

<b><u>ВНИМАНИЕ</u></b> Автоматически на вашу электронную почту приходит подтверждение о <b><u>предварительном бронировании времени</u></b><u>.</u> Вам нужно:

<ul><li>дождаться информации о предоплате</li><li>отправить нам скриншот оплаты в течение 24-х часов</li><li>получить от нас подтверждение, что желаемая дата и время забронировано.</li></ul>

�������� ����������, �� ������������ � <a href="https://www.google.com/url?q=https%3A%2F%2Fvk.com%2Fpages%3Fhash%3Ddd2aea6878aabba105%26oid%3D-174809315%26p%3D%25D0%259F%25D0%25A0%25D0%2590%25D0%2592%25D0%2598%25D0%259B%25D0%2590_%25D0%2590%25D0%25A0%25D0%2595%25D0%259D%25D0%2594%25D0%25AB_%25D0%25A4%25D0%259E%25D0%25A2%25D0%259E%25D0%25A1%25D0%25A2%25D0%25A3%25D0%2594%25D0%2598%25D0%2598&amp;sa=D&amp;source=calendar&amp;ust=1762503000000000&amp;usg=AOvVaw0LR6y1Ukh_SRdIeJXIrHOT" target="_blank" data-link-id="34" rel="noopener noreferrer">��������� ������ ����������</a>
            """.strip()
            
            calendar_service = GoogleCalendarService()
            print("[CALENDAR] Вызов calendar_service.create_event...")
            result = await calendar_service.create_event(
                title=f"{service_name}",
                description=event_description,
                start_time=event_start,
                end_time=event_end
            )
            print(f"[CALENDAR] Событие успешно создано в календаре: {result.get('htmlLink', 'N/A')}")

            if service_id != 9:
                try:
                    extra_service = await service_repo.get_by_id(9)
                    extra_name = extra_service.name if extra_service else "Доп. услуга"
                    extra_start = event_start - timedelta(hours=1)
                    extra_end = event_start
                    main_event_id = result.get("id")
                    main_event_link = result.get("htmlLink")
                    extra_description = (
                        f"<b>Доп. услуга</b>\n"
                        f"Для бронирования: {service_name}\n"
                        f"Service ID: 9\n"
                        f"Linked Service ID: {service_id}\n"
                        f"Связано с событием: {main_event_id or 'неизвестно'}\n"
                        f"Ссылка на основное событие: {main_event_link or 'неизвестно'}\n"
                    )
                    await calendar_service.create_event(
                        title=f"{extra_name}: {service_name}",
                        description=extra_description,
                        start_time=extra_start,
                        end_time=extra_end
                    )
                except Exception as e:
                    print(f"[CALENDAR] Не удалось создать доп. слот id=9: {e}")
            
        except Exception as e:
            import traceback
            print(f"[ERROR] Ошибка создания события в календаре: {e}")
            print(f"[ERROR] Детали ошибки:\n{traceback.format_exc()}")
    else:
        print(f"[WARNING] Календарь недоступен. CALENDAR_AVAILABLE={CALENDAR_AVAILABLE}, GoogleCalendarService={GoogleCalendarService}")
    
    try:
        from database import client_repo
        from database.models import Client

        phone_clean = booking_data['phone'].replace('+7 ', '').replace(' ', '').replace('-', '')
        if len(phone_clean) == 11 and phone_clean.startswith('7'):
            phone_clean = phone_clean[1:]

        client = await client_repo.get_by_telegram_id(telegram_id)
        if not client:
            client_id = await client_repo.create(
                Client(
                    telegram_id=telegram_id,
                    name=booking_data['name'],
                    last_name=booking_data.get('last_name') or "",
                    phone=phone_clean,
                    email=booking_data.get('email'),
                )
            )
            client = await client_repo.get_by_id(client_id)
        else:
            client.name = booking_data['name']
            client.last_name = booking_data.get('last_name') or ""
            client.phone = phone_clean
            if booking_data.get('email'):
                client.email = booking_data.get('email')
            await client_repo.update(client)

    except Exception as e:
        print(f"Ошибка обновления клиента в БД: {e}")

    try:
        from database import admin_repo
        from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

        extras = booking_data.get('extras', [])
        extras_labels = {
            'photographer': 'Фотограф',
            'makeuproom': 'Гримерка',
            'fireplace': 'Розжиг камина',
            'rental': 'Прокат: халат и полотенце'
        }
        extras_display = ", ".join(extras_labels.get(e, e) for e in extras) if extras else "Нет"

        username = callback.from_user.username
        phone_digits = "".join(ch for ch in booking_data['phone'] if ch.isdigit())
        if len(phone_digits) == 11 and phone_digits.startswith(("7", "8")):
            phone_digits = phone_digits[1:]
        phone_clean = phone_digits

        contact_url = f"https://t.me/{username}" if username else f"tg://user?id={telegram_id}"

        phone_display = booking_data['phone']
        phone_html = f"<code>{phone_display}</code>"

        admin_text = (
            "📅 <b>Новая бронь</b>\n\n"
            f"🎯 Услуга: {service_name}\n"
            f"📅 Дата: {selected_date.strftime('%d.%m.%Y')}\n"
            f"🕒 Время: {time_range_display}\n"
            f"👤 Клиент: {_format_full_name(booking_data)}\n"
            f"📱 Телефон: {phone_html}\n"
            f"👥 Гостей: {booking_data['guests_count']}\n"
            f"➕ Доп. услуги: {extras_display}\n"
        )

        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Связаться в Telegram", url=contact_url)],
            [InlineKeyboardButton(text="Связаться во внутреннем чате", callback_data=f"support_reply_{telegram_id}")]
        ])

        admins = await admin_repo.get_all()
        for admin in admins:
            if not admin.is_active or not admin.telegram_id:
                continue
            try:
                await callback.bot.send_message(
                    admin.telegram_id,
                    admin_text,
                    reply_markup=keyboard,
                    parse_mode="HTML"
                )
            except Exception as e:
                print(f"Не удалось отправить уведомление админу {admin.telegram_id}: {e}")
    except Exception as e:
        print(f"Ошибка админского уведомления: {e}")

    await callback.message.edit_text(
        f"✅ <b>Бронирование оформлено!</b>\n\n"
        f"📅 <b>Дата:</b> {selected_date.strftime('%d.%m.%Y')}\n"
        f"🕒 <b>Время:</b> {time_range_display}\n"
        f"👤 <b>Клиент:</b> {_format_full_name(booking_data)}\n"
        f"📱 <b>Телефон:</b> {booking_data['phone']}\n"
        f"👥 <b>Гостей:</b> {booking_data['guests_count']}\n"
        f"⏰ <b>Продолжительность:</b> {duration_minutes} мин.\n\n"
        f"🎯 <b>Услуга:</b> {service_name}\n\n"
        f"📩 <b>Спасибо за бронирование! Ожидайте информацию о предоплате.</b>",
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
    dp.callback_query.register(time_prev_date, F.data.startswith("time_prev_date_"))
    dp.callback_query.register(time_next_date, F.data.startswith("time_next_date_"))
    dp.callback_query.register(confirm_time_selection, F.data.startswith("select_time_"))
    dp.callback_query.register(back_from_date_selection, F.data.startswith("booking_back_from_date_"))
    dp.callback_query.register(back_from_time_selection, F.data.startswith("booking_back_from_time_"))
    dp.callback_query.register(start_name_input, F.data.startswith("booking_name_"))
    dp.message.register(process_name_input, BookingStates.entering_name)
    dp.callback_query.register(start_last_name_input, F.data.startswith("booking_last_name_"))
    dp.message.register(process_last_name_input, BookingStates.entering_last_name)
    dp.callback_query.register(start_phone_input, F.data.startswith("booking_phone_"))
    dp.message.register(process_phone_input, BookingStates.entering_phone)
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








