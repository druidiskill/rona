from datetime import datetime, timedelta

from vkbottle.bot import Bot, Message

from config import ADMIN_IDS_VK
from database import client_service, service_repo
from telegram_bot.services.calendar_queries import (
    get_user_calendar_events_by_vk_id,
    is_calendar_available,
)
from vk_bot.handlers.booking import get_services_booking_keyboard
from vk_bot.keyboards import get_back_to_main_keyboard, get_main_menu_keyboard


def _parse_admin_ids(value: str) -> set[int]:
    return {int(x.strip()) for x in value.split(",") if x.strip().isdigit()}


ADMIN_IDS = _parse_admin_ids(ADMIN_IDS_VK)


def _normalize_text(text: str | None) -> str:
    if not text:
        return ""
    return " ".join(text.strip().lower().split())


def _strip_leading_emoji(text: str) -> str:
    # Для кнопок вида "🏠 Главное меню" или "📸 Услуги"
    if not text:
        return text
    parts = text.split(" ", 1)
    if len(parts) == 2 and len(parts[0]) <= 3:
        return parts[1]
    return text


async def _send_main_menu(message: Message):
    client = await client_service.get_or_create_client(
        vk_id=message.from_id,
        name="Пользователь",
    )
    greeting_name = (
        client.name
        if client and client.name and client.name.strip() and client.name != "Пользователь"
        else "Пользователь"
    )
    is_admin = message.from_id in ADMIN_IDS
    text = (
        "🎉 Добро пожаловать в фотостудию!\n\n"
        f"Привет, {greeting_name}! 👋\n\n"
        "Выберите действие в меню ниже:"
    )
    await message.answer(text, keyboard=get_main_menu_keyboard(is_admin=is_admin))


async def _send_services(message: Message):
    services = await service_repo.get_all_active()
    if not services:
        await message.answer(
            "📸 Сейчас нет доступных услуг.",
            keyboard=get_back_to_main_keyboard(),
        )
        return

    lines = ["📸 Наши услуги:\n"]
    for service in services:
        lines.append(f"• {service.name} — от {service.price_min}₽")
    lines.append("\nВыберите услугу кнопкой ниже:")
    await message.answer("\n".join(lines), keyboard=get_services_booking_keyboard(services))


async def _send_my_bookings(message: Message):
    if not is_calendar_available():
        await message.answer(
            "Google Calendar недоступен. Проверьте настройки.",
            keyboard=get_back_to_main_keyboard(),
        )
        return

    now = datetime.now()
    events, error_code = await get_user_calendar_events_by_vk_id(
        vk_id=message.from_id,
        period_start=now - timedelta(days=180),
        period_end=now + timedelta(days=90),
    )
    if error_code == "calendar_unavailable":
        await message.answer(
            "Google Calendar недоступен. Проверьте настройки.",
            keyboard=get_back_to_main_keyboard(),
        )
        return
    if not events:
        await message.answer(
            "📅 У вас пока нет бронирований.",
            keyboard=get_back_to_main_keyboard(),
        )
        return

    text_lines = ["📅 Ваши бронирования:\n"]
    for event in events[:15]:
        start = event.get("start")
        summary = event.get("summary") or "Без названия"
        if not start:
            continue
        text_lines.append(f"• {start.strftime('%d.%m.%Y %H:%M')} — {summary}")
    await message.answer("\n".join(text_lines), keyboard=get_back_to_main_keyboard())


async def _send_contacts(message: Message):
    await message.answer(
        "📞 Контакты:\n\n"
        "📍 Адрес: улица Володи Дубинина, 3, Санкт-Петербург\n"
        "🌐 Сайт: https://innasuvorova.ru/rona_photostudio\n"
        "✉️ Email: rona.photostudio.petergof@gmail.com\n"
        "🕒 Время работы: с 9:00 до 21:00 по предварительному бронированию",
        keyboard=get_back_to_main_keyboard(),
    )


async def _send_help(message: Message):
    await message.answer(
        "🤖 Помощь по боту\n\n"
        "Основные функции:\n"
        "• Услуги\n"
        "• Мои бронирования\n"
        "• Контакты\n\n"
        "Следующий шаг: подключаем полноценный процесс бронирования.",
        keyboard=get_back_to_main_keyboard(),
    )


def register_start_handlers(bot: Bot):
    @bot.on.message()
    async def main_router(message: Message):
        text = _normalize_text(message.text)
        text_wo_emoji = _normalize_text(_strip_leading_emoji(text))

        start_commands = {"/start", "start", "начать", "меню", "главное меню"}
        if text in start_commands or text_wo_emoji in start_commands:
            await _send_main_menu(message)
            return

        if text == "услуги" or text_wo_emoji == "услуги":
            await _send_services(message)
            return

        if text == "мои бронирования" or text_wo_emoji == "мои бронирования":
            await _send_my_bookings(message)
            return

        if text == "контакты" or text_wo_emoji == "контакты":
            await _send_contacts(message)
            return

        if text == "помощь" or text_wo_emoji == "помощь":
            await _send_help(message)
            return

        await message.answer(
            "🤔 Не понимаю команду.\nИспользуйте кнопки меню или напишите /start.",
            keyboard=get_main_menu_keyboard(is_admin=message.from_id in ADMIN_IDS),
        )
