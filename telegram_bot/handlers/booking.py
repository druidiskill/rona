from aiogram import Dispatcher, F
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from datetime import datetime, timedelta, date

from telegram_bot.keyboards import get_booking_form_keyboard, get_main_menu_keyboard, get_date_selection_keyboard, get_time_selection_keyboard
from telegram_bot.states import BookingStates
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


async def start_booking(callback: CallbackQuery, state: FSMContext):
    """Начало бронирования"""
    service_id = int(callback.data.split("_")[2])
    service = await service_repo.get_by_id(service_id)
    
    if not service:
        await callback.answer("Услуга не найдена", show_alert=True)
        return
    
    # Проверяем, есть ли уже клиент с таким telegram_id
    from database import client_repo
    telegram_id = callback.from_user.id
    existing_client = await client_repo.get_by_telegram_id(telegram_id)
    
    # Инициализируем данные бронирования
    if existing_client and existing_client.phone:
        # Если клиент уже существует и у него есть телефон, заполняем его данные
        # Форматируем телефон для отображения (+7 XXX XXX XX XX)
        phone_display = f"+7 {existing_client.phone[:3]} {existing_client.phone[3:6]} {existing_client.phone[6:8]} {existing_client.phone[8:10]}"
        
        await state.update_data(
            service_id=service_id,
            service_name=service.name,
            booking_data={
                'date': None,
                'time': None,
                'name': existing_client.name,
                'phone': phone_display,
                'guests_count': None,
                'duration': 60,  # По умолчанию 1 час
                'extras': [],
                'email': existing_client.email,
                'service_name': service.name  # Сохраняем название услуги в booking_data
            }
        )
    else:
        # Если клиента нет или у него нет телефона, заполняем пустыми значениями
        await state.update_data(
            service_id=service_id,
            service_name=service.name,
            booking_data={
                'date': None,
                'time': None,
                'name': None,
                'phone': None,
                'guests_count': None,
                'duration': 60,  # По умолчанию 1 час
                'extras': [],
                'email': None,
                'service_name': service.name  # Сохраняем название услуги в booking_data
            }
        )
    await state.set_state(BookingStates.filling_form)
    
    await show_booking_form(callback, state)

async def show_booking_form(callback: CallbackQuery, state: FSMContext):
    """Показ формы бронирования"""
    data = await state.get_data()
    booking_data = data.get('booking_data', {})
    # Получаем service_name из booking_data или из state
    service_name = booking_data.get('service_name') or data.get('service_name', '')
    service_id = data.get('service_id')
    
    text = f"📝 <b>Бронирование услуги: {service_name}</b>\n\n"
    text += "📋 <b>Заполните данные для бронирования:</b>\n\n"
    
    # Обязательные поля
    text += f"‼️ <b>Дата:</b> {booking_data.get('date', 'Не выбрано')}\n"
    text += f"‼️ <b>Время:</b> {booking_data.get('time', 'Не выбрано')}\n"
    text += f"‼️ <b>Имя:</b> {booking_data.get('name', 'Не указано')}\n"
    text += f"‼️ <b>Номер телефона:</b> {booking_data.get('phone', 'Не указан')}\n"
    text += f"‼️ <b>Количество гостей:</b> {booking_data.get('guests_count', 'Не указано')}\n"
    
    # Необязательные поля
    text += f"⏰ <b>Продолжительность:</b> {booking_data.get('duration', 60)} мин.\n"
    
    # Форматируем дополнительные услуги для отображения
    extras = booking_data.get('extras', [])
    extras_display = []
    extras_labels = {
        'photographer': '📸 Фотограф',
        'makeuproom': '💄 Гримерка'
    }
    for extra in extras:
        extras_display.append(extras_labels.get(extra, extra))
    text += f"➕ <b>Доп. услуги:</b> {', '.join(extras_display) if extras_display else 'Нет'}\n"
    
    email_display = booking_data.get('email', 'Не указан')
    if email_display:
        text += f"✅ <b>E-mail:</b> {email_display}\n"
    else:
        text += f"📧 <b>E-mail:</b> {email_display}\n"
    text += "\n"
    
    text += "Выберите параметр для заполнения:"
    
    # Проверяем, что service_id не None
    if service_id is None:
        await callback.answer("Ошибка: ID услуги не найден", show_alert=True)
        return
    
    await callback.message.edit_text(
        text,
        reply_markup=get_booking_form_keyboard(service_id, booking_data),
        parse_mode="HTML"
    )

async def select_date(callback: CallbackQuery, state: FSMContext):
    """Выбор даты для бронирования"""
    parts = callback.data.split("_")
    if len(parts) < 3:
        await callback.answer("Ошибка в данных", show_alert=True)
        return
    
    service_id = int(parts[2])
    
    await callback.message.edit_text(
        "📅 <b>Выберите дату:</b>\n\n"
        "Доступны следующие даты:",
        reply_markup=get_date_selection_keyboard(service_id),
        parse_mode="HTML"
    )

async def select_time(callback: CallbackQuery, state: FSMContext):
    """Выбор времени для бронирования"""
    parts = callback.data.split("_")
    
    if len(parts) < 3:
        await callback.answer("Ошибка в данных", show_alert=True)
        return
    
    if parts[2] == 'None' or parts[2] == 'null':
        await callback.answer("Ошибка: неверный ID услуги", show_alert=True)
        return
    
    service_id = int(parts[2])
    
    # Получаем данные из состояния
    data = await state.get_data()
    booking_data = data.get('booking_data', {})
    selected_date = booking_data.get('date')
    
    if not selected_date:
        await callback.answer("Сначала выберите дату", show_alert=True)
        return
    
    try:
        # Получаем доступные временные слоты из Google Calendar
        if CALENDAR_AVAILABLE and GoogleCalendarService:
            calendar_service = GoogleCalendarService()
            selected_date_obj = datetime.strptime(selected_date, "%Y-%m-%d").date()
            start_of_day = datetime.combine(selected_date_obj, datetime.min.time())
            end_of_day = datetime.combine(selected_date_obj, datetime.max.time())
            
            # Получаем свободные слоты по 1 часу (60 минут)
            available_slots = await calendar_service.get_free_slots(
                date=selected_date_obj,
                duration_minutes=60  # Фиксированно 1 час
            )
            
            if not available_slots:
                await callback.message.edit_text(
                    f"❌ <b>На {selected_date_obj.strftime('%d.%m.%Y')} нет свободных слотов</b>\n\n"
                    "Попробуйте выбрать другую дату.",
                    reply_markup=get_booking_form_keyboard(service_id, booking_data),
                    parse_mode="HTML"
                )
                return
            
            # Создаем временные слоты
            time_slots = []
            for slot in available_slots:
                time_slots.append({
                    'start_time': slot['start'].time(),
                    'end_time': slot['end'].time(),
                    'is_available': True
                })
        else:
            # Если календарь недоступен, создаем стандартные слоты (9:00 - 21:00)
            selected_date_obj = datetime.strptime(selected_date, "%Y-%m-%d").date()
            time_slots = []
            for hour in range(9, 21):
                time_slots.append({
                    'start_time': datetime.strptime(f"{hour:02d}:00", "%H:%M").time(),
                    'end_time': datetime.strptime(f"{hour+1:02d}:00", "%H:%M").time(),
                    'is_available': True
                })
        
        # Сохраняем временные слоты в состоянии
        await state.update_data(time_slots=time_slots)
        
        try:
            await callback.message.edit_text(
                f"🕒 <b>Выберите время на {selected_date_obj.strftime('%d.%m.%Y')}</b>\n\n"
                "Доступные времена (слоты по 1 часу):",
                reply_markup=get_time_selection_keyboard(service_id, time_slots, selected_date),
                parse_mode="HTML"
            )
        except Exception as e:
            if "message is not modified" in str(e):
                await callback.answer("Время уже выбрано")
            else:
                print(f"Ошибка редактирования сообщения: {e}")
                await callback.answer("Ошибка обновления сообщения", show_alert=True)
        
    except Exception as e:
        print(f"Ошибка получения данных из Google Calendar: {e}")
        await callback.message.edit_text(
            f"❌ <b>Ошибка получения доступного времени</b>\n\n"
            "Попробуйте позже или выберите другую дату.",
            reply_markup=get_booking_form_keyboard(service_id, booking_data),
            parse_mode="HTML"
        )

async def date_prev_week(callback: CallbackQuery, state: FSMContext):
    """Предыдущая неделя"""
    parts = callback.data.split("_")
    service_id = int(parts[3])
    week_offset = int(parts[4])
    
    await callback.message.edit_text(
        "📅 <b>Выберите дату:</b>\n\n"
        "Доступны следующие даты:",
        reply_markup=get_date_selection_keyboard(service_id, week_offset),
        parse_mode="HTML"
    )

async def date_next_week(callback: CallbackQuery, state: FSMContext):
    """Следующая неделя"""
    parts = callback.data.split("_")
    service_id = int(parts[3])
    week_offset = int(parts[4])
    
    await callback.message.edit_text(
        "📅 <b>Выберите дату:</b>\n\n"
        "Доступны следующие даты:",
        reply_markup=get_date_selection_keyboard(service_id, week_offset),
        parse_mode="HTML"
    )

async def confirm_date_selection(callback: CallbackQuery, state: FSMContext):
    """Подтверждение выбора даты"""
    parts = callback.data.split("_")
    service_id = int(parts[2])
    selected_date = parts[3]  # YYYY-MM-DD format
    
    # Сохраняем выбранную дату в состоянии
    data = await state.get_data()
    booking_data = data.get('booking_data', {})
    booking_data['date'] = selected_date
    # Сохраняем service_name если его еще нет в booking_data
    if 'service_name' not in booking_data:
        booking_data['service_name'] = data.get('service_name', '')
    await state.update_data(booking_data=booking_data)
    
    # Возвращаемся к форме бронирования
    await show_booking_form(callback, state)

async def time_prev_date(callback: CallbackQuery, state: FSMContext):
    """Предыдущая дата в выборе времени"""
    parts = callback.data.split("_")
    service_id = int(parts[3])
    prev_date = parts[4]  # YYYY-MM-DD format
    
    # Обновляем выбранную дату в состоянии
    data = await state.get_data()
    booking_data = data.get('booking_data', {})
    booking_data['date'] = prev_date
    # Сохраняем service_name если его еще нет в booking_data
    if 'service_name' not in booking_data:
        booking_data['service_name'] = data.get('service_name', '')
    await state.update_data(booking_data=booking_data)
    
    # Получаем временные слоты для новой даты
    try:
        if CALENDAR_AVAILABLE and GoogleCalendarService:
            calendar_service = GoogleCalendarService()
            prev_date_obj = datetime.strptime(prev_date, "%Y-%m-%d").date()
            
            available_slots = await calendar_service.get_free_slots(
                date=prev_date_obj,
                duration_minutes=60
        )
        
        if not available_slots:
            await callback.message.edit_text(
                f"❌ <b>На {prev_date_obj.strftime('%d.%m.%Y')} нет свободных слотов</b>\n\n"
                "Попробуйте выбрать другую дату.",
                reply_markup=get_booking_form_keyboard(service_id, booking_data),
                parse_mode="HTML"
            )
            return
        
        # Создаем временные слоты
        time_slots = []
        for slot in available_slots:
            time_slots.append({
                'start_time': slot['start'].time(),
                'end_time': slot['end'].time(),
                'is_available': True
            })
        else:
            # Если календарь недоступен, создаем стандартные слоты (9:00 - 21:00)
            prev_date_obj = datetime.strptime(prev_date, "%Y-%m-%d").date()
            time_slots = []
            for hour in range(9, 21):
                time_slots.append({
                    'start_time': datetime.strptime(f"{hour:02d}:00", "%H:%M").time(),
                    'end_time': datetime.strptime(f"{hour+1:02d}:00", "%H:%M").time(),
                    'is_available': True
                })
        
        # Сохраняем временные слоты в состоянии
        await state.update_data(time_slots=time_slots)
        
        await callback.message.edit_text(
            f"🕒 <b>Выберите время на {prev_date_obj.strftime('%d.%m.%Y')}</b>\n\n"
            "Доступные времена (слоты по 1 часу):",
            reply_markup=get_time_selection_keyboard(service_id, time_slots, prev_date),
            parse_mode="HTML"
        )
        
    except Exception as e:
        print(f"Ошибка получения данных из Google Calendar: {e}")
        await callback.message.edit_text(
            f"❌ <b>Ошибка получения доступного времени</b>\n\n"
            "Попробуйте позже или выберите другую дату.",
            reply_markup=get_booking_form_keyboard(service_id, booking_data),
            parse_mode="HTML"
        )

async def time_next_date(callback: CallbackQuery, state: FSMContext):
    """Следующая дата в выборе времени"""
    parts = callback.data.split("_")
    service_id = int(parts[3])
    next_date = parts[4]  # YYYY-MM-DD format
    
    # Обновляем выбранную дату в состоянии
    data = await state.get_data()
    booking_data = data.get('booking_data', {})
    booking_data['date'] = next_date
    # Сохраняем service_name если его еще нет в booking_data
    if 'service_name' not in booking_data:
        booking_data['service_name'] = data.get('service_name', '')
    await state.update_data(booking_data=booking_data)
    
    # Получаем временные слоты для новой даты
    try:
        if CALENDAR_AVAILABLE and GoogleCalendarService:
            calendar_service = GoogleCalendarService()
            next_date_obj = datetime.strptime(next_date, "%Y-%m-%d").date()
            
            available_slots = await calendar_service.get_free_slots(
                date=next_date_obj,
                duration_minutes=60
        )
        
        if not available_slots:
            await callback.message.edit_text(
                f"❌ <b>На {next_date_obj.strftime('%d.%m.%Y')} нет свободных слотов</b>\n\n"
                "Попробуйте выбрать другую дату.",
                reply_markup=get_booking_form_keyboard(service_id, booking_data),
                parse_mode="HTML"
            )
            return
        
        # Создаем временные слоты
        time_slots = []
        for slot in available_slots:
            time_slots.append({
                'start_time': slot['start'].time(),
                'end_time': slot['end'].time(),
                'is_available': True
            })
        else:
            # Если календарь недоступен, создаем стандартные слоты (9:00 - 21:00)
            next_date_obj = datetime.strptime(next_date, "%Y-%m-%d").date()
            time_slots = []
            for hour in range(9, 21):
                time_slots.append({
                    'start_time': datetime.strptime(f"{hour:02d}:00", "%H:%M").time(),
                    'end_time': datetime.strptime(f"{hour+1:02d}:00", "%H:%M").time(),
                    'is_available': True
                })
        
        # Сохраняем временные слоты в состоянии
        await state.update_data(time_slots=time_slots)
        
        await callback.message.edit_text(
            f"🕒 <b>Выберите время на {next_date_obj.strftime('%d.%m.%Y')}</b>\n\n"
            "Доступные времена (слоты по 1 часу):",
            reply_markup=get_time_selection_keyboard(service_id, time_slots, next_date),
            parse_mode="HTML"
        )
        
    except Exception as e:
        print(f"Ошибка получения данных из Google Calendar: {e}")
        await callback.message.edit_text(
            f"❌ <b>Ошибка получения доступного времени</b>\n\n"
            "Попробуйте позже или выберите другую дату.",
            reply_markup=get_booking_form_keyboard(service_id, booking_data),
            parse_mode="HTML"
        )

async def confirm_time_selection(callback: CallbackQuery, state: FSMContext):
    """Подтверждение выбора времени"""
    parts = callback.data.split("_")
    service_id = int(parts[2])
    time_index = int(parts[3])
    
    # Получаем данные из состояния
    data = await state.get_data()
    booking_data = data.get('booking_data', {})
    time_slots = data.get('time_slots', [])
    
    # Получаем выбранное время из временных слотов
    if time_index < len(time_slots):
        selected_slot = time_slots[time_index]
        selected_time = f"{selected_slot['start_time'].strftime('%H:%M')} - {selected_slot['end_time'].strftime('%H:%M')}"
    else:
        selected_time = "09:00 - 10:00"  # Fallback
    
    # Сохраняем выбранное время в состоянии
    data = await state.get_data()
    booking_data = data.get('booking_data', {})
    booking_data['time'] = selected_time
    # Сохраняем service_name если его еще нет в booking_data
    if 'service_name' not in booking_data:
        booking_data['service_name'] = data.get('service_name', '')
    await state.update_data(booking_data=booking_data)
    
    # Возвращаемся к форме бронирования
    await show_booking_form(callback, state)

async def back_from_date_selection(callback: CallbackQuery, state: FSMContext):
    """Назад из выбора даты к форме бронирования"""
    parts = callback.data.split("_")
    service_id = int(parts[4])  # booking_back_from_date_{service_id}
    
    # Возвращаемся к форме бронирования с сохранением данных
    await show_booking_form(callback, state)

async def back_from_time_selection(callback: CallbackQuery, state: FSMContext):
    """Назад из выбора времени к форме бронирования"""
    parts = callback.data.split("_")
    service_id = int(parts[4])  # booking_back_from_time_{service_id}
    
    # Возвращаемся к форме бронирования с сохранением данных
    await show_booking_form(callback, state)

async def start_name_input(callback: CallbackQuery, state: FSMContext):
    """Начало ввода имени"""
    parts = callback.data.split("_")
    service_id = int(parts[2])
    
    await state.set_state(BookingStates.entering_name)
    await callback.message.edit_text(
        "👤 <b>Введите ваше имя:</b>\n\n"
        "Имя должно содержать только буквы и быть длиннее 1 символа.\n"
        "Например: Анна, Иван, Мария",
        parse_mode="HTML"
    )

async def process_name_input(message: Message, state: FSMContext):
    """Обработка введенного имени"""
    name = message.text.strip()
    
    # Проверяем, что имя содержит только буквы и длиннее 1 символа
    if not name or len(name) < 2:
        await message.answer(
            "❌ <b>Имя слишком короткое</b>\n\n"
            "Пожалуйста, введите имя длиннее 1 символа.",
            parse_mode="HTML"
        )
        return
    
    # Проверяем, что имя содержит только буквы (включая русские)
    if not name.replace(' ', '').replace('-', '').isalpha():
        await message.answer(
            "❌ <b>Имя содержит недопустимые символы</b>\n\n"
            "Имя должно содержать только буквы, пробелы и дефисы.\n"
            "Например: Анна, Иван-Петр, Мария Ивановна",
            parse_mode="HTML"
        )
        return
    
    # Сохраняем имя в состоянии
    data = await state.get_data()
    booking_data = data.get('booking_data', {})
    booking_data['name'] = name
    # Сохраняем service_name если его еще нет в booking_data
    if 'service_name' not in booking_data:
        booking_data['service_name'] = data.get('service_name', '')
    await state.update_data(booking_data=booking_data)
    
    # Возвращаемся к форме бронирования
    await state.set_state(BookingStates.filling_form)
    
    # Получаем service_id из состояния
    service_id = data.get('service_id')
    if service_id:
        # Показываем форму бронирования как новое сообщение
        data = await state.get_data()
        booking_data = data.get('booking_data', {})
        service_name = data.get('service_name', '')
        
        text = f"📝 <b>Бронирование услуги: {service_name}</b>\n\n"
        text += "📋 <b>Заполните данные для бронирования:</b>\n\n"
        
        # Обязательные поля
        text += f"✅ <b>Дата:</b> {booking_data.get('date', 'Не выбрано')}\n"
        text += f"✅ <b>Время:</b> {booking_data.get('time', 'Не выбрано')}\n"
        text += f"✅ <b>Имя:</b> {booking_data.get('name', 'Не указано')}\n"
        text += f"‼️ <b>Номер телефона:</b> {booking_data.get('phone', 'Не указан')}\n"
        text += f"‼️ <b>Количество гостей:</b> {booking_data.get('guests_count', 'Не указано')}\n"
        
        # Необязательные поля
        text += f"⏰ <b>Продолжительность:</b> {booking_data.get('duration', 60)} мин.\n"
        text += f"➕ <b>Доп. услуги:</b> {', '.join(booking_data.get('extras', [])) if booking_data.get('extras') else 'Нет'}\n"
        text += f"📧 <b>E-mail:</b> {booking_data.get('email', 'Не указан')}\n\n"
        
        text += "Выберите параметр для заполнения:"
        
        await message.answer(
            text,
            reply_markup=get_booking_form_keyboard(service_id, booking_data),
            parse_mode="HTML"
        )

async def start_phone_input(callback: CallbackQuery, state: FSMContext):
    """Начало ввода номера телефона"""
    parts = callback.data.split("_")
    service_id = int(parts[2])
    
    await state.set_state(BookingStates.entering_phone)
    await callback.message.edit_text(
        "📱 <b>Введите ваш номер телефона:</b>\n\n"
        "Номер должен начинаться с +7 или 8 и содержать 10 цифр после кода страны.\n"
        "Например: +7 900 123 45 67 или 8 900 123 45 67",
        parse_mode="HTML"
    )

async def process_phone_input(message: Message, state: FSMContext):
    """Обработка введенного номера телефона"""
    phone = message.text.strip()
    
    # Очищаем номер от всех символов кроме цифр и +
    clean_phone = ''.join(c for c in phone if c.isdigit() or c == '+')
    
    # Проверяем базовые требования
    if not phone or len(clean_phone) < 10:
        await message.answer(
            "❌ <b>Номер телефона слишком короткий</b>\n\n"
            "Пожалуйста, введите полный номер телефона.\n"
            "Например: +7 900 123 45 67",
            parse_mode="HTML"
        )
        return
    
    # Проверяем формат номера
    is_valid = False
    formatted_phone = ""
    
    # Проверяем российские номера
    if clean_phone.startswith('+7') and len(clean_phone) == 12:
        # +7XXXXXXXXXX
        formatted_phone = f"+7 {clean_phone[2:5]} {clean_phone[5:8]} {clean_phone[8:10]} {clean_phone[10:12]}"
        is_valid = True
    elif clean_phone.startswith('8') and len(clean_phone) == 11:
        # 8XXXXXXXXXX
        formatted_phone = f"+7 {clean_phone[1:4]} {clean_phone[4:7]} {clean_phone[7:9]} {clean_phone[9:11]}"
        is_valid = True
    elif clean_phone.startswith('7') and len(clean_phone) == 11:
        # 7XXXXXXXXXX
        formatted_phone = f"+7 {clean_phone[1:4]} {clean_phone[4:7]} {clean_phone[7:9]} {clean_phone[9:11]}"
        is_valid = True
    elif len(clean_phone) == 10 and clean_phone.startswith('9'):
        # 9XXXXXXXXX (без кода страны)
        formatted_phone = f"+7 {clean_phone[0:3]} {clean_phone[3:6]} {clean_phone[6:8]} {clean_phone[8:10]}"
        is_valid = True
    
    if not is_valid:
        await message.answer(
            "❌ <b>Неверный формат номера телефона</b>\n\n"
            "Пожалуйста, введите номер в одном из форматов:\n"
            "• +7 900 123 45 67\n"
            "• 8 900 123 45 67\n"
            "• 7 900 123 45 67\n"
            "• 900 123 45 67",
            parse_mode="HTML"
        )
        return
    
    # Сохраняем номер в состоянии
    data = await state.get_data()
    booking_data = data.get('booking_data', {})
    booking_data['phone'] = formatted_phone
    # Сохраняем service_name если его еще нет в booking_data
    if 'service_name' not in booking_data:
        booking_data['service_name'] = data.get('service_name', '')
    await state.update_data(booking_data=booking_data)
    
    # Возвращаемся к форме бронирования
    await state.set_state(BookingStates.filling_form)
    
    # Получаем service_id из состояния
    service_id = data.get('service_id')
    if service_id:
        # Показываем форму бронирования как новое сообщение
        data = await state.get_data()
        booking_data = data.get('booking_data', {})
        service_name = data.get('service_name', '')
        
        text = f"📝 <b>Бронирование услуги: {service_name}</b>\n\n"
        text += "📋 <b>Заполните данные для бронирования:</b>\n\n"
        
        # Обязательные поля
        text += f"✅ <b>Дата:</b> {booking_data.get('date', 'Не выбрано')}\n"
        text += f"✅ <b>Время:</b> {booking_data.get('time', 'Не выбрано')}\n"
        text += f"✅ <b>Имя:</b> {booking_data.get('name', 'Не указано')}\n"
        text += f"✅ <b>Номер телефона:</b> {booking_data.get('phone', 'Не указан')}\n"
        text += f"‼️ <b>Количество гостей:</b> {booking_data.get('guests_count', 'Не указано')}\n"
        
        # Необязательные поля
        text += f"⏰ <b>Продолжительность:</b> {booking_data.get('duration', 60)} мин.\n"
        text += f"➕ <b>Доп. услуги:</b> {', '.join(booking_data.get('extras', [])) if booking_data.get('extras') else 'Нет'}\n"
        text += f"📧 <b>E-mail:</b> {booking_data.get('email', 'Не указан')}\n\n"
        
        text += "Выберите параметр для заполнения:"
        
        await message.answer(
            text,
            reply_markup=get_booking_form_keyboard(service_id, booking_data),
            parse_mode="HTML"
        )

async def start_guests_count_input(callback: CallbackQuery, state: FSMContext):
    """Начало ввода количества гостей"""
    parts = callback.data.split("_")
    service_id = int(parts[2])
    
    await state.set_state(BookingStates.entering_guests_count)
    await callback.message.edit_text(
        "👥 <b>Введите количество гостей:</b>\n\n"
        "Укажите количество человек, которые будут участвовать в фотосессии.\n"
        "Например: 2, 4, 6",
        parse_mode="HTML"
    )

async def process_guests_count_input(message: Message, state: FSMContext):
    """Обработка введенного количества гостей"""
    guests_text = message.text.strip()
    
    # Проверяем, что введено число
    try:
        guests_count = int(guests_text)
    except ValueError:
        await message.answer(
            "❌ <b>Неверный формат числа</b>\n\n"
            "Пожалуйста, введите количество гостей числом.\n"
            "Например: 2, 4, 6",
            parse_mode="HTML"
        )
        return
    
    # Проверяем диапазон (от 1 до 20 человек)
    if guests_count < 1:
        await message.answer(
            "❌ <b>Количество гостей должно быть больше 0</b>\n\n"
            "Пожалуйста, введите корректное количество гостей.\n"
            "Например: 1, 2, 4",
            parse_mode="HTML"
        )
        return
    
    if guests_count > 20:
        await message.answer(
            "❌ <b>Слишком много гостей</b>\n\n"
            "Максимальное количество гостей: 20 человек.\n"
            "Для больших групп свяжитесь с нами по телефону.",
            parse_mode="HTML"
        )
        return
    
    # Сохраняем количество гостей в состоянии
    data = await state.get_data()
    booking_data = data.get('booking_data', {})
    booking_data['guests_count'] = guests_count
    # Сохраняем service_name если его еще нет в booking_data
    if 'service_name' not in booking_data:
        booking_data['service_name'] = data.get('service_name', '')
    await state.update_data(booking_data=booking_data)
    
    # Возвращаемся к форме бронирования
    await state.set_state(BookingStates.filling_form)
    
    # Получаем service_id из состояния
    service_id = data.get('service_id')
    if service_id:
        # Показываем форму бронирования как новое сообщение
        data = await state.get_data()
        booking_data = data.get('booking_data', {})
        service_name = data.get('service_name', '')
        
        text = f"📝 <b>Бронирование услуги: {service_name}</b>\n\n"
        text += "📋 <b>Заполните данные для бронирования:</b>\n\n"
        
        # Обязательные поля
        text += f"✅ <b>Дата:</b> {booking_data.get('date', 'Не выбрано')}\n"
        text += f"✅ <b>Время:</b> {booking_data.get('time', 'Не выбрано')}\n"
        text += f"✅ <b>Имя:</b> {booking_data.get('name', 'Не указано')}\n"
        text += f"✅ <b>Номер телефона:</b> {booking_data.get('phone', 'Не указан')}\n"
        text += f"✅ <b>Количество гостей:</b> {booking_data.get('guests_count', 'Не указано')}\n"
        
        # Необязательные поля
        text += f"⏰ <b>Продолжительность:</b> {booking_data.get('duration', 60)} мин.\n"
        text += f"➕ <b>Доп. услуги:</b> {', '.join(booking_data.get('extras', [])) if booking_data.get('extras') else 'Нет'}\n"
        text += f"📧 <b>E-mail:</b> {booking_data.get('email', 'Не указан')}\n\n"
        
        text += "Выберите параметр для заполнения:"
        
        await message.answer(
            text,
            reply_markup=get_booking_form_keyboard(service_id, booking_data),
            parse_mode="HTML"
        )

async def start_duration_input(callback: CallbackQuery, state: FSMContext):
    """Начало ввода продолжительности"""
    parts = callback.data.split("_")
    service_id = int(parts[2])
    
    # Получаем информацию об услуге для отображения минимальной продолжительности
    from database import service_repo
    service = await service_repo.get_by_id(service_id)
    
    if service:
        min_duration = service.min_duration_minutes
        step_duration = service.duration_step_minutes
        duration_info = f"\n\n📋 <b>Информация:</b>\n• Минимальная продолжительность: {min_duration} мин.\n• Шаг: {step_duration} мин."
    else:
        duration_info = ""
    
    await state.set_state(BookingStates.entering_duration)
    await callback.message.edit_text(
        f"⏰ <b>Введите продолжительность фотосессии:</b>\n\n"
        f"Укажите продолжительность в минутах (кратно шагу).\n"
        f"Например: 60, 90, 120{duration_info}",
        parse_mode="HTML"
    )

async def process_duration_input(message: Message, state: FSMContext):
    """Обработка введенной продолжительности"""
    duration_text = message.text.strip()
    
    # Проверяем, что введено число
    try:
        duration = int(duration_text)
    except ValueError:
        await message.answer(
            "❌ <b>Неверный формат числа</b>\n\n"
            "Пожалуйста, введите продолжительность числом (в минутах).\n"
            "Например: 60, 90, 120",
            parse_mode="HTML"
        )
        return
    
    # Проверяем минимальную продолжительность (минимум 30 минут)
    if duration < 30:
        await message.answer(
            "❌ <b>Слишком короткая продолжительность</b>\n\n"
            "Минимальная продолжительность: 30 минут.\n"
            "Пожалуйста, введите корректную продолжительность.",
            parse_mode="HTML"
        )
        return
    
    # Проверяем максимальную продолжительность (максимум 8 часов = 480 минут)
    if duration > 480:
        await message.answer(
            "❌ <b>Слишком долгая продолжительность</b>\n\n"
            "Максимальная продолжительность: 480 минут (8 часов).\n"
            "Для более длительных съемок свяжитесь с нами по телефону.",
            parse_mode="HTML"
        )
        return
    
    # Получаем информацию об услуге для проверки шага
    data = await state.get_data()
    service_id = data.get('service_id')
    if service_id:
        from database import service_repo
        service = await service_repo.get_by_id(service_id)
        if service:
            step = service.duration_step_minutes
            min_duration = service.min_duration_minutes
            
            # Проверяем, что продолжительность соответствует шагу
            if duration < min_duration:
                await message.answer(
                    f"❌ <b>Минимальная продолжительность: {min_duration} мин.</b>\n\n"
                    f"Пожалуйста, введите продолжительность не менее {min_duration} минут.",
                    parse_mode="HTML"
                )
                return
            
            # Проверяем, что продолжительность кратна шагу
            if (duration - min_duration) % step != 0:
                nearest_valid = min_duration + ((duration - min_duration) // step) * step
                await message.answer(
                    f"❌ <b>Продолжительность должна быть кратной шагу ({step} мин.)</b>\n\n"
                    f"Доступные значения: {min_duration}, {min_duration + step}, {min_duration + step * 2}...\n"
                    f"Ближайшее корректное значение: {nearest_valid} мин.",
                    parse_mode="HTML"
                )
                return
    
    # Сохраняем продолжительность в состоянии
    booking_data = data.get('booking_data', {})
    booking_data['duration'] = duration
    # Сохраняем service_name если его еще нет в booking_data
    if 'service_name' not in booking_data:
        booking_data['service_name'] = data.get('service_name', '')
    await state.update_data(booking_data=booking_data)
    
    # Возвращаемся к форме бронирования
    await state.set_state(BookingStates.filling_form)
    
    # Получаем service_id из состояния
    if service_id:
        # Показываем форму бронирования как новое сообщение
        data = await state.get_data()
        booking_data = data.get('booking_data', {})
        service_name = booking_data.get('service_name') or data.get('service_name', '')
        
        text = f"📝 <b>Бронирование услуги: {service_name}</b>\n\n"
        text += "📋 <b>Заполните данные для бронирования:</b>\n\n"
        
        # Обязательные поля
        text += f"✅ <b>Дата:</b> {booking_data.get('date', 'Не выбрано')}\n"
        text += f"✅ <b>Время:</b> {booking_data.get('time', 'Не выбрано')}\n"
        text += f"✅ <b>Имя:</b> {booking_data.get('name', 'Не указано')}\n"
        text += f"✅ <b>Номер телефона:</b> {booking_data.get('phone', 'Не указан')}\n"
        text += f"✅ <b>Количество гостей:</b> {booking_data.get('guests_count', 'Не указано')}\n"
        
        # Необязательные поля
        text += f"✅ <b>Продолжительность:</b> {booking_data.get('duration', 60)} мин.\n"
        text += f"➕ <b>Доп. услуги:</b> {', '.join(booking_data.get('extras', [])) if booking_data.get('extras') else 'Нет'}\n"
        text += f"📧 <b>E-mail:</b> {booking_data.get('email', 'Не указан')}\n\n"
        
        text += "Выберите параметр для заполнения:"
        
        await message.answer(
            text,
            reply_markup=get_booking_form_keyboard(service_id, booking_data),
            parse_mode="HTML"
        )

async def start_email_input(callback: CallbackQuery, state: FSMContext):
    """Начало ввода email"""
    parts = callback.data.split("_")
    service_id = int(parts[2])
    
    await state.set_state(BookingStates.entering_email)
    await callback.message.edit_text(
        "📧 <b>Введите ваш e-mail (необязательно):</b>\n\n"
        "E-mail нужен для отправки подтверждения бронирования.\n"
        "Например: example@mail.ru\n\n"
        "Или отправьте /skip чтобы пропустить это поле.",
        parse_mode="HTML"
    )

async def process_email_input(message: Message, state: FSMContext):
    """Обработка введенного email"""
    email_text = message.text.strip()
    
    # Если пользователь хочет пропустить
    if email_text.lower() in ['/skip', '/пропустить', 'пропустить', 'skip']:
        email = None
    else:
        # Простая проверка формата email
        import re
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(email_pattern, email_text):
            await message.answer(
                "❌ <b>Неверный формат e-mail</b>\n\n"
                "Пожалуйста, введите корректный e-mail адрес.\n"
                "Например: example@mail.ru\n\n"
                "Или отправьте /skip чтобы пропустить это поле.",
                parse_mode="HTML"
            )
            return
        email = email_text
    
    # Сохраняем email в состоянии
    data = await state.get_data()
    booking_data = data.get('booking_data', {})
    booking_data['email'] = email
    # Сохраняем service_name если его еще нет в booking_data
    if 'service_name' not in booking_data:
        booking_data['service_name'] = data.get('service_name', '')
    await state.update_data(booking_data=booking_data)
    
    # Возвращаемся к форме бронирования
    await state.set_state(BookingStates.filling_form)
    
    # Получаем service_id из состояния
    service_id = data.get('service_id')
    if service_id:
        # Показываем форму бронирования как новое сообщение
        data = await state.get_data()
        booking_data = data.get('booking_data', {})
        service_name = booking_data.get('service_name') or data.get('service_name', '')
        
        text = f"📝 <b>Бронирование услуги: {service_name}</b>\n\n"
        text += "📋 <b>Заполните данные для бронирования:</b>\n\n"
        
        # Обязательные поля
        text += f"✅ <b>Дата:</b> {booking_data.get('date', 'Не выбрано')}\n"
        text += f"✅ <b>Время:</b> {booking_data.get('time', 'Не выбрано')}\n"
        text += f"✅ <b>Имя:</b> {booking_data.get('name', 'Не указано')}\n"
        text += f"✅ <b>Номер телефона:</b> {booking_data.get('phone', 'Не указан')}\n"
        text += f"✅ <b>Количество гостей:</b> {booking_data.get('guests_count', 'Не указано')}\n"
        
        # Необязательные поля
        text += f"✅ <b>Продолжительность:</b> {booking_data.get('duration', 60)} мин.\n"
        text += f"➕ <b>Доп. услуги:</b> {', '.join(booking_data.get('extras', [])) if booking_data.get('extras') else 'Нет'}\n"
        email_display = booking_data.get('email', 'Не указан')
        if email_display:
            text += f"✅ <b>E-mail:</b> {email_display}\n"
        else:
            text += f"📧 <b>E-mail:</b> {email_display}\n"
        text += "\n"
        
        text += "Выберите параметр для заполнения:"
        
        await message.answer(
            text,
            reply_markup=get_booking_form_keyboard(service_id, booking_data),
            parse_mode="HTML"
        )

async def start_extras_input(callback: CallbackQuery, state: FSMContext):
    """Начало выбора дополнительных услуг"""
    # Получаем service_id из callback или из state
    parts = callback.data.split("_")
    data = await state.get_data()
    
    # Пытаемся извлечь service_id из callback
    if len(parts) >= 3 and parts[2].isdigit():
        service_id = int(parts[2])
    elif callback.data.startswith("booking_toggle_extra_"):
        # Формат: booking_toggle_extra_{service_id}_{key}_{action}
        service_id = int(parts[3])
    else:
        # Если не можем извлечь из callback, берем из state
        service_id = data.get('service_id')
        if not service_id:
            await callback.answer("Ошибка: ID услуги не найден", show_alert=True)
            return
    
    booking_data = data.get('booking_data', {})
    current_extras = booking_data.get('extras', [])
    
    # Список доступных дополнительных услуг
    available_extras = {
        'photographer': '📸 Фотограф (+2000₽)',
        'makeuproom': '💄 Гримерка (1000₽/час)'
    }
    
    # Формируем текст с текущим выбором
    text = "➕ <b>Дополнительные услуги:</b>\n\n"
    text += "Выберите дополнительные услуги для вашей фотосессии:\n\n"
    
    for key, label in available_extras.items():
        status = "✅" if key in current_extras else "☐"
        text += f"{status} {label}\n"
    
    text += "\nНажмите на услугу, чтобы добавить/убрать её."
    
    # Создаем клавиатуру для выбора
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    
    keyboard = []
    for key, label in available_extras.items():
        is_selected = key in current_extras
        button_text = f"{'✅' if is_selected else '☐'} {label.split('(')[0].strip()}"
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
    """Переключение дополнительной услуги"""
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
    # Сохраняем service_name если его еще нет в booking_data
    if 'service_name' not in booking_data:
        booking_data['service_name'] = data.get('service_name', '')
    await state.update_data(booking_data=booking_data)
    
    # Обновляем сообщение
    await start_extras_input(callback, state)

async def extras_done(callback: CallbackQuery, state: FSMContext):
    """Завершение выбора дополнительных услуг"""
    parts = callback.data.split("_")
    service_id = int(parts[3])
    
    # Возвращаемся к форме бронирования
    await state.set_state(BookingStates.filling_form)
    await show_booking_form(callback, state)

async def back_from_extras(callback: CallbackQuery, state: FSMContext):
    """Возврат из выбора дополнительных услуг"""
    parts = callback.data.split("_")
    service_id = int(parts[3])  # booking_extras_back_{service_id}
    
    # Возвращаемся к форме бронирования
    await state.set_state(BookingStates.filling_form)
    await show_booking_form(callback, state)

async def confirm_booking(callback: CallbackQuery, state: FSMContext):
    """Подтверждение бронирования"""
    parts = callback.data.split("_")
    service_id = int(parts[2])
    
    # Получаем данные из состояния
    data = await state.get_data()
    booking_data = data.get('booking_data', {})
    # Получаем service_name из booking_data или из state
    service_name = booking_data.get('service_name') or data.get('service_name', '')
    
    # Проверяем, что все обязательные поля заполнены
    required_fields = ['date', 'time', 'name', 'phone', 'guests_count']
    missing_fields = []
    
    for field in required_fields:
        if not booking_data.get(field):
            missing_fields.append(field)
    
    if missing_fields:
        field_names = {
            'date': 'Дата',
            'time': 'Время', 
            'name': 'Имя',
            'phone': 'Номер телефона',
            'guests_count': 'Количество гостей'
        }
        
        missing_names = [field_names[field] for field in missing_fields]
        
        await callback.answer(
            f"❌ <b>Не все поля заполнены</b>\n\n"
            f"Заполните: {', '.join(missing_names)}",
            show_alert=True
        )
        return
    
    # Формируем selected_datetime для дальнейшего использования
    selected_date = datetime.strptime(booking_data['date'], "%Y-%m-%d").date()
    selected_time_str = booking_data['time'].split(' - ')[0]  # Берем время начала
    selected_time = datetime.strptime(selected_time_str, "%H:%M").time()
    selected_datetime = datetime.combine(selected_date, selected_time)
    
    # Финальная проверка доступности времени в Google Calendar
    if CALENDAR_AVAILABLE and GoogleCalendarService:
        try:
            calendar_service = GoogleCalendarService()
            
            # Получаем доступные слоты на выбранную дату
            available_slots = await calendar_service.get_free_slots(
                date=selected_date,
                duration_minutes=60
            )
            
            # Приводим к UTC для сравнения
            selected_datetime_utc = selected_datetime.replace(tzinfo=None)
            
            is_time_available = False
            for slot in available_slots:
                slot_start = slot['start'].replace(tzinfo=None) if slot['start'].tzinfo else slot['start']
                slot_end = slot['end'].replace(tzinfo=None) if slot['end'].tzinfo else slot['end']
                
                if slot_start <= selected_datetime_utc < slot_end:
                    is_time_available = True
                    break
            
            if not is_time_available:
                await callback.answer(
                    "❌ <b>Время больше не доступно</b>\n\n"
                    "К сожалению, выбранное время уже занято. "
                    "Пожалуйста, выберите другое время.",
                    show_alert=True
                )
                return
        except Exception as e:
            print(f"Ошибка проверки доступности времени: {e}")
            await callback.answer(
                "❌ <b>Ошибка проверки доступности</b>\n\n"
                "Попробуйте позже или выберите другое время.",
                show_alert=True
            )
            return
    
    # Создаем событие в Google Calendar
    if CALENDAR_AVAILABLE and GoogleCalendarService:
        print(f"[CALENDAR] Попытка создания события в календаре для {booking_data['name']}")
        try:
            # Формируем данные для события (используем уже определенные переменные)
            event_start = selected_datetime
            # Используем сохраненную продолжительность или по умолчанию 60 минут
            duration_minutes = booking_data.get('duration', 60)
            event_end = event_start + timedelta(minutes=duration_minutes)
            
            print(f"[CALENDAR] Создание события: {event_start} - {event_end}")
            
            # Создаем описание события
            event_description = f"""
<b>Кто забронировал</b>
{booking_data['name']}
email: {booking_data.get('email', 'не указан')}
{booking_data['phone']}

<b>Какой зал вы хотите забронировать?</b>
{service_name}

<b>Какое количество гостейпланируется, включая фотографа?</b>
{booking_data['guests_count']}

<b>Нужна ли гримерная за час до съемки?</b>
{booking_data.get('makeuproom', 'Не указано')}

<b>Нужен ли фотограф?</b> 
{booking_data.get('need_photographer', 'Не указано')}

<b><u>ВНИМАНИЕ</u></b> Автоматически на вашу электронную почту приходит подтверждение о <b><u>предварительном бронировании времени</u></b><u>.</u> Вам нужно:

<ul><li>дождаться информации о предоплате</li><li>отправить нам скриншот оплаты в течение 24-х часов</li><li>получить от нас подтверждение, что желаемая дата и время забронировано.</li></ul>

Бронируя фотостудию, Вы соглашаетесь с <a href="https://www.google.com/url?q=https%3A%2F%2Fvk.com%2Fpages%3Fhash%3Ddd2aea6878aabba105%26oid%3D-174809315%26p%3D%25D0%259F%25D0%25A0%25D0%2590%25D0%2592%25D0%2598%25D0%259B%25D0%2590_%25D0%2590%25D0%25A0%25D0%2595%25D0%259D%25D0%2594%25D0%25AB_%25D0%25A4%25D0%259E%25D0%25A2%25D0%259E%25D0%25A1%25D0%25A2%25D0%25A3%25D0%2594%25D0%2598%25D0%2598&amp;sa=D&amp;source=calendar&amp;ust=1762503000000000&amp;usg=AOvVaw0LR6y1Ukh_SRdIeJXIrHOT" target="_blank" data-link-id="34" rel="noopener noreferrer">Правилами аренды фотостудии</a>
            """.strip()
            
            # Создаем событие в календаре
            calendar_service = GoogleCalendarService()
            print("[CALENDAR] Вызов calendar_service.create_event...")
            result = await calendar_service.create_event(
                title=f"Фотосессия: {service_name}",
                description=event_description,
                start_time=event_start,
                end_time=event_end
            )
            print(f"[CALENDAR] Событие успешно создано в календаре: {result.get('htmlLink', 'N/A')}")
            
        except Exception as e:
            import traceback
            print(f"[ERROR] Ошибка создания события в календаре: {e}")
            print(f"[ERROR] Детали ошибки:\n{traceback.format_exc()}")
            # Не останавливаем процесс бронирования, если календарь недоступен
    else:
        print(f"[WARNING] Календарь недоступен. CALENDAR_AVAILABLE={CALENDAR_AVAILABLE}, GoogleCalendarService={GoogleCalendarService}")
    
    # Сохраняем бронирование в базу данных
    try:
        from database import client_repo, booking_repo
        
        # Получаем telegram_id из callback
        telegram_id = callback.from_user.id
        
        # Создаем или находим клиента по telegram_id
        client = await client_repo.get_by_telegram_id(telegram_id)
        
        # Форматируем номер телефона в формат 10 цифр (убираем +7)
        phone_clean = booking_data['phone'].replace('+7 ', '').replace(' ', '').replace('-', '')
        if len(phone_clean) == 11 and phone_clean.startswith('7'):
            phone_clean = phone_clean[1:]  # Убираем первую 7
        
        if not client:
            # Создаем нового клиента
            from database.models import Client
            new_client = Client(
                telegram_id=telegram_id,
                name=booking_data['name'],
                phone=phone_clean,
                email=booking_data.get('email')
            )
            client_id = await client_repo.create(new_client)
            # Получаем созданного клиента
            client = await client_repo.get_by_id(client_id)
        else:
            # Обновляем существующего клиента
            client.name = booking_data['name']
            client.phone = phone_clean
            if booking_data.get('email'):
                client.email = booking_data.get('email')
            await client_repo.update(client)
        
        # Создаем бронирование
        from database.models import Booking, BookingStatus
        # Рассчитываем num_durations на основе продолжительности и шага услуги
        service = await service_repo.get_by_id(service_id)
        duration_minutes = booking_data.get('duration', 60)
        if service:
            # Вычисляем количество шагов продолжительности
            num_durations = max(1, (duration_minutes - service.min_duration_minutes) // service.duration_step_minutes + 1)
        else:
            num_durations = 1  # Fallback
        
        booking = Booking(
            service_id=service_id,
            client_id=client.id,
            start_time=selected_datetime,  # Объединяем дату и время
            num_clients=booking_data['guests_count'],
            num_durations=num_durations,
            status=BookingStatus.CONFIRMED,
            all_price=0.0  # Пока без расчета цены
        )
        
        created_booking = await booking_repo.create(booking)
        
        # Отправляем подтверждение
        await callback.message.edit_text(
            f"✅ <b>Бронирование подтверждено!</b>\n\n"
            f"📅 <b>Дата:</b> {selected_date.strftime('%d.%m.%Y')}\n"
            f"🕒 <b>Время:</b> {booking_data['time']}\n"
            f"👤 <b>Клиент:</b> {booking_data['name']}\n"
            f"📱 <b>Телефон:</b> {booking_data['phone']}\n"
            f"👥 <b>Гостей:</b> {booking_data['guests_count']}\n"
            f"⏰ <b>Продолжительность:</b> {booking_data.get('duration', 60)} мин.\n\n"
            f"🎯 <b>Услуга:</b> {service_name}\n\n"
            f"📝 <b>Событие создано в календаре</b>\n"
            f"💾 <b>Данные сохранены в базе</b>\n\n"
            f"Спасибо за бронирование! Мы свяжемся с вами для подтверждения деталей.",
            reply_markup=get_main_menu_keyboard(),
            parse_mode="HTML"
        )
        
        # Очищаем состояние
        await state.clear()
        
    except Exception as e:
        print(f"Ошибка сохранения в БД: {e}")
        await callback.answer(
            "❌ <b>Ошибка сохранения данных</b>\n\n"
            "Бронирование не может быть завершено. "
            "Попробуйте позже или свяжитесь с нами.",
            show_alert=True
        )

async def cancel_booking(callback: CallbackQuery, state: FSMContext):
    """Отмена бронирования"""
    await state.clear()
    await callback.message.edit_text(
        "❌ <b>Бронирование отменено</b>\n\n"
        "Вы можете начать заново в любое время.",
        reply_markup=get_main_menu_keyboard(),
        parse_mode="HTML"
    )

def register_booking_handlers(dp: Dispatcher):
    """Регистрация обработчиков бронирования"""
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
    dp.callback_query.register(start_phone_input, F.data.startswith("booking_phone_"))
    dp.message.register(process_phone_input, BookingStates.entering_phone)
    dp.callback_query.register(start_guests_count_input, F.data.startswith("booking_guests_"))
    dp.message.register(process_guests_count_input, BookingStates.entering_guests_count)
    dp.callback_query.register(start_duration_input, F.data.startswith("booking_duration_"))
    dp.message.register(process_duration_input, BookingStates.entering_duration)
    dp.callback_query.register(start_email_input, F.data.startswith("booking_email_"))
    dp.message.register(process_email_input, BookingStates.entering_email)
    # Более специфичные обработчики extras должны быть зарегистрированы первыми
    dp.callback_query.register(toggle_extra_service, F.data.startswith("booking_toggle_extra_"))
    dp.callback_query.register(extras_done, F.data.startswith("booking_extras_done_"))
    dp.callback_query.register(back_from_extras, F.data.startswith("booking_extras_back_"))
    dp.callback_query.register(start_extras_input, F.data.startswith("booking_extras_"))
    dp.callback_query.register(confirm_booking, F.data.startswith("booking_confirm_"))
    dp.callback_query.register(cancel_booking, F.data.startswith("booking_cancel_"))
