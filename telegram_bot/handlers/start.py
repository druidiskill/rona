from aiogram import Dispatcher, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import CommandStart, Command
from aiogram.fsm.context import FSMContext
from datetime import datetime, timedelta

from telegram_bot.keyboards import get_main_menu_keyboard, get_services_keyboard
from telegram_bot.states import BookingStates
from database import client_service, service_repo

# Опциональный импорт Google Calendar
try:
    from google_calendar.calendar_service import GoogleCalendarService
    CALENDAR_AVAILABLE = True
except Exception as e:
    GoogleCalendarService = None
    CALENDAR_AVAILABLE = False
    print(f"[WARNING] Google Calendar недоступен: {e}")

async def start_command(message: Message, state: FSMContext, is_admin: bool = False):
    """Обработчик команды /start"""
    await state.clear()
    
    # Получаем или создаем клиента
    client = await client_service.get_or_create_client(
        telegram_id=message.from_user.id,
        name=message.from_user.full_name or "Пользователь"
    )
    
    welcome_text = f"""
🎉 <b>Добро пожаловать в фотостудию!</b>

Привет, {message.from_user.first_name}! 👋

Выберите действие в меню ниже:
    """
    
    await message.answer(
        welcome_text,
        reply_markup=get_main_menu_keyboard(is_admin)
    )

async def main_menu_callback(callback: CallbackQuery, state: FSMContext, is_admin: bool = False):
    """Обработчик главного меню"""
    await state.clear()
    
    if callback.data == "admin_panel":
        if is_admin:
            from telegram_bot.handlers.admin import admin_panel
            await admin_panel(callback, is_admin)
        else:
            await callback.answer("У вас нет прав администратора", show_alert=True)
        return
    elif callback.data == "services":
        # Показываем услуги
        services = await service_repo.get_all_active()
        await callback.message.edit_text(
            "📸 <b>Наши услуги:</b>\n\nВыберите услугу для бронирования:",
            reply_markup=get_services_keyboard(services)
        )
    elif callback.data == "my_bookings":
        if not CALENDAR_AVAILABLE or not GoogleCalendarService:
            await callback.message.edit_text(
                "📅 <b>Ваши бронирования</b>\n\n"
                "Google Calendar недоступен. Проверьте настройки и токены.",
                reply_markup=get_main_menu_keyboard(),
                parse_mode="HTML"
            )
            return

        # Показываем бронирования клиента из календаря
        user_id = callback.from_user.id
        now = datetime.now()
        period_end = now + timedelta(days=90)

        try:
            calendar_service = GoogleCalendarService()
            events = await calendar_service.list_events(now, period_end)
        except Exception as e:
            print(f"Ошибка получения событий календаря: {e}")
            await callback.message.edit_text(
                "📅 <b>Ваши бронирования</b>\n\n"
                "Не удалось получить данные из календаря.",
                reply_markup=get_main_menu_keyboard(),
                parse_mode="HTML"
            )
            return

        needle = f"Telegram ID: {user_id}"
        user_events = [
            event for event in events
            if needle in (event.get(\"description\") or \"\")
        ]

        if not user_events:
            await callback.message.edit_text(
                "📅 <b>Ваши бронирования</b>\n\nУ вас пока нет бронирований.",
                reply_markup=get_main_menu_keyboard(),
                parse_mode="HTML"
            )
            return

        text = "📅 <b>Ваши бронирования:</b>\n\n"
        for event in user_events:
            start = event.get("start")
            if not start:
                continue
            summary = event.get("summary", "Без названия")
            text += f"📸 {summary}\n"
            text += f"📅 {start.strftime('%d.%m.%Y %H:%M')}\n\n"

        await callback.message.edit_text(
            text,
            reply_markup=get_main_menu_keyboard(),
            parse_mode="HTML"
        )
    elif callback.data == "contacts":
        # Показываем контакты
        await callback.message.edit_text(
            "📞 <b>Контакты:</b>\n\n"
            "📍 Адрес: <a href=\"https://yandex.ru/maps/-/CLbv7S8T\">улица Володи Дубинина, 3, Санкт-Петербург</a>\n"
            "🌐 Сайт: <a href=\"https://innasuvorova.ru/rona_photostudio\">Наш сайт</a>\n"
            "📱 Телефон: <a href=\"tel:+79119854008\">+7(911)985-40-08</a>\n"
            "✉️ Email: zvezda-mk@yandex.ru\n"
            "🕒 Время работы: 9:00 - 21:00",
            reply_markup=get_main_menu_keyboard(),
            parse_mode="HTML"
        )
    elif callback.data == "back_to_main":
        await callback.message.edit_text(
            "🏠 <b>Главное меню</b>\n\nВыберите действие:",
            reply_markup=get_main_menu_keyboard(is_admin=is_admin),
            parse_mode="HTML"
        )

async def help_command(message: Message):
    """Обработчик команды /help"""
    help_text = """
🤖 <b>Помощь по боту</b>

<b>Основные команды:</b>
/start - Главное меню
/help - Эта справка
/bookings - Мои бронирования
/contacts - Контакты

<b>Как забронировать:</b>
1. Выберите "📸 Услуги" в меню
2. Выберите нужную услугу
3. Укажите количество людей и время
4. Подтвердите бронирование

<b>Поддержка:</b>
Если у вас есть вопросы, обратитесь к администратору.
    """
    await message.answer(help_text, parse_mode="HTML")

def register_start_handlers(dp: Dispatcher):
    """Регистрация обработчиков старта"""
    dp.message.register(start_command, CommandStart())
    dp.message.register(help_command, Command("help"))
    dp.callback_query.register(main_menu_callback, F.data.in_([
        "services", "my_bookings", "contacts", "back_to_main", "admin_panel"
    ]))
