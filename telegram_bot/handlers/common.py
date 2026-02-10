from aiogram import Dispatcher, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command

from telegram_bot.keyboards import (
    get_main_menu_keyboard, get_admin_keyboard, get_services_management_keyboard, 
    get_bookings_management_keyboard, get_contacts_keyboard, get_my_bookings_keyboard,
    get_clients_management_keyboard, get_admins_management_keyboard
)

async def help_callback(callback: CallbackQuery):
    """Обработчик кнопки помощи"""
    help_text = """
🤖 <b>Помощь по боту</b>

<b>Основные функции:</b>
📸 <b>Услуги</b> - просмотр и бронирование фотосессий
📅 <b>Мои бронирования</b> - просмотр ваших бронирований
📞 <b>Контакты</b> - контактная информация

<b>Как забронировать:</b>
1. Выберите "📸 Услуги"
2. Выберите нужную услугу
3. Укажите дату и время
4. Выберите количество людей
5. Добавьте дополнительные услуги (при необходимости)
6. Подтвердите бронирование

<b>Дополнительные услуги:</b>
📸 Фотограф - профессиональный фотограф (+2000₽)
💄 Гримерка - подготовка к фотосессии (1000₽/час)

<b>Поддержка:</b>
Если у вас есть вопросы, обратитесь к администратору через контакты.
    """
    
    await callback.message.edit_text(
        help_text,
        reply_markup=get_main_menu_keyboard(),
        parse_mode="HTML"
    )

async def unknown_message(message: Message):
    """Обработчик неизвестных сообщений"""
    await message.answer(
        "🤔 <b>Не понимаю команду</b>\n\n"
        "Используйте кнопки меню или команду /start для начала работы.",
        reply_markup=get_main_menu_keyboard(),
        parse_mode="HTML"
    )

async def back_to_main_callback(callback: CallbackQuery, is_admin: bool = False):
    """Обработчик кнопки 'Назад в главное меню'"""
    await callback.message.edit_text(
        "🏠 <b>Главное меню</b>\n\nВыберите действие:",
        reply_markup=get_main_menu_keyboard(is_admin)
    )

async def back_to_admin_callback(callback: CallbackQuery):
    """Обработчик кнопки 'Назад в админ-панель'"""
    await callback.message.edit_text(
        "🔧 <b>Админ-панель</b>\n\nВыберите действие:",
        reply_markup=get_admin_keyboard()
    )

async def back_to_services_management_callback(callback: CallbackQuery):
    """Обработчик кнопки 'Назад к управлению услугами'"""
    await callback.message.edit_text(
        "📸 <b>Управление услугами</b>\n\nВыберите действие:",
        reply_markup=get_services_management_keyboard()
    )

async def back_to_bookings_management_callback(callback: CallbackQuery):
    """Обработчик кнопки 'Назад к управлению бронированиями'"""
    await callback.message.edit_text(
        "📅 <b>Управление бронированиями</b>\n\nВыберите действие:",
        reply_markup=get_bookings_management_keyboard()
    )

async def contacts_callback(callback: CallbackQuery):
    """Обработчик кнопки контактов"""
    contacts_text = """
📞 <b>Контакты фотостудии</b>

<b>Телефон:</b> +7 (900) 123-45-67
<b>WhatsApp:</b> +7 (900) 123-45-67
<b>Email:</b> info@studio.ru
<b>Сайт:</b> https://studio.ru

<b>Адрес:</b> г. Москва, ул. Примерная, д. 1
<b>Время работы:</b> 9:00 - 21:00 (ежедневно)

<b>Как добраться:</b>
🚇 Метро "Примерная" (5 мин пешком)
🚌 Автобусы: 123, 456 (остановка "Студия")
🚗 Парковка: бесплатная
    """
    
    await callback.message.edit_text(
        contacts_text,
        reply_markup=get_contacts_keyboard()
    )

async def my_bookings_callback(callback: CallbackQuery):
    """Обработчик кнопки моих бронирований"""
    await callback.message.edit_text(
        "📅 <b>Мои бронирования</b>\n\nВыберите действие:",
        reply_markup=get_my_bookings_keyboard()
    )

async def admin_clients_callback(callback: CallbackQuery):
    """Обработчик кнопки управления клиентами"""
    await callback.message.edit_text(
        "👥 <b>Управление клиентами</b>\n\nВыберите действие:",
        reply_markup=get_clients_management_keyboard()
    )

async def admin_admins_callback(callback: CallbackQuery):
    """Обработчик кнопки управления администраторами"""
    await callback.message.edit_text(
        "👨‍💼 <b>Управление администраторами</b>\n\nВыберите действие:",
        reply_markup=get_admins_management_keyboard()
    )

async def unknown_callback(callback: CallbackQuery):
    """Обработчик неизвестных callback'ов"""
    await callback.answer("Неизвестная команда", show_alert=True)

def register_common_handlers(dp: Dispatcher):
    """Регистрация общих обработчиков"""
    dp.callback_query.register(help_callback, F.data == "help")
    dp.callback_query.register(contacts_callback, F.data == "contacts")
    dp.callback_query.register(my_bookings_callback, F.data == "my_bookings")
    dp.callback_query.register(admin_clients_callback, F.data == "admin_clients")
    dp.callback_query.register(admin_admins_callback, F.data == "admin_admins")
    dp.callback_query.register(back_to_main_callback, F.data == "back_to_main")
    dp.callback_query.register(back_to_admin_callback, F.data == "admin_panel")
    dp.callback_query.register(back_to_services_management_callback, F.data == "admin_services")
    dp.callback_query.register(back_to_bookings_management_callback, F.data == "admin_bookings")
    dp.message.register(unknown_message)
    dp.callback_query.register(unknown_callback)
