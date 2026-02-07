from aiogram import Dispatcher, F
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext

from telegram_bot.keyboards import get_admin_keyboard, get_main_menu_keyboard, get_services_management_keyboard, get_bookings_management_keyboard
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
            "📅 <b>Бронирования на неделю</b>\n\n"
            "Google Calendar недоступен. Проверьте настройки и токены.",
            reply_markup=get_admin_keyboard(),
            parse_mode="HTML"
        )
        return

    today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    week_later = today + timedelta(days=7)

    try:
        calendar_service = GoogleCalendarService()
        events = await calendar_service.list_events(today, week_later)
    except Exception as e:
        print(f"Ошибка получения событий календаря: {e}")
        await callback.message.edit_text(
            "📅 <b>Бронирования на неделю</b>\n\n"
            "Не удалось получить данные из календаря.",
            reply_markup=get_admin_keyboard(),
            parse_mode="HTML"
        )
        return

    if not events:
        await callback.message.edit_text(
            "📅 <b>Бронирования на неделю</b>\n\n"
            "Нет бронирований на ближайшие 7 дней.",
            reply_markup=get_admin_keyboard(),
            parse_mode="HTML"
        )
        return

    bookings_text = "📅 <b>Бронирования на неделю:</b>\n\n"
    shown = 0
    for event in events:
        if shown >= 10:
            break
        start = event.get("start")
        if not start:
            continue
        summary = event.get("summary", "Без названия")
        bookings_text += f"{start.strftime('%d.%m %H:%M')} — {summary}\n"
        shown += 1

    await callback.message.edit_text(
        bookings_text,
        reply_markup=get_admin_keyboard(),
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
                clients_text += f"   Telegram: @{client.telegram_id}\n"
            if client.phone:
                clients_text += f"   📞 {client.phone}\n"
            clients_text += "\n"
    else:
        clients_text += "Клиентов пока нет."
    
    await callback.message.edit_text(
        clients_text,
        reply_markup=get_admin_keyboard()
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
        admins_text += f"👤 ID: {admin.id}\n"
        admins_text += f"📱 Telegram: {admin.telegram_id or 'Не указан'}\n"
        admins_text += f"📧 VK: {admin.vk_id or 'Не указан'}\n"
        admins_text += f"📊 Статус: {status}\n\n"
    
    await callback.message.edit_text(
        admins_text,
        reply_markup=get_admin_keyboard()
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
