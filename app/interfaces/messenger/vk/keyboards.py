from vkbottle import Keyboard, KeyboardButtonColor, Text


def get_main_menu_keyboard(is_admin: bool = False) -> str:
    keyboard = Keyboard(one_time=False, inline=False)
    keyboard.add(Text("📸 Услуги"), color=KeyboardButtonColor.PRIMARY).row()
    keyboard.add(Text("📅 Мои бронирования"), color=KeyboardButtonColor.PRIMARY).row()
    keyboard.add(Text("📞 Контакты"), color=KeyboardButtonColor.SECONDARY).row()
    keyboard.add(Text("ℹ️ Помощь"), color=KeyboardButtonColor.SECONDARY)
    if is_admin:
        keyboard.row().add(Text("🔧 Админ-панель"), color=KeyboardButtonColor.NEGATIVE)
    return keyboard.get_json()


def get_back_to_main_keyboard(is_admin: bool = False) -> str:
    return get_main_menu_keyboard(is_admin=is_admin)


def _truncate_label(text: str, max_length: int = 40) -> str:
    text = (text or "").strip()
    if len(text) <= max_length:
        return text
    return text[: max_length - 3].rstrip() + "..."


def _has_photographer_extra(event: dict) -> bool:
    description = (event.get("description") or "").lower()
    return (
        "нужен ли фотограф?" in description and "да" in description
    ) or ("дополнительные услуги" in description and "фотограф" in description)


def _display_summary_for_list_button(event: dict) -> str:
    summary = (event.get("summary") or "Без названия").strip()
    prefix = "Фотосессия:"
    if summary.startswith(prefix) and not _has_photographer_extra(event):
        cleaned = summary[len(prefix):].strip()
        return cleaned or "Без названия"
    return summary


def get_my_bookings_keyboard() -> str:
    keyboard = Keyboard(one_time=False, inline=False)
    keyboard.add(Text("📅 Активные", payload={"a": "mb_active", "p": 0}), color=KeyboardButtonColor.PRIMARY).row()
    keyboard.add(Text("🕘 История", payload={"a": "mb_history", "p": 0}), color=KeyboardButtonColor.PRIMARY).row()
    keyboard.add(Text("🔙 Назад", payload={"a": "mb_back"}), color=KeyboardButtonColor.SECONDARY)
    return keyboard.get_json()


def get_active_bookings_keyboard(events: list[dict], page: int, total_pages: int) -> str:
    keyboard = Keyboard(one_time=False, inline=False)
    for event in events:
        event_id = event.get("id")
        start = event.get("start")
        if not event_id or not start:
            continue
        summary = _display_summary_for_list_button(event)
        text = _truncate_label(f"✏️ {start.strftime('%d.%m %H:%M')} {summary}")
        keyboard.add(
            Text(text, payload={"a": "mb_open", "id": event_id, "p": page}),
            color=KeyboardButtonColor.PRIMARY,
        ).row()

    if total_pages > 1:
        if page > 0:
            keyboard.add(Text("⬅️", payload={"a": "mb_active", "p": page - 1}), color=KeyboardButtonColor.SECONDARY)
        if page < total_pages - 1:
            keyboard.add(Text("➡️", payload={"a": "mb_active", "p": page + 1}), color=KeyboardButtonColor.SECONDARY)
        keyboard.row()

    keyboard.add(Text("🔙 К разделам", payload={"a": "mb_menu"}), color=KeyboardButtonColor.SECONDARY)
    return keyboard.get_json()


def get_booking_history_keyboard(page: int, total_pages: int) -> str:
    keyboard = Keyboard(one_time=False, inline=False)
    if total_pages > 1:
        if page > 0:
            keyboard.add(Text("⬅️", payload={"a": "mb_history", "p": page - 1}), color=KeyboardButtonColor.SECONDARY)
        if page < total_pages - 1:
            keyboard.add(Text("➡️", payload={"a": "mb_history", "p": page + 1}), color=KeyboardButtonColor.SECONDARY)
        keyboard.row()
    keyboard.add(Text("🔙 К разделам", payload={"a": "mb_menu"}), color=KeyboardButtonColor.SECONDARY)
    return keyboard.get_json()


def get_active_booking_actions_keyboard(event_id: str, page: int) -> str:
    keyboard = Keyboard(one_time=False, inline=False)
    keyboard.add(
        Text("❌ Отменить бронирование", payload={"a": "mb_cancel", "id": event_id, "p": page}),
        color=KeyboardButtonColor.NEGATIVE,
    ).row()
    keyboard.add(Text("🔙 К активным", payload={"a": "mb_active", "p": page}), color=KeyboardButtonColor.SECONDARY)
    return keyboard.get_json()


def get_admin_keyboard() -> str:
    keyboard = Keyboard(one_time=False, inline=False)
    keyboard.add(Text("📅 Бронирования", payload={"a": "adm_bookings"}), color=KeyboardButtonColor.PRIMARY).row()
    keyboard.add(Text("📸 Услуги", payload={"a": "adm_services"}), color=KeyboardButtonColor.PRIMARY).row()
    keyboard.add(Text("👥 Клиенты", payload={"a": "adm_clients"}), color=KeyboardButtonColor.PRIMARY).row()
    keyboard.add(Text("👨‍💼 Администраторы", payload={"a": "adm_admins"}), color=KeyboardButtonColor.PRIMARY).row()
    keyboard.add(Text("❓ Помощь", payload={"a": "adm_help"}), color=KeyboardButtonColor.SECONDARY).row()
    keyboard.add(Text("🔙 Главное меню", payload={"a": "adm_back_main"}), color=KeyboardButtonColor.SECONDARY)
    return keyboard.get_json()


def get_admin_bookings_keyboard() -> str:
    keyboard = Keyboard(one_time=False, inline=False)
    keyboard.add(Text("📅 Будущие", payload={"a": "adm_bookings"}), color=KeyboardButtonColor.PRIMARY).row()
    keyboard.add(Text("📅 Сегодня", payload={"a": "adm_day", "d": "today"}), color=KeyboardButtonColor.PRIMARY)
    keyboard.add(Text("📅 Завтра", payload={"a": "adm_day", "d": "tomorrow"}), color=KeyboardButtonColor.PRIMARY).row()
    keyboard.add(Text("📅 Неделя", payload={"a": "adm_day", "d": "week"}), color=KeyboardButtonColor.PRIMARY).row()
    keyboard.add(Text("🔍 Поиск", payload={"a": "adm_booking_search"}), color=KeyboardButtonColor.SECONDARY).row()
    keyboard.add(Text("🔙 Назад", payload={"a": "adm_panel"}), color=KeyboardButtonColor.SECONDARY)
    return keyboard.get_json()


def get_admin_future_bookings_keyboard(
    events: list[dict],
    user_id: int,
    register_token,
    *,
    page: int,
    total_pages: int,
) -> str:
    keyboard = Keyboard(one_time=False, inline=False)
    for event in events:
        event_id = event.get("id")
        start = event.get("start")
        if not event_id or not start:
            continue
        token = register_token(user_id, event_id)
        summary = _display_summary_for_list_button(event)
        label = _truncate_label(f"🕐 {start.strftime('%d.%m %H:%M')} {summary}")
        keyboard.add(
            Text(label, payload={"a": "adm_booking_open", "t": token, "p": page}),
            color=KeyboardButtonColor.PRIMARY,
        ).row()
    if total_pages > 1:
        if page > 0:
            keyboard.add(Text("⬅️", payload={"a": "adm_bookings", "p": page - 1}), color=KeyboardButtonColor.SECONDARY)
        if page < total_pages - 1:
            keyboard.add(Text("➡️", payload={"a": "adm_bookings", "p": page + 1}), color=KeyboardButtonColor.SECONDARY)
        keyboard.row()
    keyboard.add(Text("🔙 К бронированиям", payload={"a": "adm_bookings_menu"}), color=KeyboardButtonColor.SECONDARY)
    return keyboard.get_json()


def get_admin_booking_detail_keyboard(token: str, page: int = 0) -> str:
    keyboard = Keyboard(one_time=False, inline=False)
    keyboard.add(
        Text("❌ Отменить бронирование", payload={"a": "adm_booking_cancel", "t": token, "p": page}),
        color=KeyboardButtonColor.NEGATIVE,
    ).row()
    keyboard.add(Text("🔙 К бронированиям", payload={"a": "adm_bookings", "p": page}), color=KeyboardButtonColor.SECONDARY)
    keyboard.add(Text("🔙 В админ-панель", payload={"a": "adm_panel"}), color=KeyboardButtonColor.SECONDARY)
    return keyboard.get_json()


def get_admin_services_keyboard() -> str:
    keyboard = Keyboard(one_time=False, inline=False)
    keyboard.add(Text("➕ Добавить услугу", payload={"a": "adm_service_add"}), color=KeyboardButtonColor.POSITIVE).row()
    keyboard.add(Text("📋 Список услуг", payload={"a": "adm_services_list"}), color=KeyboardButtonColor.PRIMARY).row()
    keyboard.add(Text("🔙 Назад", payload={"a": "adm_panel"}), color=KeyboardButtonColor.SECONDARY)
    return keyboard.get_json()


def get_admin_services_list_keyboard(services: list) -> str:
    keyboard = Keyboard(one_time=False, inline=False)
    for service in services:
        label = _truncate_label(f"📸 {service.name}")
        keyboard.add(
            Text(label, payload={"a": "adm_service_open", "id": service.id}),
            color=KeyboardButtonColor.PRIMARY,
        ).row()
    keyboard.add(Text("🔙 К услугам", payload={"a": "adm_services"}), color=KeyboardButtonColor.SECONDARY)
    return keyboard.get_json()


def get_admin_service_detail_keyboard(service_id: int, is_active: bool) -> str:
    keyboard = Keyboard(one_time=False, inline=False)
    keyboard.add(
        Text("✏️ Редактировать", payload={"a": "adm_service_edit", "id": service_id}),
        color=KeyboardButtonColor.PRIMARY,
    ).row()
    keyboard.add(
        Text(
            "🗑️ Деактивировать" if is_active else "✅ Активировать",
            payload={"a": "adm_service_toggle", "id": service_id},
        ),
        color=KeyboardButtonColor.NEGATIVE if is_active else KeyboardButtonColor.POSITIVE,
    ).row()
    keyboard.add(Text("🔙 К списку услуг", payload={"a": "adm_services_list"}), color=KeyboardButtonColor.SECONDARY)
    keyboard.add(Text("🔙 В админ-панель", payload={"a": "adm_panel"}), color=KeyboardButtonColor.SECONDARY)
    return keyboard.get_json()


def get_admin_service_editor_keyboard(mode: str, service_id: int | None = None) -> str:
    keyboard = Keyboard(one_time=False, inline=False)
    keyboard.add(Text("📝 Название", payload={"a": "adm_service_field", "m": mode, "f": "name"}), color=KeyboardButtonColor.PRIMARY).row()
    keyboard.add(Text("📄 Описание", payload={"a": "adm_service_field", "m": mode, "f": "description"}), color=KeyboardButtonColor.PRIMARY).row()
    keyboard.add(Text("💰 Цены", payload={"a": "adm_service_price_menu", "m": mode}), color=KeyboardButtonColor.PRIMARY).row()
    keyboard.add(Text("👥 Макс. людей", payload={"a": "adm_service_field", "m": mode, "f": "max_clients"}), color=KeyboardButtonColor.PRIMARY).row()
    keyboard.add(Text("🔧 Доп. услуги", payload={"a": "adm_service_extras", "m": mode}), color=KeyboardButtonColor.PRIMARY).row()
    keyboard.add(Text("⏰ Длительность", payload={"a": "adm_service_field", "m": mode, "f": "duration"}), color=KeyboardButtonColor.PRIMARY).row()
    keyboard.add(Text("📸 Фото", payload={"a": "adm_service_field", "m": mode, "f": "photos"}), color=KeyboardButtonColor.PRIMARY).row()
    keyboard.add(
        Text("✅ Создать" if mode == "add" else "💾 Сохранить", payload={"a": "adm_service_save", "m": mode}),
        color=KeyboardButtonColor.POSITIVE,
    ).row()
    if mode == "edit" and service_id:
        keyboard.add(Text("🔙 К услуге", payload={"a": "adm_service_open", "id": service_id}), color=KeyboardButtonColor.SECONDARY)
    else:
        keyboard.add(Text("🔙 К услугам", payload={"a": "adm_services"}), color=KeyboardButtonColor.SECONDARY)
    return keyboard.get_json()


def get_admin_service_price_keyboard(mode: str, service_id: int | None = None) -> str:
    keyboard = Keyboard(one_time=False, inline=False)
    keyboard.add(Text("💰 Будни", payload={"a": "adm_service_field", "m": mode, "f": "price_weekday"}), color=KeyboardButtonColor.PRIMARY).row()
    keyboard.add(Text("💰 Выходные", payload={"a": "adm_service_field", "m": mode, "f": "price_weekend"}), color=KeyboardButtonColor.PRIMARY).row()
    keyboard.add(Text("👤 Доп. будни", payload={"a": "adm_service_field", "m": mode, "f": "price_extra_weekday"}), color=KeyboardButtonColor.PRIMARY).row()
    keyboard.add(Text("👤 Доп. вых.", payload={"a": "adm_service_field", "m": mode, "f": "price_extra_weekend"}), color=KeyboardButtonColor.PRIMARY).row()
    keyboard.add(Text("👥 От 10 чел.", payload={"a": "adm_service_field", "m": mode, "f": "price_group"}), color=KeyboardButtonColor.PRIMARY).row()
    keyboard.add(Text("🔙 К редактированию", payload={"a": "adm_service_editor_back"}), color=KeyboardButtonColor.SECONDARY)
    return keyboard.get_json()


def get_admin_service_back_keyboard(mode: str, service_id: int | None = None) -> str:
    keyboard = Keyboard(one_time=False, inline=False)
    keyboard.add(Text("↩️ К редактированию", payload={"a": "adm_service_editor_back"}), color=KeyboardButtonColor.SECONDARY)
    return keyboard.get_json()


def get_admin_service_extras_keyboard(
    services: list,
    selected_ids: list[int],
    *,
    mode: str,
    service_id: int | None = None,
) -> str:
    keyboard = Keyboard(one_time=False, inline=False)
    for service in services:
        prefix = "✅ " if service.id in selected_ids else ""
        label = _truncate_label(f"{prefix}{service.name}")
        keyboard.add(
            Text(label, payload={"a": "adm_service_extra_toggle", "m": mode, "id": service.id}),
            color=KeyboardButtonColor.PRIMARY,
        ).row()
    keyboard.add(Text("Готово", payload={"a": "adm_service_extras_done", "m": mode}), color=KeyboardButtonColor.POSITIVE).row()
    keyboard.add(Text("🔙 К редактированию", payload={"a": "adm_service_editor_back"}), color=KeyboardButtonColor.SECONDARY)
    return keyboard.get_json()


def get_admin_help_keyboard() -> str:
    keyboard = Keyboard(one_time=False, inline=False)
    keyboard.add(Text("➕ Добавить вопрос", payload={"a": "adm_faq_add"}), color=KeyboardButtonColor.POSITIVE).row()
    keyboard.add(Text("🔙 Назад", payload={"a": "adm_panel"}), color=KeyboardButtonColor.SECONDARY)
    return keyboard.get_json()


def get_admin_faq_list_keyboard(items: list[tuple[int, str, bool]]) -> str:
    keyboard = Keyboard(one_time=False, inline=False)
    for faq_id, question, is_active in items:
        prefix = "✅" if is_active else "❌"
        label = _truncate_label(f"{prefix} {question}")
        keyboard.add(
            Text(label, payload={"a": "adm_faq_open", "id": faq_id}),
            color=KeyboardButtonColor.PRIMARY,
        ).row()
    keyboard.add(Text("➕ Добавить вопрос", payload={"a": "adm_faq_add"}), color=KeyboardButtonColor.POSITIVE).row()
    keyboard.add(Text("🔙 Назад", payload={"a": "adm_panel"}), color=KeyboardButtonColor.SECONDARY)
    return keyboard.get_json()


def get_admin_faq_detail_keyboard(faq_id: int, is_active: bool) -> str:
    keyboard = Keyboard(one_time=False, inline=False)
    keyboard.add(Text("✏️ Вопрос", payload={"a": "adm_faq_edit_q", "id": faq_id}), color=KeyboardButtonColor.PRIMARY).row()
    keyboard.add(Text("✏️ Ответ", payload={"a": "adm_faq_edit_a", "id": faq_id}), color=KeyboardButtonColor.PRIMARY).row()
    keyboard.add(
        Text(
            "❌ Деактивировать" if is_active else "✅ Активировать",
            payload={"a": "adm_faq_toggle", "id": faq_id},
        ),
        color=KeyboardButtonColor.NEGATIVE if is_active else KeyboardButtonColor.POSITIVE,
    ).row()
    keyboard.add(Text("🗑️ Удалить", payload={"a": "adm_faq_delete", "id": faq_id}), color=KeyboardButtonColor.NEGATIVE).row()
    keyboard.add(Text("🔙 Назад", payload={"a": "adm_help"}), color=KeyboardButtonColor.SECONDARY)
    return keyboard.get_json()
