from aiogram import Dispatcher, F
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext
import re

from telegram_bot.keyboards import (
    get_admin_keyboard,
    get_main_menu_keyboard,
    get_services_management_keyboard,
    get_bookings_management_keyboard,
    get_admin_future_bookings_keyboard,
    get_admin_booking_detail_keyboard,
)
from telegram_bot.states import AdminStates
from database import admin_repo, service_repo, client_repo
from datetime import datetime, timedelta

# Опциональный импорт Google Calendar
try:
    from google_calendar.calendar_service import GoogleCalendarService
    CALENDAR_AVAILABLE = True
except Exception as e:
    GoogleCalendarService = None
    CALENDAR_AVAILABLE = False
    print(f"[WARNING] Google Calendar недоступен: {e}")


def _extract_booking_contact_details(description: str) -> dict:
    """Извлекает контактные данные клиента из описания события календаря."""
    text = re.sub(r"<[^>]+>", "", description or "")
    lines = [line.strip() for line in text.splitlines() if line.strip()]

    name = None
    for i, line in enumerate(lines):
        if line.lower() == "кто забронировал" and i + 1 < len(lines):
            name = lines[i + 1]
            break

    email_match = re.search(r"[\w.\-+%]+@[\w.\-]+\.\w+", text)
    phone_match = re.search(r"(\+?\d[\d\-\s\(\)]{8,}\d)", text)
    tg_id_match = re.search(r"Telegram ID:\s*(\d+)", text, flags=re.IGNORECASE)
    tg_link_match = re.search(r"https?://t\.me/([A-Za-z0-9_]{5,32})", text, flags=re.IGNORECASE)
    tg_username_match = re.search(r"(?:^|\s)@([A-Za-z0-9_]{5,32})(?:\s|$)", text)

    return {
        "name": name,
        "email": email_match.group(0) if email_match else None,
        "phone": phone_match.group(1) if phone_match else None,
        "telegram_id": tg_id_match.group(1) if tg_id_match else None,
        "telegram_username": (
            tg_link_match.group(1)
            if tg_link_match
            else (tg_username_match.group(1) if tg_username_match else None)
        ),
    }


def _normalize_phone(phone: str | None) -> str | None:
    """Нормализует телефон к формату 10 цифр для поиска в clients.phone."""
    if not phone:
        return None
    digits = "".join(ch for ch in str(phone) if ch.isdigit())
    if len(digits) == 11 and digits.startswith(("7", "8")):
        digits = digits[1:]
    if len(digits) == 10:
        return digits
    return None

async def admin_panel(callback: CallbackQuery, is_admin: bool, parse_mode: str = "HTML"):
    """Админ-панель"""
    if not is_admin:
        await callback.answer("У вас нет прав администратора", show_alert=True)
        return
    
    await callback.message.edit_text(
        "🔧 <b>Админ-панель</b>\n\n"
        "Выберите действие:",
        reply_markup=get_admin_keyboard(),
        parse_mode=parse_mode
    )

async def admin_stats(callback: CallbackQuery, is_admin: bool):
    """Статистика для админа"""
    if not is_admin:
        await callback.answer("У вас нет прав администратора", show_alert=True)
        return
    
    # Получаем статистику
    services = await service_repo.get_all_active()
    # Здесь можно добавить получение статистики бронирований
    
    stats_text = f"""📊 <b>Статистика студии</b>

📸 <b>Услуги:</b> {len(services)} активных
📅 <b>Бронирования сегодня:</b> [будет добавлено]
💰 <b>Выручка за месяц:</b> [будет добавлено]
👥 <b>Новых клиентов:</b> [будет добавлено]"""
    
    await callback.message.edit_text(
        stats_text,
        reply_markup=get_admin_keyboard(),
        parse_mode="HTML"
    )

async def admin_bookings(callback: CallbackQuery, is_admin: bool):
    """Управление бронированиями"""
    if not is_admin:
        await callback.answer("У вас нет прав администратора", show_alert=True)
        return

    if not CALENDAR_AVAILABLE or not GoogleCalendarService:
        await callback.message.edit_text(
            "📅 <b>Бронирования</b>\n\n"
            "Google Calendar недоступен. Проверьте настройки и токены.",
            reply_markup=get_admin_keyboard(),
            parse_mode="HTML"
        )
        return

    period_start = datetime.now()
    period_end = period_start + timedelta(days=365)
    try:
        calendar_service = GoogleCalendarService()
        events = await calendar_service.list_events(period_start, period_end, max_results=250)
    except Exception as e:
        print(f"Ошибка получения событий календаря: {e}")
        await callback.message.edit_text(
            "📅 <b>Бронирования</b>\n\n"
            "Не удалось получить данные из календаря.",
            reply_markup=get_admin_keyboard(),
            parse_mode="HTML"
        )
        return

    future_events = [event for event in events if event.get("start")]
    if not future_events:
        await callback.message.edit_text(
            "📅 <b>Бронирования</b>\n\n"
            "Будущих бронирований нет.",
            reply_markup=get_admin_keyboard(),
            parse_mode="HTML"
        )
        return

    await callback.message.edit_text(
        "📅 <b>Будущие бронирования</b>\n\n"
        "Выберите бронирование для просмотра деталей:",
        reply_markup=get_admin_future_bookings_keyboard(future_events),
        parse_mode="HTML"
    )


async def admin_booking_open(callback: CallbackQuery, is_admin: bool):
    """Карточка выбранного бронирования для админа."""
    if not is_admin:
        await callback.answer("У вас нет прав администратора", show_alert=True)
        return

    event_id = callback.data.replace("admin_booking_open_", "", 1)
    if not CALENDAR_AVAILABLE or not GoogleCalendarService:
        await callback.answer("Google Calendar недоступен", show_alert=True)
        return

    try:
        calendar_service = GoogleCalendarService()
        raw_event = calendar_service._service.events().get(
            calendarId=calendar_service.calendar_id,
            eventId=event_id
        ).execute()
    except Exception as e:
        print(f"Ошибка получения события {event_id}: {e}")
        await callback.answer("Не удалось получить бронирование", show_alert=True)
        return

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

    contact = _extract_booking_contact_details(description)

    text = "📋 <b>Информация о бронировании</b>\n\n"
    text += f"🎯 <b>Услуга:</b> {summary}\n"
    if start_dt:
        text += f"📅 <b>Дата:</b> {start_dt.strftime('%d.%m.%Y')}\n"
        text += f"🕒 <b>Время:</b> {start_dt.strftime('%H:%M')}"
        if end_dt:
            text += f" - {end_dt.strftime('%H:%M')}"
        text += "\n"

    # Для режима чата нужен numeric user_id.
    chat_target_user_id = contact.get("telegram_id")
    if not chat_target_user_id:
        # Фолбек: ищем клиента в БД по телефону/email и берем его telegram_id.
        try:
            phone_norm = _normalize_phone(contact.get("phone"))
            db_client = None
            if phone_norm:
                db_client = await client_repo.get_by_phone(phone_norm)
            if (not db_client) and contact.get("email"):
                clients = await client_repo.get_all() if hasattr(client_repo, "get_all") else []
                email_lc = contact["email"].strip().lower()
                for c in clients:
                    if c.email and c.email.strip().lower() == email_lc:
                        db_client = c
                        break
            if db_client and db_client.telegram_id:
                chat_target_user_id = str(db_client.telegram_id)
        except Exception as e:
            print(f"Ошибка поиска клиента в БД для внутреннего чата: {e}")

    text += "\n📞 <b>Данные для связи</b>\n"
    text += f"👤 <b>Клиент:</b> {contact['name'] or 'Не указан'}\n"
    text += f"📱 <b>Телефон:</b> {contact['phone'] or 'Не указан'}\n"
    text += f"📧 <b>Email:</b> {contact['email'] or 'Не указан'}\n"
    if not chat_target_user_id:
        text += "⚠️ <i>Для этого бронирования внутренний чат недоступен: не найден Telegram ID клиента.</i>\n"

    await callback.message.edit_text(
        text,
        reply_markup=get_admin_booking_detail_keyboard(chat_target_user_id, None),
        parse_mode="HTML"
    )

async def admin_services(callback: CallbackQuery, is_admin: bool):
    """Управление услугами"""
    if not is_admin:
        await callback.answer("У вас нет прав администратора", show_alert=True)
        return
    
    services = await service_repo.get_all_active()
    
    services_text = "📸 <b>Управление услугами</b>\n\n"
    for service in services:
        services_text += f"📸 <b>{service.name}</b>\n"
        services_text += f"💰 {service.price_min}₽ - {service.price_min_weekend}₽\n"
        services_text += f"👥 До {service.max_num_clients} чел.\n"
        services_text += f"⏰ {service.min_duration_minutes} мин.\n"
        services_text += f"📊 {'✅ Активна' if service.is_active else '❌ Неактивна'}\n\n"
    
    await callback.message.edit_text(
        services_text,
        reply_markup=get_services_management_keyboard(),
        parse_mode="HTML"
    )

async def admin_clients(callback: CallbackQuery, is_admin: bool):
    """Управление клиентами"""
    if not is_admin:
        await callback.answer("У вас нет прав администратора", show_alert=True)
        return
    
    # Получаем статистику клиентов
    from database import client_repo
    clients = await client_repo.get_all() if hasattr(client_repo, 'get_all') else []
    
    clients_text = "👥 <b>Управление клиентами</b>\n\n"
    clients_text += f"📊 Всего клиентов: {len(clients)}\n\n"
    
    if clients:
        clients_text += "📋 <b>Последние клиенты:</b>\n"
        for client in clients[:5]:  # Показываем последних 5
            clients_text += f"👤 {client.name}\n"
            if client.telegram_id:
                telegram_label = "Не указан"
                try:
                    chat = await callback.bot.get_chat(client.telegram_id)
                    if chat.username:
                        telegram_label = f"@{chat.username}"
                except Exception as e:
                    print(f"Не удалось получить username для client.telegram_id={client.telegram_id}: {e}")
                clients_text += f"   Telegram: {telegram_label}\n"
            if client.phone:
                clients_text += f"   📞 {client.phone}\n"
            clients_text += "\n"
    else:
        clients_text += "Клиентов пока нет."
    
    await callback.message.edit_text(
        clients_text,
        reply_markup=get_admin_keyboard(),
        parse_mode="HTML"
    )

async def admin_admins(callback: CallbackQuery, is_admin: bool):
    """Управление администраторами"""
    if not is_admin:
        await callback.answer("У вас нет прав администратора", show_alert=True)
        return
    
    admins = await admin_repo.get_all()
    
    admins_text = "👨‍💼 <b>Управление администраторами</b>\n\n"
    for admin in admins:
        status = "✅ Активен" if admin.is_active else "❌ Неактивен"
        telegram_label = "Не указан"
        if admin.telegram_id:
            try:
                chat = await callback.bot.get_chat(admin.telegram_id)
                if chat.username:
                    telegram_label = f"@{chat.username}"
            except Exception as e:
                print(f"Не удалось получить username для admin.telegram_id={admin.telegram_id}: {e}")

        admins_text += f"👤 ID: {admin.id}\n"
        admins_text += f"📱 Telegram: {telegram_label}\n"
        admins_text += f"📧 VK: {admin.vk_id or 'Не указан'}\n"
        admins_text += f"📊 Статус: {status}\n\n"
    
    await callback.message.edit_text(
        admins_text,
        reply_markup=get_admin_keyboard(),
        parse_mode="HTML"
    )

async def bookings_today(callback: CallbackQuery, is_admin: bool):
    """Бронирования на сегодня"""
    if not is_admin:
        await callback.answer("У вас нет прав администратора", show_alert=True)
        return
    
    today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    tomorrow = today + timedelta(days=1)
    
    if not CALENDAR_AVAILABLE or not GoogleCalendarService:
        await callback.message.edit_text(
            "📅 <b>Бронирования на сегодня</b>\n\n"
            "Google Calendar недоступен. Проверьте настройки и токены.",
            reply_markup=get_bookings_management_keyboard(),
            parse_mode="HTML"
        )
        return

    try:
        calendar_service = GoogleCalendarService()
        events = await calendar_service.list_events(today, tomorrow)
    except Exception as e:
        print(f"Ошибка получения событий календаря: {e}")
        await callback.message.edit_text(
            "📅 <b>Бронирования на сегодня</b>\n\n"
            "Не удалось получить данные из календаря.",
            reply_markup=get_bookings_management_keyboard(),
            parse_mode="HTML"
        )
        return

    if not events:
        await callback.message.edit_text(
            "📅 <b>Бронирования на сегодня</b>\n\n"
            "На сегодня бронирований нет.",
            reply_markup=get_bookings_management_keyboard(),
            parse_mode="HTML"
        )
        return

    bookings_text = f"📅 <b>Бронирования на сегодня ({today.strftime('%d.%m.%Y')})</b>\n\n"
    for event in events:
        start = event.get("start")
        if not start:
            continue
        summary = event.get("summary", "Без названия")
        bookings_text += f"🕐 {start.strftime('%H:%M')} — {summary}\n\n"

    await callback.message.edit_text(
        bookings_text,
        reply_markup=get_bookings_management_keyboard(),
        parse_mode="HTML"
    )

async def bookings_tomorrow(callback: CallbackQuery, is_admin: bool):
    """Бронирования на завтра"""
    if not is_admin:
        await callback.answer("У вас нет прав администратора", show_alert=True)
        return
    
    tomorrow = (datetime.now() + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
    day_after = tomorrow + timedelta(days=1)
    
    if not CALENDAR_AVAILABLE or not GoogleCalendarService:
        await callback.message.edit_text(
            "📅 <b>Бронирования на завтра</b>\n\n"
            "Google Calendar недоступен. Проверьте настройки и токены.",
            reply_markup=get_bookings_management_keyboard(),
            parse_mode="HTML"
        )
        return

    try:
        calendar_service = GoogleCalendarService()
        events = await calendar_service.list_events(tomorrow, day_after)
    except Exception as e:
        print(f"Ошибка получения событий календаря: {e}")
        await callback.message.edit_text(
            "📅 <b>Бронирования на завтра</b>\n\n"
            "Не удалось получить данные из календаря.",
            reply_markup=get_bookings_management_keyboard(),
            parse_mode="HTML"
        )
        return

    if not events:
        await callback.message.edit_text(
            "📅 <b>Бронирования на завтра</b>\n\n"
            "На завтра бронирований нет.",
            reply_markup=get_bookings_management_keyboard(),
            parse_mode="HTML"
        )
        return

    bookings_text = f"📅 <b>Бронирования на завтра ({tomorrow.strftime('%d.%m.%Y')})</b>\n\n"
    for event in events:
        start = event.get("start")
        if not start:
            continue
        summary = event.get("summary", "Без названия")
        bookings_text += f"🕐 {start.strftime('%H:%M')} — {summary}\n\n"

    await callback.message.edit_text(
        bookings_text,
        reply_markup=get_bookings_management_keyboard(),
        parse_mode="HTML"
    )

async def bookings_week(callback: CallbackQuery, is_admin: bool):
    """Бронирования на неделю"""
    if not is_admin:
        await callback.answer("У вас нет прав администратора", show_alert=True)
        return

    today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    week_later = today + timedelta(days=7)

    if not CALENDAR_AVAILABLE or not GoogleCalendarService:
        await callback.message.edit_text(
            "📅 <b>Бронирования на неделю</b>\n\n"
            "Google Calendar недоступен. Проверьте настройки и токены.",
            reply_markup=get_bookings_management_keyboard(),
            parse_mode="HTML"
        )
        return

    try:
        calendar_service = GoogleCalendarService()
        events = await calendar_service.list_events(today, week_later, max_results=100)
    except Exception as e:
        print(f"Ошибка получения событий календаря: {e}")
        await callback.message.edit_text(
            "📅 <b>Бронирования на неделю</b>\n\n"
            "Не удалось получить данные из календаря.",
            reply_markup=get_bookings_management_keyboard(),
            parse_mode="HTML"
        )
        return

    if not events:
        await callback.message.edit_text(
            "📅 <b>Бронирования на неделю</b>\n\n"
            "На ближайшие 7 дней бронирований нет.",
            reply_markup=get_bookings_management_keyboard(),
            parse_mode="HTML"
        )
        return

    bookings_text = "📅 <b>Бронирования на неделю:</b>\n\n"
    for event in events:
        start = event.get("start")
        if not start:
            continue
        summary = event.get("summary", "Без названия")
        bookings_text += f"🕐 {start.strftime('%d.%m %H:%M')} — {summary}\n"

    await callback.message.edit_text(
        bookings_text,
        reply_markup=get_bookings_management_keyboard(),
        parse_mode="HTML"
    )

async def search_bookings(callback: CallbackQuery, state: FSMContext, is_admin: bool):
    """Запуск поиска бронирований по тексту"""
    if not is_admin:
        await callback.answer("У вас нет прав администратора", show_alert=True)
        return

    await state.set_state(AdminStates.waiting_for_booking_search_query)
    await callback.message.edit_text(
        "🔍 <b>Поиск бронирований</b>\n\n"
        "Введите текст для поиска (имя, телефон, услуга или часть описания).",
        reply_markup=get_bookings_management_keyboard(),
        parse_mode="HTML"
    )

async def process_search_bookings_query(message: Message, state: FSMContext, is_admin: bool):
    """Поиск бронирований по введенному тексту"""
    if not is_admin:
        await state.clear()
        await message.answer("У вас нет прав администратора")
        return

    query = (message.text or "").strip()
    if len(query) < 2:
        await message.answer("❌ Введите минимум 2 символа для поиска.")
        return

    if not CALENDAR_AVAILABLE or not GoogleCalendarService:
        await state.clear()
        await message.answer(
            "Google Calendar недоступен. Проверьте настройки и токены.",
            reply_markup=get_bookings_management_keyboard()
        )
        return

    now = datetime.now()
    period_start = now - timedelta(days=30)
    period_end = now + timedelta(days=180)

    try:
        calendar_service = GoogleCalendarService()
        events = await calendar_service.list_events(
            period_start,
            period_end,
            query=query,
            max_results=30
        )
    except Exception as e:
        print(f"Ошибка поиска событий календаря: {e}")
        await state.clear()
        await message.answer(
            "❌ Ошибка поиска в календаре. Попробуйте позже.",
            reply_markup=get_bookings_management_keyboard()
        )
        return

    if not events:
        await state.clear()
        await message.answer(
            f"🔍 По запросу <b>{query}</b> ничего не найдено.",
            reply_markup=get_bookings_management_keyboard(),
            parse_mode="HTML"
        )
        return

    result_text = f"🔍 <b>Результаты поиска: {query}</b>\n\n"
    for event in events:
        start = event.get("start")
        if not start:
            continue
        summary = event.get("summary", "Без названия")
        result_text += f"🕐 {start.strftime('%d.%m %H:%M')} — {summary}\n"

    await state.clear()
    await message.answer(
        result_text,
        reply_markup=get_bookings_management_keyboard(),
        parse_mode="HTML"
    )

async def admin_access_denied(message: Message, is_admin: bool):
    """Обработка доступа к админ-функциям"""
    if not is_admin:
        await message.answer(
            "🔒 <b>Доступ запрещен</b>\n\n"
            "У вас нет прав администратора.\n"
            "Обратитесь к администратору для получения доступа.",
            reply_markup=get_main_menu_keyboard()
        )

def register_admin_handlers(dp: Dispatcher):
    """Регистрация обработчиков админ-панели"""
    dp.callback_query.register(admin_panel, F.data == "admin_panel")
    dp.callback_query.register(admin_stats, F.data == "admin_stats")
    dp.callback_query.register(admin_bookings, F.data == "admin_bookings")
    dp.callback_query.register(admin_services, F.data == "admin_services")
    dp.callback_query.register(admin_clients, F.data == "admin_clients")
    dp.callback_query.register(admin_admins, F.data == "admin_admins")
    dp.callback_query.register(bookings_today, F.data == "bookings_today")
    dp.callback_query.register(bookings_tomorrow, F.data == "bookings_tomorrow")
    dp.callback_query.register(bookings_week, F.data == "bookings_week")
    dp.callback_query.register(search_bookings, F.data == "search_bookings")
    dp.callback_query.register(admin_booking_open, F.data.startswith("admin_booking_open_"))
    dp.message.register(process_search_bookings_query, AdminStates.waiting_for_booking_search_query)
