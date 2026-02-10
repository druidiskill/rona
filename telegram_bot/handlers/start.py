from aiogram import Dispatcher, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import CommandStart, Command
from aiogram.fsm.context import FSMContext
from datetime import datetime, timedelta

from telegram_bot.keyboards import get_main_menu_keyboard, get_services_keyboard, get_my_bookings_keyboard
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

    greeting_name = (
        client.name
        if client and client.name and client.name.strip() and client.name != "Пользователь"
        else (message.from_user.first_name or "Пользователь")
    )
    
    welcome_text = f"""
🎉 <b>Добро пожаловать в фотостудию!</b>

Привет, {greeting_name}! 👋

Выберите действие в меню ниже:
    """
    
    await message.answer(
        welcome_text,
        reply_markup=get_main_menu_keyboard(is_admin),
        parse_mode="HTML"
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
        text = "📸 <b>Наши услуги:</b>\n\nВыберите услугу для бронирования:"
        try:
            await callback.message.edit_text(
                text,
                reply_markup=get_services_keyboard(services),
                parse_mode="HTML"
            )
        except Exception:
            # Если текущее сообщение - фото/медиа, edit_text не работает
            try:
                await callback.message.delete()
            except Exception:
                pass
            await callback.message.answer(
                text,
                reply_markup=get_services_keyboard(services),
                parse_mode="HTML"
            )
    elif callback.data == "my_bookings":
        await callback.message.edit_text(
            "📅 <b>Мои бронирования</b>\n\n"
            "Выберите раздел:",
            reply_markup=get_my_bookings_keyboard(),
            parse_mode="HTML"
        )
    elif callback.data in {"active_bookings", "booking_history"}:
        if not CALENDAR_AVAILABLE or not GoogleCalendarService:
            await callback.message.edit_text(
                "📅 <b>Ваши бронирования</b>\n\n"
                "Google Calendar недоступен. Проверьте настройки и токены.",
                reply_markup=get_my_bookings_keyboard(),
                parse_mode="HTML"
            )
            return

        # Показываем бронирования клиента из календаря (по телефону)
        from database import client_repo
        user_id = callback.from_user.id
        phone_display = None
        try:
            client = await client_repo.get_by_telegram_id(user_id)
            if client and client.phone:
                phone = client.phone
                if len(phone) == 10 and phone.isdigit():
                    phone_display = f"+7 {phone[:3]} {phone[3:6]} {phone[6:8]} {phone[8:10]}"
                else:
                    phone_display = str(phone)
        except Exception:
            phone_display = None
        now = datetime.now()
        if callback.data == "active_bookings":
            period_start = now
            period_end = now + timedelta(days=90)
            title = "📅 <b>Активные бронирования:</b>\n\n"
            empty_text = "📅 <b>Активные бронирования</b>\n\nУ вас пока нет активных бронирований."
        else:
            period_start = now - timedelta(days=180)
            period_end = now
            title = "📅 <b>История бронирований:</b>\n\n"
            empty_text = "📅 <b>История бронирований</b>\n\nИстория пока пуста."

        try:
            calendar_service = GoogleCalendarService()
            events = await calendar_service.list_events(period_start, period_end)
        except Exception as e:
            print(f"Ошибка получения событий календаря: {e}")
            await callback.message.edit_text(
                "📅 <b>Ваши бронирования</b>\n\n"
                "Не удалось получить данные из календаря.",
                reply_markup=get_my_bookings_keyboard(),
                parse_mode="HTML"
            )
            return

        user_events = []
        if phone_display:
            needle = phone_display
            user_events = [
                event for event in events
                if needle in (event.get("description") or "")
            ]

        if not user_events:
            await callback.message.edit_text(
                empty_text,
                reply_markup=get_my_bookings_keyboard(),
                parse_mode="HTML"
            )
            return

        text = title
        for event in user_events:
            start = event.get("start")
            if not start:
                continue
            summary = event.get("summary", "Без названия")
            text += f"📸 {summary}\n"
            text += f"📅 {start.strftime('%d.%m.%Y %H:%M')}\n\n"

        await callback.message.edit_text(
            text,
            reply_markup=get_my_bookings_keyboard(),
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
        text = "🏠 <b>Главное меню</b>\n\nВыберите действие:"
        try:
            await callback.message.edit_text(
                text,
                reply_markup=get_main_menu_keyboard(is_admin=is_admin),
                parse_mode="HTML"
            )
        except Exception:
            try:
                await callback.message.delete()
            except Exception:
                pass
            await callback.message.answer(
                text,
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
        "services", "my_bookings", "active_bookings", "booking_history", "contacts", "back_to_main", "admin_panel"
    ]))
