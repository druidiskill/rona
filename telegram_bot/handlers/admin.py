from aiogram import Dispatcher, F
from aiogram.types import CallbackQuery, Message, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext

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
from db import admin_repo, service_repo, client_repo, faq_repo
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
from core.support.admin_faq import (
    build_admin_faq_detail_text,
    build_admin_faq_keyboard_items,
    build_admin_faq_overview_text,
    validate_admin_faq_answer,
    validate_admin_faq_question,
)
from core.support.admin_faq_use_case import (
    create_admin_faq_entry,
    delete_admin_faq_entry,
    get_admin_faq_entry,
    toggle_admin_faq_active,
    update_admin_faq_answer,
    update_admin_faq_question,
)
from core.admin.bookings import (
    cancel_admin_booking_event,
    load_admin_booking_detail,
    load_admin_future_bookings,
    load_admin_period_bookings,
    search_admin_bookings,
)
from core.admin.overview import (
    build_admin_admins_text,
    build_admin_clients_text,
    build_admin_services_text,
    build_admin_stats_text,
)
from core.admin.tokens import (
    register_admin_booking_token,
    resolve_admin_booking_token,
)

ADMIN_FUTURE_BOOKINGS_LIMIT = 30


def _extract_booking_contact_details(description: str) -> dict:
    return svc_extract_booking_contact_details(description)


def _normalize_phone(phone: str | None) -> str | None:
    return svc_normalize_phone(phone)


def _format_phone_plus7(phone: str | None) -> str | None:
    return svc_format_phone_plus7(phone)

def _build_admin_future_bookings_keyboard(events: list[dict], user_id: int) -> InlineKeyboardMarkup:
    keyboard: list[list[InlineKeyboardButton]] = []
    for event in events[:ADMIN_FUTURE_BOOKINGS_LIMIT]:
        event_id = event.get("id")
        start = event.get("start")
        summary = _display_summary_for_list_button(event)
        if not event_id or not start:
            continue
        token = register_admin_booking_token(user_id, event_id)
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
    return build_admin_faq_overview_text(faqs)

async def _build_admin_faq_list_keyboard() -> InlineKeyboardMarkup:
    faqs = await faq_repo.get_all()
    items = build_admin_faq_keyboard_items(faqs)
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

    entry = await get_admin_faq_entry(faq_repo, faq_id)
    if not entry:
        await callback.answer("FAQ не найден", show_alert=True)
        return

    await callback.message.edit_text(
        build_admin_faq_detail_text(entry),
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

    entry = await get_admin_faq_entry(faq_repo, faq_id)
    if not entry:
        await callback.answer("FAQ не найден", show_alert=True)
        return

    entry = await toggle_admin_faq_active(faq_repo, faq_id)
    if not entry:
        await callback.answer("FAQ не найден", show_alert=True)
        return

    await callback.message.edit_text(
        build_admin_faq_detail_text(entry),
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

    await delete_admin_faq_entry(faq_repo, faq_id)
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
    error_text = validate_admin_faq_question(question)
    if error_text:
        await message.answer(error_text)
        return

    await state.update_data(faq_question=question)
    await state.set_state(AdminStates.waiting_for_faq_answer)
    await message.answer("✍️ Введите ответ для этого вопроса:")

async def process_faq_answer(message: Message, state: FSMContext, is_admin: bool):
    if not is_admin:
        await message.answer("У вас нет прав администратора")
        return

    answer = (message.text or "").strip()
    error_text = validate_admin_faq_answer(answer)
    if error_text:
        await message.answer(error_text)
        return

    data = await state.get_data()
    question = (data.get("faq_question") or "").strip()
    if not question:
        await state.set_state(AdminStates.waiting_for_faq_question)
        await message.answer("❌ Вопрос не найден. Введите вопрос:")
        return

    await create_admin_faq_entry(faq_repo, question=question, answer=answer)
    await state.clear()

    text = await _build_admin_faq_text()
    await message.answer("✅ Вопрос добавлен.", parse_mode="HTML")
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
    error_text = validate_admin_faq_question(question)
    if error_text:
        await message.answer(error_text)
        return

    data = await state.get_data()
    faq_id = data.get("faq_id")
    if not isinstance(faq_id, int):
        await state.clear()
        await message.answer("❌ Не выбран FAQ для редактирования.")
        return

    entry = await update_admin_faq_question(faq_repo, faq_id=faq_id, question=question)
    await state.clear()

    if not entry:
        await message.answer("❌ FAQ не найден.")
        return

    await message.answer("✅ Вопрос обновлён.", parse_mode="HTML")
    await message.answer(
        build_admin_faq_detail_text(entry),
        reply_markup=get_admin_faq_detail_keyboard(faq_id, entry.is_active),
        parse_mode="HTML",
    )

async def process_faq_edit_answer(message: Message, state: FSMContext, is_admin: bool):
    if not is_admin:
        await message.answer("У вас нет прав администратора")
        return

    answer = (message.text or "").strip()
    error_text = validate_admin_faq_answer(answer)
    if error_text:
        await message.answer(error_text)
        return

    data = await state.get_data()
    faq_id = data.get("faq_id")
    if not isinstance(faq_id, int):
        await state.clear()
        await message.answer("❌ Не выбран FAQ для редактирования.")
        return

    entry = await update_admin_faq_answer(faq_repo, faq_id=faq_id, answer=answer)
    await state.clear()

    if not entry:
        await message.answer("❌ FAQ не найден.")
        return

    await message.answer("✅ Ответ обновлён.", parse_mode="HTML")
    await message.answer(
        build_admin_faq_detail_text(entry),
        reply_markup=get_admin_faq_detail_keyboard(faq_id, entry.is_active),
        parse_mode="HTML",
    )

async def admin_stats(callback: CallbackQuery, is_admin: bool):
    """Раздел статистики."""
    if not is_admin:
        await callback.answer("У вас нет прав администратора", show_alert=True)
        return

    services = await service_repo.get_all()
    await callback.message.edit_text(
        build_admin_stats_text(services_count=len(services)),
        reply_markup=get_admin_keyboard(),
        parse_mode="HTML",
    )

async def admin_bookings(callback: CallbackQuery, is_admin: bool):
    """Управление бронированиями"""
    if not is_admin:
        await callback.answer("У вас нет прав администратора", show_alert=True)
        return

    result = await load_admin_future_bookings(
        is_calendar_available=is_calendar_available,
        list_events=svc_list_events,
    )
    if result.status != "ok":
        await callback.message.edit_text(
            result.text,
            reply_markup=get_admin_keyboard(),
            parse_mode="HTML",
        )
        return

    text = result.text
    if len(result.events) > ADMIN_FUTURE_BOOKINGS_LIMIT:
        text = (
            f"{text}\n\n"
            f"Показаны ближайшие {ADMIN_FUTURE_BOOKINGS_LIMIT} записей. "
            "Для остальных используйте поиск или разделы по периодам."
        )

    await callback.message.edit_text(
        text,
        reply_markup=_build_admin_future_bookings_keyboard(result.events, callback.from_user.id),
        parse_mode="HTML",
    )

async def admin_booking_open(callback: CallbackQuery, is_admin: bool):
    """Карточка выбранного бронирования для админа."""
    if not is_admin:
        await callback.answer("У вас нет прав администратора", show_alert=True)
        return

    token_or_event_id = callback.data.replace("admin_booking_open_", "", 1)
    event_id, err = resolve_admin_booking_token(token_or_event_id, callback.from_user.id)
    if err == "access_denied":
        await callback.answer("Нет доступа к этой записи", show_alert=True)
        return
    if err == "stale" or not event_id:
        await callback.answer("Список устарел, откройте заново", show_alert=True)
        return

    result = await load_admin_booking_detail(
        event_id=event_id,
        is_calendar_available=is_calendar_available,
        get_event=svc_get_event,
        extract_contact_details=_extract_booking_contact_details,
        normalize_phone=_normalize_phone,
        client_repo=client_repo,
    )
    if result.status != "ok":
        await callback.answer(result.text, show_alert=True)
        return

    booking_token = register_admin_booking_token(callback.from_user.id, event_id)
    await callback.message.edit_text(
        result.text,
        reply_markup=get_admin_booking_detail_keyboard(result.chat_target_user_id, None, booking_token),
        parse_mode="HTML",
    )

async def admin_booking_cancel(callback: CallbackQuery, is_admin: bool):
    """Отмена бронирования админом."""
    if not is_admin:
        await callback.answer("У вас нет прав администратора", show_alert=True)
        return

    token = callback.data.replace("admin_booking_cancel_", "", 1)
    event_id, err = resolve_admin_booking_token(token, callback.from_user.id)
    if err == "access_denied":
        await callback.answer("Нет доступа к этой записи", show_alert=True)
        return
    if err == "stale" or not event_id:
        await callback.answer("Список устарел, откройте заново", show_alert=True)
        return

    result = await cancel_admin_booking_event(
        event_id=event_id,
        is_calendar_available=is_calendar_available,
        list_events=svc_list_events,
        delete_event=svc_delete_event,
    )
    if result == "calendar_unavailable":
        await callback.answer("Календарь недоступен", show_alert=True)
        return
    if result != "ok":
        await callback.answer("Не удалось отменить бронирование", show_alert=True)
        return

    await callback.answer("✅ Бронирование отменено")
    await admin_bookings(callback, is_admin)

async def admin_services(callback: CallbackQuery, is_admin: bool):
    """Раздел услуг."""
    if not is_admin:
        await callback.answer("У вас нет прав администратора", show_alert=True)
        return

    services = await service_repo.get_all_active()
    await callback.message.edit_text(
        build_admin_services_text(services),
        reply_markup=get_services_management_keyboard(),
        parse_mode="HTML",
    )

async def admin_clients(callback: CallbackQuery, is_admin: bool):
    """Раздел клиентов."""
    if not is_admin:
        await callback.answer("У вас нет прав администратора", show_alert=True)
        return

    clients = await client_repo.get_all() if hasattr(client_repo, "get_all") else []
    client_rows: list[dict] = []
    for client in clients[:5]:
        telegram_label = None
        if client.telegram_id:
            telegram_label = "Без username"
            try:
                chat = await callback.bot.get_chat(client.telegram_id)
                if chat.username:
                    telegram_label = f"@{chat.username}"
            except Exception as exc:
                print(f"Не удалось получить username для client.telegram_id={client.telegram_id}: {exc}")

        client_rows.append({
            "name": client.name,
            "telegram_label": telegram_label,
            "phone_display": _format_phone_plus7(client.phone) if client.phone else None,
        })

    await callback.message.edit_text(
        build_admin_clients_text(client_rows),
        reply_markup=get_admin_keyboard(),
        parse_mode="HTML",
    )

async def admin_admins(callback: CallbackQuery, is_admin: bool):
    """Раздел администраторов."""
    if not is_admin:
        await callback.answer("У вас нет прав администратора", show_alert=True)
        return

    admins = await admin_repo.get_all()
    admin_rows: list[dict] = []
    for admin in admins:
        telegram_label = "Без username"
        if admin.telegram_id:
            try:
                chat = await callback.bot.get_chat(admin.telegram_id)
                if chat.username:
                    telegram_label = f"@{chat.username}"
            except Exception as exc:
                print(f"Не удалось получить username для admin.telegram_id={admin.telegram_id}: {exc}")

        admin_rows.append({
            "id": admin.id,
            "telegram_label": telegram_label,
            "vk_label": admin.vk_id or "Не указан",
            "is_active": admin.is_active,
        })

    await callback.message.edit_text(
        build_admin_admins_text(admin_rows),
        reply_markup=get_admin_keyboard(),
        parse_mode="HTML",
    )

async def bookings_today(callback: CallbackQuery, is_admin: bool):
    """Бронирования на сегодня"""
    if not is_admin:
        await callback.answer("У вас нет прав администратора", show_alert=True)
        return

    today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    tomorrow = today + timedelta(days=1)
    result = await load_admin_period_bookings(
        title=f"Бронирования на сегодня ({today.strftime('%d.%m.%Y')})",
        empty_text="На сегодня бронирований нет.",
        period_start=today,
        period_end=tomorrow,
        is_calendar_available=is_calendar_available,
        list_events=svc_list_events,
    )

    await callback.message.edit_text(
        result.text,
        reply_markup=get_bookings_management_keyboard(),
        parse_mode="HTML",
    )

async def bookings_tomorrow(callback: CallbackQuery, is_admin: bool):
    """Бронирования на завтра"""
    if not is_admin:
        await callback.answer("У вас нет прав администратора", show_alert=True)
        return

    tomorrow = (datetime.now() + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
    day_after = tomorrow + timedelta(days=1)
    result = await load_admin_period_bookings(
        title=f"Бронирования на завтра ({tomorrow.strftime('%d.%m.%Y')})",
        empty_text="На завтра бронирований нет.",
        period_start=tomorrow,
        period_end=day_after,
        is_calendar_available=is_calendar_available,
        list_events=svc_list_events,
    )

    await callback.message.edit_text(
        result.text,
        reply_markup=get_bookings_management_keyboard(),
        parse_mode="HTML",
    )

async def bookings_week(callback: CallbackQuery, is_admin: bool):
    """Бронирования на неделю"""
    if not is_admin:
        await callback.answer("У вас нет прав администратора", show_alert=True)
        return

    today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    week_later = today + timedelta(days=7)
    result = await load_admin_period_bookings(
        title="Бронирования на неделю",
        empty_text="На ближайшие 7 дней бронирований нет.",
        period_start=today,
        period_end=week_later,
        is_calendar_available=is_calendar_available,
        list_events=svc_list_events,
        max_results=100,
        include_date=True,
    )

    await callback.message.edit_text(
        result.text,
        reply_markup=get_bookings_management_keyboard(),
        parse_mode="HTML",
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
    """Поиск бронирований по текстовому запросу."""
    if not is_admin:
        await state.clear()
        await message.answer("У вас нет прав администратора")
        return

    result = await search_admin_bookings(
        query=message.text or "",
        is_calendar_available=is_calendar_available,
        list_events=svc_list_events,
    )

    if result.status == "validation_error":
        await message.answer(result.text)
        return

    await state.clear()
    await message.answer(
        result.text,
        reply_markup=get_bookings_management_keyboard(),
        parse_mode="HTML" if "<b>" in result.text else None,
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
