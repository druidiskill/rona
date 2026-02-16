from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton
from typing import List
from database.models import Service, TimeSlot
from datetime import datetime, timedelta

def get_main_menu_keyboard(is_admin: bool = False) -> InlineKeyboardMarkup:
    """Главное меню"""
    keyboard = [
        [InlineKeyboardButton(text="📸 Услуги", callback_data="services")],
        [InlineKeyboardButton(text="📅 Мои бронирования", callback_data="my_bookings")],
        [InlineKeyboardButton(text="📞 Контакты", callback_data="contacts")],
        [InlineKeyboardButton(text="ℹ️ Помощь", callback_data="help")]
    ]
    
    if is_admin:
        keyboard.append([InlineKeyboardButton(text="🔧 Админ-панель", callback_data="admin_panel")])
    
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def get_services_keyboard(services: List[Service]) -> InlineKeyboardMarkup:
    """Клавиатура услуг"""
    keyboard = []
    for service in services:
        keyboard.append([
            InlineKeyboardButton(
                text=f"📸 {service.name} - {service.price_min}₽",
                callback_data=f"service_{service.id}"
            )
        ])
    keyboard.append([InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_main")])
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def get_service_details_keyboard(service_id: int) -> InlineKeyboardMarkup:
    """Клавиатура деталей услуги"""
    keyboard = [
        [InlineKeyboardButton(text="📅 Забронировать", callback_data=f"book_service_{service_id}")],
        [InlineKeyboardButton(text="📸 Фотографии", callback_data=f"photos_{service_id}")],
        [InlineKeyboardButton(text="🔙 Назад к услугам", callback_data="services")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def get_booking_form_keyboard(service_id: int, booking_data: dict = None) -> InlineKeyboardMarkup:
    """Клавиатура формы бронирования"""
    if booking_data is None:
        booking_data = {}
    
    # Проверяем, что service_id не None
    if service_id is None:
        raise ValueError("service_id не может быть None")
    
    # Определяем статус полей
    date_status = "✅" if booking_data.get('date') else "‼️"
    time_status = "✅" if booking_data.get('time') else "‼️"
    name_status = "✅" if booking_data.get('name') else "‼️"
    phone_status = "✅" if booking_data.get('phone') else "‼️"
    guests_status = "✅" if booking_data.get('guests_count') else "‼️"
    
    keyboard = [
        [InlineKeyboardButton(text=f"{date_status} Дата", callback_data=f"booking_date_{service_id}")],
        [InlineKeyboardButton(text=f"{time_status} Время", callback_data=f"booking_time_{service_id}")],
        [InlineKeyboardButton(text=f"{name_status} Имя", callback_data=f"booking_name_{service_id}")],
        [InlineKeyboardButton(text=f"{phone_status} Номер телефона", callback_data=f"booking_phone_{service_id}")],
        [InlineKeyboardButton(text=f"{guests_status} Кол-во гостей", callback_data=f"booking_guests_{service_id}")],
        [InlineKeyboardButton(text="⏰ Продолжительность", callback_data=f"booking_duration_{service_id}")],
        [InlineKeyboardButton(text="➕ Доп. услуги", callback_data=f"booking_extras_{service_id}")],
        [InlineKeyboardButton(text="📧 E-mail", callback_data=f"booking_email_{service_id}")],
        [InlineKeyboardButton(text="✅ Подтвердить бронирование", callback_data=f"booking_confirm_{service_id}")],
        [InlineKeyboardButton(text="❌ Отменить", callback_data=f"booking_cancel_{service_id}")],
        [InlineKeyboardButton(text="🔙 Назад к услуге", callback_data=f"service_{service_id}")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def get_date_selection_keyboard(service_id: int, week_offset: int = 0) -> InlineKeyboardMarkup:
    """Клавиатура выбора даты с перелистыванием"""
    keyboard = []
    
    # Вычисляем даты для текущей недели
    today = datetime.now().date()
    start_date = today + timedelta(days=week_offset * 7)
    
    # Показываем 7 дней
    for i in range(7):
        date = start_date + timedelta(days=i)
        day_name = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"][date.weekday()]
        date_str = date.strftime("%d.%m")
        
        # Выделяем сегодняшний день
        if date == today:
            text = f"📅 {day_name} {date_str} (сегодня)"
        else:
            text = f"📅 {day_name} {date_str}"
        
        keyboard.append([
            InlineKeyboardButton(
                text=text,
                callback_data=f"select_date_{service_id}_{date.strftime('%Y-%m-%d')}"
            )
        ])
    
    # Кнопки перелистывания
    navigation_row = []
    if week_offset > 0:
        navigation_row.append(InlineKeyboardButton(
            text="⬅️ Предыдущая неделя", 
            callback_data=f"date_prev_week_{service_id}_{week_offset-1}"
        ))
    
    navigation_row.append(InlineKeyboardButton(
        text="➡️ Следующая неделя", 
        callback_data=f"date_next_week_{service_id}_{week_offset+1}"
    ))
    
    if navigation_row:
        keyboard.append(navigation_row)
    
    # Кнопка "Назад"
    keyboard.append([InlineKeyboardButton(text="🔙 Назад", callback_data=f"booking_back_from_date_{service_id}")])
    
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def get_time_selection_keyboard(service_id: int, time_slots: list, selected_date: str = None) -> InlineKeyboardMarkup:
    """Клавиатура выбора времени с перелистыванием дат"""
    keyboard = []
    
    # Показываем временные слоты (максимум 12 для полного дня)
    for i, slot in enumerate(time_slots[:12]):  # Показываем до 12 слотов (9:00-21:00)
        start_time = slot['start_time']
        end_time = slot['end_time']
        is_available = slot['is_available']
        
        time_str = f"{start_time.strftime('%H:%M')} - {end_time.strftime('%H:%M')}"
        status = "✅" if is_available else "❌"
        
        keyboard.append([
            InlineKeyboardButton(
                text=f"{status} {time_str}",
                callback_data=f"select_time_{service_id}_{i}" if is_available else "unavailable"
            )
        ])
    
    # Кнопки перелистывания дат
    if selected_date:
        selected_date_obj = datetime.strptime(selected_date, "%Y-%m-%d").date()
        prev_date = selected_date_obj - timedelta(days=1)
        next_date = selected_date_obj + timedelta(days=1)
        
        navigation_row = [
            InlineKeyboardButton(
                text=f"⬅️ {prev_date.strftime('%d.%m')}", 
                callback_data=f"time_prev_date_{service_id}_{prev_date.strftime('%Y-%m-%d')}"
            ),
            InlineKeyboardButton(
                text=f"➡️ {next_date.strftime('%d.%m')}", 
                callback_data=f"time_next_date_{service_id}_{next_date.strftime('%Y-%m-%d')}"
            )
        ]
        keyboard.append(navigation_row)
    
    # Кнопка "Назад"
    keyboard.append([InlineKeyboardButton(text="🔙 Назад", callback_data=f"booking_back_from_time_{service_id}")])
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def get_duration_selection_keyboard(service_id: int, min_duration_minutes: int = 60) -> InlineKeyboardMarkup:
    """Клавиатура выбора продолжительности (от минимальной длительности услуги до 8 часов + весь день)."""
    min_duration = int(min_duration_minutes or 60)
    if min_duration < 60:
        min_duration = 60
    if min_duration % 60 != 0:
        min_duration = ((min_duration // 60) + 1) * 60

    duration_values = [minutes for minutes in range(min_duration, 481, 60)]
    keyboard: list[list[InlineKeyboardButton]] = []

    for i in range(0, len(duration_values), 2):
        row: list[InlineKeyboardButton] = []
        for minutes in duration_values[i:i + 2]:
            hours = minutes // 60
            hour_label = "час" if hours == 1 else ("часа" if 2 <= hours <= 4 else "часов")
            row.append(
                InlineKeyboardButton(
                    text=f"{hours} {hour_label}",
                    callback_data=f"booking_set_duration_{service_id}_{minutes}",
                )
            )
        keyboard.append(row)

    keyboard.append([InlineKeyboardButton(text="Весь день", callback_data=f"booking_set_duration_{service_id}_720")])
    keyboard.append([InlineKeyboardButton(text="🔙 Назад", callback_data=f"service_{service_id}")])
    return InlineKeyboardMarkup(inline_keyboard=keyboard)










def get_admin_keyboard() -> InlineKeyboardMarkup:
    """Админская клавиатура"""
    keyboard = [
        [InlineKeyboardButton(text="📅 Бронирования", callback_data="admin_bookings")],
        [InlineKeyboardButton(text="📸 Управление услугами", callback_data="admin_services")],
        [InlineKeyboardButton(text="👥 Клиенты", callback_data="admin_clients")],
        [InlineKeyboardButton(text="👨‍💼 Администраторы", callback_data="admin_admins")],
        [InlineKeyboardButton(text="🔙 Главное меню", callback_data="back_to_main")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def get_services_management_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура управления услугами"""
    keyboard = [
        [InlineKeyboardButton(text="➕ Добавить услугу", callback_data="add_service_new")],
        [InlineKeyboardButton(text="✏️ Редактировать услугу", callback_data="edit_service")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="admin_panel")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def get_support_menu_keyboard(is_admin: bool = False) -> InlineKeyboardMarkup:
    """Главное меню с кнопкой завершения диалога поддержки"""
    keyboard = get_main_menu_keyboard(is_admin).inline_keyboard
    keyboard.append([InlineKeyboardButton(text="✅ Закончить диалог", callback_data="support_end")])
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def get_bookings_management_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура управления бронированиями"""
    keyboard = [
        [InlineKeyboardButton(text="📅 Сегодня", callback_data="bookings_today")],
        [InlineKeyboardButton(text="📅 Завтра", callback_data="bookings_tomorrow")],
        [InlineKeyboardButton(text="📅 Неделя", callback_data="bookings_week")],
        [InlineKeyboardButton(text="🔍 Поиск", callback_data="search_bookings")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="admin_panel")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def get_booking_actions_keyboard(booking_id: int) -> InlineKeyboardMarkup:
    """Клавиатура действий с бронированием"""
    keyboard = [
        [InlineKeyboardButton(text="✅ Подтвердить", callback_data=f"confirm_booking_{booking_id}")],
        [InlineKeyboardButton(text="❌ Отменить", callback_data=f"cancel_booking_{booking_id}")],
        [InlineKeyboardButton(text="✏️ Редактировать", callback_data=f"edit_booking_{booking_id}")],
        [InlineKeyboardButton(text="📞 Связаться", callback_data=f"contact_client_{booking_id}")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="admin_bookings")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def get_services_list_keyboard(services: List[Service]) -> InlineKeyboardMarkup:
    """Клавиатура списка услуг для редактирования"""
    keyboard = []
    for service in services:
        keyboard.append([
            InlineKeyboardButton(
                text=f"📸 {service.name}",
                callback_data=f"edit_service_{service.id}"
            )
        ])
    keyboard.append([InlineKeyboardButton(text="🔙 Назад", callback_data="admin_services")])
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def get_service_edit_keyboard(service_id: int) -> InlineKeyboardMarkup:
    """Клавиатура редактирования услуги"""
    keyboard = [
        [InlineKeyboardButton(text="🔧 Редактировать", callback_data=f"edit_service_new_{service_id}")],
        [InlineKeyboardButton(text="🗑️ Деактивировать", callback_data=f"delete_service_{service_id}")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="admin_services")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def get_contacts_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура контактов"""
    keyboard = [
        [InlineKeyboardButton(text="📧 Email", url="mailto:rona.photostudio.petergof@gmail.com")],
        [InlineKeyboardButton(text="🌐 Сайт", url="https://innasuvorova.ru/rona_photostudio")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_main")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def get_my_bookings_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура моих бронирований"""
    keyboard = [
        [InlineKeyboardButton(text="📅 Активные", callback_data="active_bookings")],
        [InlineKeyboardButton(text="📅 История", callback_data="booking_history")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_main")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def _has_photographer_extra(event: dict) -> bool:
    """Определяет, выбрана ли доп. услуга фотографа по описанию события."""
    description = (event.get("description") or "").lower()
    if not description:
        return False
    return (
        "нужен ли фотограф?" in description and "да" in description
    ) or ("дополнительные услуги" in description and "фотограф" in description)


def _display_summary_for_list_button(event: dict) -> str:
    """
    Для списков бронирований убирает префикс 'Фотосессия:',
    если услуга фотографа не выбрана.
    """
    summary = (event.get("summary") or "Без названия").strip()
    prefix = "Фотосессия:"
    if summary.startswith(prefix) and not _has_photographer_extra(event):
        cleaned = summary[len(prefix):].strip()
        return cleaned or "Без названия"
    return summary


def get_admin_future_bookings_keyboard(events: list[dict]) -> InlineKeyboardMarkup:
    """Клавиатура списка будущих бронирований для админа."""
    keyboard = []
    for event in events:
        event_id = event.get("id")
        start = event.get("start")
        summary = _display_summary_for_list_button(event)
        if not event_id or not start:
            continue
        button_text = f"🕐 {start.strftime('%d.%m %H:%M')} — {summary}"
        keyboard.append([
            InlineKeyboardButton(
                text=button_text[:64],
                callback_data=f"admin_booking_open_{event_id}"
            )
        ])

    keyboard.append([InlineKeyboardButton(text="🔙 Назад", callback_data="admin_panel")])
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def get_admin_booking_detail_keyboard(
    telegram_user_id: str | None = None,
    telegram_username: str | None = None
) -> InlineKeyboardMarkup:
    """Клавиатура карточки бронирования для админа."""
    keyboard = []
    if telegram_user_id:
        keyboard.append([InlineKeyboardButton(text="💬 Связаться", callback_data=f"support_reply_{telegram_user_id}")])
    elif telegram_username:
        keyboard.append([InlineKeyboardButton(text="💬 Связаться", callback_data=f"support_reply_username_{telegram_username}")])

    keyboard.extend([
        [InlineKeyboardButton(text="🔙 К списку бронирований", callback_data="admin_bookings")],
        [InlineKeyboardButton(text="🔙 В админ-панель", callback_data="admin_panel")]
    ])
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def get_active_bookings_list_keyboard(events: list[dict]) -> InlineKeyboardMarkup:
    """Клавиатура списка активных бронирований пользователя."""
    keyboard = []
    for event in events:
        event_id = event.get("id")
        start = event.get("start")
        summary = _display_summary_for_list_button(event)
        if not event_id or not start:
            continue
        button_text = f"✏️ {start.strftime('%d.%m %H:%M')} — {summary}"
        keyboard.append([
            InlineKeyboardButton(
                text=button_text[:64],
                callback_data=f"active_booking_open_{event_id}"
            )
        ])

    keyboard.append([InlineKeyboardButton(text="🔙 Назад", callback_data="my_bookings")])
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def get_active_booking_actions_keyboard(event_id: str) -> InlineKeyboardMarkup:
    """Клавиатура действий по активной брони пользователя."""
    keyboard = [
        [InlineKeyboardButton(text="❌ Отменить бронирование", callback_data=f"active_booking_cancel_{event_id}")],
        [InlineKeyboardButton(text="🔙 К активным", callback_data="active_bookings")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def get_clients_management_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура управления клиентами"""
    keyboard = [
        [InlineKeyboardButton(text="👥 Все клиенты", callback_data="all_clients")],
        [InlineKeyboardButton(text="🔍 Поиск клиента", callback_data="search_client")],
        [InlineKeyboardButton(text="📊 Статистика", callback_data="clients_stats")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="admin_panel")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def get_admins_management_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура управления администраторами"""
    keyboard = [
        [InlineKeyboardButton(text="👨‍💼 Список админов", callback_data="admins_list")],
        [InlineKeyboardButton(text="➕ Добавить админа", callback_data="add_admin")],
        [InlineKeyboardButton(text="🗑️ Удалить админа", callback_data="remove_admin")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="admin_panel")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def get_add_service_main_keyboard() -> InlineKeyboardMarkup:
    """Главная клавиатура добавления услуги"""
    keyboard = [
        [InlineKeyboardButton(text="📝 Название", callback_data="add_service_name")],
        [InlineKeyboardButton(text="📄 Описание", callback_data="add_service_description")],
        [InlineKeyboardButton(text="💰 Цена", callback_data="add_service_price_menu")],
        [InlineKeyboardButton(text="👥 Макс. человек", callback_data="add_service_max_clients")],
        [InlineKeyboardButton(text="🔧 Доп. услуги", callback_data="add_service_extras")],
        [InlineKeyboardButton(text="⏰ Длительность", callback_data="add_service_duration")],
        [InlineKeyboardButton(text="📸 Фото", callback_data="add_service_photos")],
        [InlineKeyboardButton(text="✅ Создать услугу", callback_data="create_service_final")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="admin_services")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def get_add_service_price_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура настройки цен для новой услуги"""
    keyboard = [
        [InlineKeyboardButton(text="💰 Цена (будни)", callback_data="add_service_price_weekday")],
        [InlineKeyboardButton(text="💰 Цена (выходные)", callback_data="add_service_price_weekend")],
        [InlineKeyboardButton(text="👤 Цена за доп. человека (будни)", callback_data="add_service_price_extra_weekday")],
        [InlineKeyboardButton(text="👤 Цена за доп. человека (выходные)", callback_data="add_service_price_extra_weekend")],
        [InlineKeyboardButton(text="👥 Цена от 10 человек", callback_data="add_service_price_group")],
        [InlineKeyboardButton(text="🔙 Назад к услуге", callback_data="add_service_main")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def get_add_service_extras_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура дополнительных услуг"""
    keyboard = [
        [InlineKeyboardButton(text="📸 Фотограф", callback_data="add_service_photographer")],
        [InlineKeyboardButton(text="💄 Гримерка", callback_data="add_service_makeuproom")],
        [InlineKeyboardButton(text="🔙 Назад к услуге", callback_data="add_service_main")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def get_existing_services_keyboard(services: List[Service], selected_ids: List[int] = None) -> InlineKeyboardMarkup:
    """Клавиатура выбора существующих услуг как дополнительных"""
    if selected_ids is None:
        selected_ids = []
    
    keyboard = []
    for service in services:
        if service.is_active:
            # Показываем статус выбора
            status = "✅" if service.id in selected_ids else "⬜"
            keyboard.append([
                InlineKeyboardButton(
                    text=f"{status} {service.name} - {service.price_min}₽",
                    callback_data=f"select_extra_service_{service.id}"
                )
            ])
    
    keyboard.append([InlineKeyboardButton(text="✅ Готово", callback_data="extras_done")])
    keyboard.append([InlineKeyboardButton(text="🔙 Назад к услуге", callback_data="add_service_main")])
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def get_edit_service_main_keyboard():
    """Клавиатура для главного меню редактирования услуги"""
    keyboard = [
        [InlineKeyboardButton(text="📸 Название", callback_data="edit_service_name")],
        [InlineKeyboardButton(text="📝 Описание", callback_data="edit_service_description")],
        [InlineKeyboardButton(text="💰 Цена", callback_data="edit_service_price")],
        [InlineKeyboardButton(text="👥 Макс. человек", callback_data="edit_service_max_clients")],
        [InlineKeyboardButton(text="🔧 Доп. услуги", callback_data="edit_service_extras")],
        [InlineKeyboardButton(text="⏰ Длительность", callback_data="edit_service_duration")],
        [InlineKeyboardButton(text="📸 Фото", callback_data="edit_service_photos")],
        [InlineKeyboardButton(text="💾 Сохранить изменения", callback_data="save_edit_service")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_services_management")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def get_booking_keyboard(service_id: int) -> InlineKeyboardMarkup:
    """Клавиатура для бронирования услуги"""
    keyboard = [
        [InlineKeyboardButton(text="📅 Выбрать дату", callback_data=f"booking_date_{service_id}")],
        [InlineKeyboardButton(text="👥 Количество гостей", callback_data=f"booking_guests_{service_id}")],
        [InlineKeyboardButton(text="⏰ Продолжительность", callback_data=f"booking_duration_{service_id}")],
        [InlineKeyboardButton(text="📸 Фотограф", callback_data=f"booking_photographer_{service_id}")],
        [InlineKeyboardButton(text="💄 Гримерка", callback_data=f"booking_makeuproom_{service_id}")],
        [InlineKeyboardButton(text="✅ Подтвердить бронирование", callback_data=f"booking_confirm_{service_id}")],
        [InlineKeyboardButton(text="🔙 Назад к услуге", callback_data=f"service_{service_id}")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def get_back_to_service_keyboard(service_id: int, message_ids: str = ""):
    """Клавиатура для возврата к услуге из фотографий"""
    keyboard = [
        [InlineKeyboardButton(text="🔙 Назад к услуге", callback_data=f"back_to_service_{service_id}_{message_ids}")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)



