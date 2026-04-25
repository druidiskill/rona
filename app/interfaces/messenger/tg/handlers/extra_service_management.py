from __future__ import annotations

from aiogram import Dispatcher, F
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from app.core.modules.admin.extra_service_crud import (
    build_extra_service_model,
    build_extra_service_save_summary,
    build_extra_service_save_text,
    get_missing_extra_service_field_labels,
)
from app.core.modules.admin.extra_service_editor import (
    build_add_extra_service_editor_text,
    build_edit_extra_service_editor_text,
    get_extra_service_field_prompt,
    parse_sort_order,
)
from app.core.modules.admin.service_extras import cleanup_deleted_extra_service
from app.core.modules.admin.service_editor_state import update_nested_state_data
from app.integrations.local.db import extra_service_repo, service_repo
from app.interfaces.messenger.tg.keyboards import (
    get_extra_service_edit_keyboard,
    get_extra_service_editor_keyboard,
    get_extra_services_list_keyboard,
    get_extra_services_management_keyboard,
)
from app.interfaces.messenger.tg.states import AdminStates


def _build_extra_service_card_text(extra_service) -> str:
    status = "✅ Активна" if extra_service.is_active else "❌ Неактивна"
    return (
        "📦 <b>Доп. услуга</b>\n\n"
        f"<b>Название:</b> {extra_service.name}\n"
        f"<b>Описание:</b> {extra_service.description or 'Не указано'}\n"
        f"<b>Цена / подпись:</b> {extra_service.price_text or 'Не указано'}\n"
        f"<b>Порядок:</b> {extra_service.sort_order}\n"
        f"<b>Статус:</b> {status}"
    )


async def show_extra_services_management(callback: CallbackQuery, is_admin: bool):
    if not is_admin:
        await callback.answer("У вас нет прав администратора", show_alert=True)
        return

    extra_services = await extra_service_repo.get_all()
    text = "📦 <b>Управление доп. услугами</b>\n\n"
    if not extra_services:
        text += "Доп. услуг пока нет."
    else:
        for extra_service in extra_services:
            status = "✅ Активна" if extra_service.is_active else "❌ Неактивна"
            text += (
                f"📦 <b>{extra_service.name}</b>\n"
                f"💰 {extra_service.price_text or 'Не указано'}\n"
                f"🔢 Порядок: {extra_service.sort_order}\n"
                f"📊 {status}\n\n"
            )

    await callback.message.edit_text(
        text,
        reply_markup=get_extra_services_management_keyboard(),
        parse_mode="HTML",
    )


async def show_extra_services_list(callback: CallbackQuery, is_admin: bool):
    if not is_admin:
        await callback.answer("У вас нет прав администратора", show_alert=True)
        return

    extra_services = await extra_service_repo.get_all()
    if not extra_services:
        await callback.message.edit_text(
            "📦 <b>Доп. услуги не найдены</b>\n\nДобавьте первую доп. услугу.",
            reply_markup=get_extra_services_management_keyboard(),
            parse_mode="HTML",
        )
        return

    await callback.message.edit_text(
        "📦 <b>Выберите доп. услугу для редактирования:</b>",
        reply_markup=get_extra_services_list_keyboard(extra_services),
        parse_mode="HTML",
    )


async def show_extra_service_edit(callback: CallbackQuery, is_admin: bool):
    if not is_admin:
        await callback.answer("У вас нет прав администратора", show_alert=True)
        return

    try:
        extra_service_id = int(callback.data.split("_")[-1])
    except (TypeError, ValueError, IndexError):
        await callback.answer("Ошибка в данных", show_alert=True)
        return

    extra_service = await extra_service_repo.get_by_id(extra_service_id)
    if not extra_service:
        await callback.answer("Доп. услуга не найдена", show_alert=True)
        return

    await callback.message.edit_text(
        _build_extra_service_card_text(extra_service),
        reply_markup=get_extra_service_edit_keyboard(extra_service_id, extra_service.is_active),
        parse_mode="HTML",
    )


async def toggle_extra_service_active(callback: CallbackQuery, is_admin: bool):
    if not is_admin:
        await callback.answer("У вас нет прав администратора", show_alert=True)
        return

    extra_service_id = int(callback.data.split("_")[-1])
    extra_service = await extra_service_repo.get_by_id(extra_service_id)
    if not extra_service:
        await callback.answer("Доп. услуга не найдена", show_alert=True)
        return

    extra_service.is_active = not extra_service.is_active
    await extra_service_repo.update(extra_service)
    status_text = "активирована" if extra_service.is_active else "деактивирована"
    await callback.answer(f"✅ Доп. услуга '{extra_service.name}' {status_text}", show_alert=True)
    await show_extra_services_management(callback, is_admin)


async def remove_extra_service(callback: CallbackQuery, is_admin: bool):
    if not is_admin:
        await callback.answer("У вас нет прав администратора", show_alert=True)
        return

    extra_service_id = int(callback.data.split("_")[-1])
    extra_service = await extra_service_repo.get_by_id(extra_service_id)
    if not extra_service:
        await callback.answer("Доп. услуга не найдена", show_alert=True)
        return

    affected_services = await cleanup_deleted_extra_service(service_repo, extra_service_id)
    await extra_service_repo.delete(extra_service_id)
    suffix = f" Удалена из {affected_services} услуг." if affected_services else ""
    await callback.answer(
        f"✅ Доп. услуга '{extra_service.name}' удалена.{suffix}",
        show_alert=True,
    )
    await show_extra_services_management(callback, is_admin)


async def start_add_extra_service(callback: CallbackQuery, state: FSMContext, is_admin: bool):
    if not is_admin:
        await callback.answer("У вас нет прав администратора", show_alert=True)
        return

    await state.clear()
    await state.update_data(new_extra_service_data={})
    await callback.message.edit_text(
        build_add_extra_service_editor_text({}),
        reply_markup=get_extra_service_editor_keyboard("add"),
        parse_mode="HTML",
    )


async def start_edit_extra_service_new(callback: CallbackQuery, state: FSMContext, is_admin: bool):
    if not is_admin:
        await callback.answer("У вас нет прав администратора", show_alert=True)
        return

    extra_service_id = int(callback.data.split("_")[-1])
    extra_service = await extra_service_repo.get_by_id(extra_service_id)
    if not extra_service:
        await callback.answer("Доп. услуга не найдена", show_alert=True)
        return

    extra_service_data = {
        "name": extra_service.name,
        "description": extra_service.description,
        "price_text": extra_service.price_text,
        "sort_order": extra_service.sort_order,
        "is_active": extra_service.is_active,
    }
    await state.update_data(edit_extra_service_id=extra_service_id, edit_extra_service_data=extra_service_data)
    await callback.message.edit_text(
        build_edit_extra_service_editor_text(extra_service_data),
        reply_markup=get_extra_service_editor_keyboard("edit", extra_service_id),
        parse_mode="HTML",
    )


async def _show_add_extra_service_main(message_or_callback, state: FSMContext):
    data = await state.get_data()
    extra_service_data = data.get("new_extra_service_data", {})
    text = build_add_extra_service_editor_text(extra_service_data)
    keyboard = get_extra_service_editor_keyboard("add")
    if isinstance(message_or_callback, CallbackQuery):
        await message_or_callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
    else:
        await message_or_callback.answer(text, reply_markup=keyboard, parse_mode="HTML")


async def _show_edit_extra_service_main(message_or_callback, state: FSMContext):
    data = await state.get_data()
    extra_service_data = data.get("edit_extra_service_data", {})
    extra_service_id = data.get("edit_extra_service_id")
    text = build_edit_extra_service_editor_text(extra_service_data)
    keyboard = get_extra_service_editor_keyboard("edit", extra_service_id)
    if isinstance(message_or_callback, CallbackQuery):
        await message_or_callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
    else:
        await message_or_callback.answer(text, reply_markup=keyboard, parse_mode="HTML")


async def add_extra_service_field(callback: CallbackQuery, state: FSMContext, is_admin: bool):
    if not is_admin:
        await callback.answer("У вас нет прав администратора", show_alert=True)
        return

    field = callback.data.replace("add_extra_service_", "", 1)
    state_map = {
        "name": AdminStates.waiting_for_new_extra_service_name,
        "description": AdminStates.waiting_for_new_extra_service_description,
        "price_text": AdminStates.waiting_for_new_extra_service_price_text,
        "sort_order": AdminStates.waiting_for_new_extra_service_sort_order,
    }
    await callback.message.edit_text(get_extra_service_field_prompt("add", field), parse_mode="HTML")
    await state.set_state(state_map[field])


async def edit_extra_service_field(callback: CallbackQuery, state: FSMContext, is_admin: bool):
    if not is_admin:
        await callback.answer("У вас нет прав администратора", show_alert=True)
        return

    field = callback.data.replace("edit_extra_service_", "", 1)
    state_map = {
        "name": AdminStates.waiting_for_edit_extra_service_name,
        "description": AdminStates.waiting_for_edit_extra_service_description,
        "price_text": AdminStates.waiting_for_edit_extra_service_price_text,
        "sort_order": AdminStates.waiting_for_edit_extra_service_sort_order,
    }
    await callback.message.edit_text(get_extra_service_field_prompt("edit", field), parse_mode="HTML")
    await state.set_state(state_map[field])


async def process_new_extra_service_name(message: Message, state: FSMContext, is_admin: bool):
    if not is_admin:
        return
    await update_nested_state_data(state, "new_extra_service_data", {}, field_name="name", field_value=message.text.strip())
    await _show_add_extra_service_main(message, state)


async def process_new_extra_service_description(message: Message, state: FSMContext, is_admin: bool):
    if not is_admin:
        return
    await update_nested_state_data(
        state,
        "new_extra_service_data",
        {},
        field_name="description",
        field_value=message.text.strip(),
    )
    await _show_add_extra_service_main(message, state)


async def process_new_extra_service_price_text(message: Message, state: FSMContext, is_admin: bool):
    if not is_admin:
        return
    await update_nested_state_data(
        state,
        "new_extra_service_data",
        {},
        field_name="price_text",
        field_value=message.text.strip(),
    )
    await _show_add_extra_service_main(message, state)


async def process_new_extra_service_sort_order(message: Message, state: FSMContext, is_admin: bool):
    if not is_admin:
        return
    try:
        sort_order = parse_sort_order(message.text)
    except ValueError:
        await message.answer("❌ Введите целое число для порядка.")
        return
    await update_nested_state_data(
        state,
        "new_extra_service_data",
        {},
        field_name="sort_order",
        field_value=sort_order,
    )
    await _show_add_extra_service_main(message, state)


async def process_edit_extra_service_name(message: Message, state: FSMContext, is_admin: bool):
    if not is_admin:
        return
    await update_nested_state_data(state, "edit_extra_service_data", {}, field_name="name", field_value=message.text.strip())
    await _show_edit_extra_service_main(message, state)


async def process_edit_extra_service_description(message: Message, state: FSMContext, is_admin: bool):
    if not is_admin:
        return
    await update_nested_state_data(
        state,
        "edit_extra_service_data",
        {},
        field_name="description",
        field_value=message.text.strip(),
    )
    await _show_edit_extra_service_main(message, state)


async def process_edit_extra_service_price_text(message: Message, state: FSMContext, is_admin: bool):
    if not is_admin:
        return
    await update_nested_state_data(
        state,
        "edit_extra_service_data",
        {},
        field_name="price_text",
        field_value=message.text.strip(),
    )
    await _show_edit_extra_service_main(message, state)


async def process_edit_extra_service_sort_order(message: Message, state: FSMContext, is_admin: bool):
    if not is_admin:
        return
    try:
        sort_order = parse_sort_order(message.text)
    except ValueError:
        await message.answer("❌ Введите целое число для порядка.")
        return
    await update_nested_state_data(
        state,
        "edit_extra_service_data",
        {},
        field_name="sort_order",
        field_value=sort_order,
    )
    await _show_edit_extra_service_main(message, state)


async def save_new_extra_service(callback: CallbackQuery, state: FSMContext, is_admin: bool):
    if not is_admin:
        await callback.answer("У вас нет прав администратора", show_alert=True)
        return

    data = await state.get_data()
    extra_service_data = data.get("new_extra_service_data", {})
    missing = get_missing_extra_service_field_labels(extra_service_data)
    if missing:
        await callback.answer("Не все поля заполнены", show_alert=True)
        await callback.message.answer(
            f"⚠️ <b>Не все поля заполнены</b>\n\nЗаполните: {', '.join(missing)}",
            parse_mode="HTML",
        )
        return

    extra_service = build_extra_service_model(extra_service_data)
    extra_service_id = await extra_service_repo.create(extra_service)
    summary = build_extra_service_save_summary(
        extra_service,
        title="Доп. услуга успешно создана!",
        extra_service_id=extra_service_id,
    )
    await state.clear()
    await callback.message.edit_text(
        build_extra_service_save_text(summary),
        reply_markup=get_extra_services_management_keyboard(),
        parse_mode="HTML",
    )


async def save_edit_extra_service(callback: CallbackQuery, state: FSMContext, is_admin: bool):
    if not is_admin:
        await callback.answer("У вас нет прав администратора", show_alert=True)
        return

    data = await state.get_data()
    extra_service_id = data.get("edit_extra_service_id")
    extra_service_data = data.get("edit_extra_service_data", {})
    missing = get_missing_extra_service_field_labels(extra_service_data)
    if missing:
        await callback.answer("Не все поля заполнены", show_alert=True)
        await callback.message.answer(
            f"⚠️ <b>Не все поля заполнены</b>\n\nЗаполните: {', '.join(missing)}",
            parse_mode="HTML",
        )
        return

    extra_service = build_extra_service_model(extra_service_data, extra_service_id=extra_service_id)
    extra_service.is_active = bool(extra_service_data.get("is_active", True))
    await extra_service_repo.update(extra_service)
    summary = build_extra_service_save_summary(
        extra_service,
        title="Доп. услуга успешно обновлена!",
        extra_service_id=extra_service_id,
    )
    await state.clear()
    await callback.message.edit_text(
        build_extra_service_save_text(summary),
        reply_markup=get_extra_services_management_keyboard(),
        parse_mode="HTML",
    )


def register_extra_service_management_handlers(dp: Dispatcher):
    dp.callback_query.register(show_extra_services_management, F.data == "admin_extra_services")
    dp.callback_query.register(show_extra_services_list, F.data == "edit_extra_service")
    dp.callback_query.register(show_extra_service_edit, F.data.regexp(r"^edit_extra_service_\d+$"))
    dp.callback_query.register(toggle_extra_service_active, F.data.startswith("toggle_extra_service_active_"))
    dp.callback_query.register(remove_extra_service, F.data.startswith("remove_extra_service_"))

    dp.callback_query.register(start_add_extra_service, F.data == "add_extra_service")
    dp.callback_query.register(start_edit_extra_service_new, F.data.startswith("edit_extra_service_new_"))
    dp.callback_query.register(add_extra_service_field, F.data.in_({
        "add_extra_service_name",
        "add_extra_service_description",
        "add_extra_service_price_text",
        "add_extra_service_sort_order",
    }))
    dp.callback_query.register(edit_extra_service_field, F.data.in_({
        "edit_extra_service_name",
        "edit_extra_service_description",
        "edit_extra_service_price_text",
        "edit_extra_service_sort_order",
    }))
    dp.callback_query.register(save_new_extra_service, F.data == "add_extra_service_save")
    dp.callback_query.register(save_edit_extra_service, F.data == "edit_extra_service_save")

    dp.message.register(process_new_extra_service_name, AdminStates.waiting_for_new_extra_service_name)
    dp.message.register(process_new_extra_service_description, AdminStates.waiting_for_new_extra_service_description)
    dp.message.register(process_new_extra_service_price_text, AdminStates.waiting_for_new_extra_service_price_text)
    dp.message.register(process_new_extra_service_sort_order, AdminStates.waiting_for_new_extra_service_sort_order)
    dp.message.register(process_edit_extra_service_name, AdminStates.waiting_for_edit_extra_service_name)
    dp.message.register(process_edit_extra_service_description, AdminStates.waiting_for_edit_extra_service_description)
    dp.message.register(process_edit_extra_service_price_text, AdminStates.waiting_for_edit_extra_service_price_text)
    dp.message.register(process_edit_extra_service_sort_order, AdminStates.waiting_for_edit_extra_service_sort_order)
