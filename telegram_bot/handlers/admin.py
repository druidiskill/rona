from aiogram import Dispatcher, F
from aiogram.types import CallbackQuery, Message, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext

import html
import hashlib

from telegram_bot.keyboards import (
    get_admin_keyboard,
    get_main_menu_keyboard,
    get_services_management_keyboard,
    get_bookings_management_keyboard,
    get_admin_booking_detail_keyboard,
    get_admin_help_keyboard,
    get_admin_faq_list_keyboard,
    get_admin_faq_detail_keyboard,
    _display_summary_for_list_button,
)
from telegram_bot.states import AdminStates
from database import admin_repo, service_repo, client_repo, faq_repo
from datetime import datetime, timedelta
from telegram_bot.services.calendar_queries import (
    is_calendar_available,
    list_events as svc_list_events,
    get_event as svc_get_event,
    delete_event as svc_delete_event,
)
from telegram_bot.services.contact_utils import (
    extract_booking_contact_details as svc_extract_booking_contact_details,
    normalize_phone as svc_normalize_phone,
    format_phone_plus7 as svc_format_phone_plus7,
)


def _extract_booking_contact_details(description: str) -> dict:
    return svc_extract_booking_contact_details(description)


def _normalize_phone(phone: str | None) -> str | None:
    return svc_normalize_phone(phone)


def _format_phone_plus7(phone: str | None) -> str | None:
    return svc_format_phone_plus7(phone)

_ADMIN_BOOKING_TOKEN_MAP: dict[str, tuple[str, int]] = {}

def _register_admin_booking_token(user_id: int, event_id: str) -> str:
    token_source = f"{user_id}:{event_id}"
    token = hashlib.sha1(token_source.encode("utf-8")).hexdigest()[:12]
    _ADMIN_BOOKING_TOKEN_MAP[token] = (event_id, user_id)
    return token

def _resolve_admin_booking_token(token_or_event_id: str, user_id: int) -> tuple[str | None, str | None]:
    entry = _ADMIN_BOOKING_TOKEN_MAP.get(token_or_event_id)
    if entry:
        mapped_event_id, mapped_user_id = entry
        if mapped_user_id != user_id:
            return None, "access_denied"
        return mapped_event_id, None

    if len(token_or_event_id) <= 16 and token_or_event_id.isalnum():
        return None, "stale"
    return token_or_event_id, None

def _build_admin_future_bookings_keyboard(events: list[dict], user_id: int) -> InlineKeyboardMarkup:
    keyboard: list[list[InlineKeyboardButton]] = []
    for event in events:
        event_id = event.get("id")
        start = event.get("start")
        summary = _display_summary_for_list_button(event)
        if not event_id or not start:
            continue
        token = _register_admin_booking_token(user_id, event_id)
        button_text = f"🕐 {start.strftime('%d.%m %H:%M')} — {summary}"
        keyboard.append([
            InlineKeyboardButton(
                text=button_text[:64],
                callback_data=f"admin_booking_open_{token}",
            )
        ])

    keyboard.append([InlineKeyboardButton(text="🔙 Назад", callback_data="admin_panel")])
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

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

async def _build_admin_faq_text() -> str:
    faqs = await faq_repo.get_all()
    text = "❓ <b>Помощь (FAQ)</b>\n\n"
    if not faqs:
        text += "Список вопросов пуст."
        return text

    for idx, entry in enumerate(faqs, start=1):
        status = "✅" if entry.is_active else "❌"
        question = html.escape(entry.question or "")
        text += f"{status} {idx}. {question}\n"
    return text

async def _build_admin_faq_list_keyboard() -> InlineKeyboardMarkup:
    faqs = await faq_repo.get_all()
    items = [(entry.id or 0, entry.question or "", entry.is_active) for entry in faqs]
    return get_admin_faq_list_keyboard(items)

async def admin_help(callback: CallbackQuery, is_admin: bool):
    """Раздел помощи в админ-панели."""
    if not is_admin:
        await callback.answer("У вас нет прав администратора", show_alert=True)
        return

    text = await _build_admin_faq_text()
    keyboard = await _build_admin_faq_list_keyboard()
    await callback.message.edit_text(
        text,
        reply_markup=keyboard,
        parse_mode="HTML",
    )
    await callback.answer()

async def admin_faq_add(callback: CallbackQuery, state: FSMContext, is_admin: bool):
    """Старт добавления FAQ."""
    if not is_admin:
        await callback.answer("У вас нет прав администратора", show_alert=True)
        return

    await state.clear()
    await state.set_state(AdminStates.waiting_for_faq_question)
    await callback.message.edit_text(
        "✍️ Введите вопрос для FAQ:",
        reply_markup=get_admin_help_keyboard(),
        parse_mode="HTML",
    )
    await callback.answer()

async def admin_faq_open(callback: CallbackQuery, is_admin: bool):
    if not is_admin:
        await callback.answer("У вас нет прав администратора", show_alert=True)
        return

    parts = callback.data.split("_")
    if len(parts) < 4:
        await callback.answer("Ошибка данных FAQ", show_alert=True)
        return

    try:
        faq_id = int(parts[3])
    except ValueError:
        await callback.answer("Ошибка данных FAQ", show_alert=True)
        return

    entry = await faq_repo.get_by_id(faq_id)
    if not entry:
        await callback.answer("FAQ не найден", show_alert=True)
        return

    text = (
        "❓ <b>Вопрос</b>\n"
        f"{html.escape(entry.question or '')}\n\n"
        "💡 <b>Ответ</b>\n"
        f"{html.escape(entry.answer or '')}"
    )
    await callback.message.edit_text(
        text,
        reply_markup=get_admin_faq_detail_keyboard(faq_id, entry.is_active),
        parse_mode="HTML",
    )
    await callback.answer()

async def admin_faq_edit_question(callback: CallbackQuery, state: FSMContext, is_admin: bool):
    if not is_admin:
        await callback.answer("У вас нет прав администратора", show_alert=True)
        return

    try:
        faq_id = int(callback.data.split("_")[-1])
    except ValueError:
        await callback.answer("Ошибка данных FAQ", show_alert=True)
        return

    await state.update_data(faq_id=faq_id)
    await state.set_state(AdminStates.waiting_for_faq_edit_question)
    await callback.message.edit_text(
        "✍️ Введите новый текст вопроса:",
        reply_markup=get_admin_help_keyboard(),
        parse_mode="HTML",
    )
    await callback.answer()

async def admin_faq_edit_answer(callback: CallbackQuery, state: FSMContext, is_admin: bool):
    if not is_admin:
        await callback.answer("У вас нет прав администратора", show_alert=True)
        return

    try:
        faq_id = int(callback.data.split("_")[-1])
    except ValueError:
        await callback.answer("Ошибка данных FAQ", show_alert=True)
        return

    await state.update_data(faq_id=faq_id)
    await state.set_state(AdminStates.waiting_for_faq_edit_answer)
    await callback.message.edit_text(
        "✍️ Введите новый текст ответа:",
        reply_markup=get_admin_help_keyboard(),
        parse_mode="HTML",
    )
    await callback.answer()

async def admin_faq_toggle(callback: CallbackQuery, is_admin: bool):
    if not is_admin:
        await callback.answer("У вас нет прав администратора", show_alert=True)
        return

    try:
        faq_id = int(callback.data.split("_")[-1])
    except ValueError:
        await callback.answer("Ошибка данных FAQ", show_alert=True)
        return

    entry = await faq_repo.get_by_id(faq_id)
    if not entry:
        await callback.answer("FAQ не найден", show_alert=True)
        return

    await faq_repo.set_active(faq_id, not entry.is_active)
    entry = await faq_repo.get_by_id(faq_id)
    if not entry:
        await callback.answer("FAQ не найден", show_alert=True)
        return

    text = (
        "❓ <b>Вопрос</b>\n"
        f"{html.escape(entry.question or '')}\n\n"
        "💡 <b>Ответ</b>\n"
        f"{html.escape(entry.answer or '')}"
    )
    await callback.message.edit_text(
        text,
        reply_markup=get_admin_faq_detail_keyboard(faq_id, entry.is_active),
        parse_mode="HTML",
    )
    await callback.answer()

async def admin_faq_delete(callback: CallbackQuery, is_admin: bool):
    if not is_admin:
        await callback.answer("У вас нет прав администратора", show_alert=True)
        return

    try:
        faq_id = int(callback.data.split("_")[-1])
    except ValueError:
        await callback.answer("Ошибка данных FAQ", show_alert=True)
        return

    await faq_repo.delete(faq_id)
    text = await _build_admin_faq_text()
    keyboard = await _build_admin_faq_list_keyboard()
    await callback.message.edit_text(
        text,
        reply_markup=keyboard,
        parse_mode="HTML",
    )
    await callback.answer("Удалено")

async def process_faq_question(message: Message, state: FSMContext, is_admin: bool):
    if not is_admin:
        await message.answer("У вас нет прав администратора")
        return

    question = (message.text or "").strip()
    if not question:
        await message.answer("❌ Вопрос не может быть пустым. Введите вопрос:")
        return
    if len(question) > 40:
        await message.answer("❌ Вопрос не должен быть длиннее 40 символов. Введите короче:")
        return

    await state.update_data(faq_question=question)
    await state.set_state(AdminStates.waiting_for_faq_answer)
    await message.answer("✍️ Введите ответ для этого вопроса:")

async def process_faq_answer(message: Message, state: FSMContext, is_admin: bool):
    if not is_admin:
        await message.answer("У вас нет прав администратора")
        return

    answer = (message.text or "").strip()
    if not answer:
        await message.answer("❌ Ответ не может быть пустым. Введите ответ:")
        return

    data = await state.get_data()
    question = (data.get("faq_question") or "").strip()
    if not question:
        await state.set_state(AdminStates.waiting_for_faq_question)
        await message.answer("❌ Вопрос не найден. Введите вопрос:")
        return

    await faq_repo.add(question=question, answer=answer)
    await state.clear()

    text = await _build_admin_faq_text()
    await message.answer(
        "✅ Вопрос добавлен.",
        parse_mode="HTML",
    )
    await message.answer(
        text,
        reply_markup=await _build_admin_faq_list_keyboard(),
        parse_mode="HTML",
    )

async def process_faq_edit_question(message: Message, state: FSMContext, is_admin: bool):
    if not is_admin:
        await message.answer("У вас нет прав администратора")
        return

    question = (message.text or "").strip()
    if not question:
        await message.answer("❌ Вопрос не может быть пустым. Введите вопрос:")
        return

    data = await state.get_data()
    faq_id = data.get("faq_id")
    if not isinstance(faq_id, int):
        await state.clear()
        await message.answer("❌ Не выбран FAQ для редактирования.")
        return

    await faq_repo.update_question(faq_id, question)
    await state.clear()

    entry = await faq_repo.get_by_id(faq_id)
    if not entry:
        await message.answer("❌ FAQ не найден.")
        return

    text = (
        "❓ <b>Вопрос</b>\n"
        f"{html.escape(entry.question or '')}\n\n"
        "💡 <b>Ответ</b>\n"
        f"{html.escape(entry.answer or '')}"
    )
    await message.answer(
        "✅ Вопрос обновлен.",
        parse_mode="HTML",
    )
    await message.answer(
        text,
        reply_markup=get_admin_faq_detail_keyboard(faq_id, entry.is_active),
        parse_mode="HTML",
    )

async def process_faq_edit_answer(message: Message, state: FSMContext, is_admin: bool):
    if not is_admin:
        await message.answer("У вас нет прав администратора")
        return

    answer = (message.text or "").strip()
    if not answer:
        await message.answer("❌ Ответ не может быть пустым. Введите ответ:")
        return

    data = await state.get_data()
    faq_id = data.get("faq_id")
    if not isinstance(faq_id, int):
        await state.clear()
        await message.answer("❌ Не выбран FAQ для редактирования.")
        return

    await faq_repo.update_answer(faq_id, answer)
    await state.clear()

    entry = await faq_repo.get_by_id(faq_id)
    if not entry:
        await message.answer("❌ FAQ не найден.")
        return

    text = (
        "❓ <b>Вопрос</b>\n"
        f"{html.escape(entry.question or '')}\n\n"
        "💡 <b>Ответ</b>\n"
        f"{html.escape(entry.answer or '')}"
    )
    await message.answer(
        "✅ Ответ обновлен.",
        parse_mode="HTML",
    )
    await message.answer(
        text,
        reply_markup=get_admin_faq_detail_keyboard(faq_id, entry.is_active),
        parse_mode="HTML",
    )

async def admin_stats(callback: CallbackQuery, is_admin: bool):
    """Статистика для админа"""
    if not is_admin:
        await callback.answer("У вас нет прав администратора", show_alert=True)
        return
    
    # Получаем статистику
    services = await service_repo.get_all()
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

    if not is_calendar_available():
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
        events = await svc_list_events(period_start, period_end, max_results=250)
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
        reply_markup=_build_admin_future_bookings_keyboard(future_events, callback.from_user.id),
        parse_mode="HTML"
    )


async def admin_booking_open(callback: CallbackQuery, is_admin: bool):
    """Карточка выбранного бронирования для админа."""
    if not is_admin:
        await callback.answer("У вас нет прав администратора", show_alert=True)
        return

    token_or_event_id = callback.data.replace("admin_booking_open_", "", 1)
    event_id, err = _resolve_admin_booking_token(token_or_event_id, callback.from_user.id)
    if err == "access_denied":
        await callback.answer("Нет доступа к этой записи", show_alert=True)
        return
    if err == "stale" or not event_id:
        await callback.answer("Список устарел, откройте заново", show_alert=True)
        return
    if not is_calendar_available():
        await callback.answer("Google Calendar недоступен", show_alert=True)
        return

    try:
        raw_event = await svc_get_event(event_id)
    except Exception as e:
        print(f"Ошибка получения события {event_id}: {e}")
        await callback.answer("Не удалось получить бронирование", show_alert=True)
        return
    if not raw_event:
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

    booking_token = _register_admin_booking_token(callback.from_user.id, event_id)

    await callback.message.edit_text(
        text,
        reply_markup=get_admin_booking_detail_keyboard(chat_target_user_id, None, booking_token),
        parse_mode="HTML"
    )

async def admin_booking_cancel(callback: CallbackQuery, is_admin: bool):
    """Отмена бронирования админом."""
    if not is_admin:
        await callback.answer("У вас нет прав администратора", show_alert=True)
        return

    token = callback.data.replace("admin_booking_cancel_", "", 1)
    event_id, err = _resolve_admin_booking_token(token, callback.from_user.id)
    if err == "access_denied":
        await callback.answer("Нет доступа к этой записи", show_alert=True)
        return
    if err == "stale" or not event_id:
        await callback.answer("Список устарел, откройте заново", show_alert=True)
        return

    if not is_calendar_available():
        await callback.answer("Календарь недоступен", show_alert=True)
        return

    now = datetime.now()
    period_start = now - timedelta(days=30)
    period_end = now + timedelta(days=365)

    try:
        # Удаляем связанную доп. услугу (Service ID: 9), если найдется
        try:
            all_events = await svc_list_events(period_start, period_end, max_results=250)
            marker = f"Связано с событием: {event_id}"
            linked_events = [
                e for e in all_events
                if marker in (e.get("description") or "")
                and "Service ID: 9" in (e.get("description") or "")
            ]
            for linked in linked_events:
                linked_id = linked.get("id")
                if linked_id:
                    await svc_delete_event(linked_id)
        except Exception as e:
            print(f"Ошибка удаления связанной услуги id=9: {e}")

        await svc_delete_event(event_id)
    except Exception as e:
        print(f"Ошибка отмены бронирования админом: {e}")
        await callback.answer("Не удалось отменить бронирование", show_alert=True)
        return

    await callback.answer("✅ Бронирование отменено")
    await admin_bookings(callback, is_admin)

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
                phone_display = _format_phone_plus7(client.phone)
                clients_text += f"   📞 {phone_display}\n"
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
    
    if not is_calendar_available():
        await callback.message.edit_text(
            "📅 <b>Бронирования на сегодня</b>\n\n"
            "Google Calendar недоступен. Проверьте настройки и токены.",
            reply_markup=get_bookings_management_keyboard(),
            parse_mode="HTML"
        )
        return

    try:
        events = await svc_list_events(today, tomorrow)
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
    
    if not is_calendar_available():
        await callback.message.edit_text(
            "📅 <b>Бронирования на завтра</b>\n\n"
            "Google Calendar недоступен. Проверьте настройки и токены.",
            reply_markup=get_bookings_management_keyboard(),
            parse_mode="HTML"
        )
        return

    try:
        events = await svc_list_events(tomorrow, day_after)
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

    if not is_calendar_available():
        await callback.message.edit_text(
            "📅 <b>Бронирования на неделю</b>\n\n"
            "Google Calendar недоступен. Проверьте настройки и токены.",
            reply_markup=get_bookings_management_keyboard(),
            parse_mode="HTML"
        )
        return

    try:
        events = await svc_list_events(today, week_later, max_results=100)
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

    if not is_calendar_available():
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
        events = await svc_list_events(
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
    dp.callback_query.register(admin_help, F.data == "admin_help")
    dp.callback_query.register(admin_faq_add, F.data == "admin_faq_add")
    dp.callback_query.register(admin_faq_open, F.data.startswith("admin_faq_open_"))
    dp.callback_query.register(admin_faq_edit_question, F.data.startswith("admin_faq_edit_q_"))
    dp.callback_query.register(admin_faq_edit_answer, F.data.startswith("admin_faq_edit_a_"))
    dp.callback_query.register(admin_faq_toggle, F.data.startswith("admin_faq_toggle_"))
    dp.callback_query.register(admin_faq_delete, F.data.startswith("admin_faq_delete_"))
    dp.callback_query.register(bookings_today, F.data == "bookings_today")
    dp.callback_query.register(bookings_tomorrow, F.data == "bookings_tomorrow")
    dp.callback_query.register(bookings_week, F.data == "bookings_week")
    dp.callback_query.register(search_bookings, F.data == "search_bookings")
    dp.callback_query.register(admin_booking_open, F.data.startswith("admin_booking_open_"))
    dp.callback_query.register(admin_booking_cancel, F.data.startswith("admin_booking_cancel_"))
    dp.message.register(process_search_bookings_query, AdminStates.waiting_for_booking_search_query)
    dp.message.register(process_faq_question, AdminStates.waiting_for_faq_question)
    dp.message.register(process_faq_answer, AdminStates.waiting_for_faq_answer)
    dp.message.register(process_faq_edit_question, AdminStates.waiting_for_faq_edit_question)
    dp.message.register(process_faq_edit_answer, AdminStates.waiting_for_faq_edit_answer)
