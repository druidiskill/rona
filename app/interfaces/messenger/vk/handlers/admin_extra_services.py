from __future__ import annotations

import html
import re
from enum import Enum

from vkbottle import BaseStateGroup
from vkbottle.bot import Bot, Message

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
from app.integrations.local.db import extra_service_repo, service_repo
from app.interfaces.messenger.vk.auth import is_vk_admin_id
from app.interfaces.messenger.vk.keyboards import (
    get_admin_extra_service_back_keyboard,
    get_admin_extra_service_detail_keyboard,
    get_admin_extra_service_editor_keyboard,
    get_admin_extra_services_keyboard,
    get_admin_extra_services_list_keyboard,
    get_admin_services_keyboard,
)


class VkAdminExtraServiceState(BaseStateGroup, Enum):
    editor = "editor"
    waiting_for_text = "waiting_for_text"


def _plain(text: str) -> str:
    no_tags = re.sub(r"<[^>]+>", "", text or "")
    return html.unescape(no_tags).strip()


async def _is_admin(message: Message) -> bool:
    return await is_vk_admin_id(message.from_id)


def _payload(message: Message) -> dict:
    if message.state_peer and message.state_peer.payload:
        return dict(message.state_peer.payload)
    return {}


async def _deny(message: Message) -> None:
    await message.answer("У вас нет прав администратора.")


async def _set_editor_state(
    bot: Bot,
    message: Message,
    state: VkAdminExtraServiceState,
    *,
    mode: str,
    extra_service_data: dict,
    extra_service_id: int | None = None,
    field: str | None = None,
) -> None:
    payload = {"extra_editor_mode": mode, "extra_service_data": extra_service_data}
    if extra_service_id is not None:
        payload["extra_service_id"] = extra_service_id
    if field is not None:
        payload["extra_service_field"] = field
    await bot.state_dispenser.set(message.peer_id, state, **payload)


def _get_editor_context(message: Message) -> tuple[str | None, dict, int | None, str | None]:
    payload = _payload(message)
    mode = payload.get("extra_editor_mode")
    extra_service_data = dict(payload.get("extra_service_data", {}))
    raw_id = payload.get("extra_service_id")
    extra_service_id = int(raw_id) if raw_id is not None else None
    field = payload.get("extra_service_field")
    return mode, extra_service_data, extra_service_id, field


def _build_extra_service_card_text(extra_service) -> str:
    status = "✅ Активна" if extra_service.is_active else "❌ Неактивна"
    return (
        "📦 Доп. услуга\n\n"
        f"Название: {extra_service.name}\n"
        f"Описание: {extra_service.description or 'Не указано'}\n"
        f"Цена / подпись: {extra_service.price_text or 'Не указано'}\n"
        f"Порядок: {extra_service.sort_order}\n"
        f"Статус: {status}"
    )


async def _show_extra_services_management(message: Message) -> None:
    extra_services = await extra_service_repo.get_all()
    lines = ["📦 Управление доп. услугами", ""]
    if not extra_services:
        lines.append("Доп. услуг пока нет.")
    else:
        for extra_service in extra_services:
            status = "✅ Активна" if extra_service.is_active else "❌ Неактивна"
            lines.extend(
                [
                    f"📦 {extra_service.name}",
                    f"💰 {extra_service.price_text or 'Не указано'}",
                    f"🔢 Порядок: {extra_service.sort_order}",
                    f"📊 {status}",
                    "",
                ]
            )
    await message.answer("\n".join(lines), keyboard=get_admin_extra_services_keyboard())


async def _show_extra_services_list(message: Message) -> None:
    extra_services = await extra_service_repo.get_all()
    if not extra_services:
        await message.answer("Доп. услуг пока нет.", keyboard=get_admin_extra_services_keyboard())
        return
    await message.answer("📦 Выберите доп. услугу:", keyboard=get_admin_extra_services_list_keyboard(extra_services))


async def _show_extra_service_detail(message: Message, extra_service_id: int) -> None:
    extra_service = await extra_service_repo.get_by_id(extra_service_id)
    if not extra_service:
        await message.answer("Доп. услуга не найдена.", keyboard=get_admin_extra_services_keyboard())
        return
    await message.answer(
        _build_extra_service_card_text(extra_service),
        keyboard=get_admin_extra_service_detail_keyboard(extra_service_id, extra_service.is_active),
    )


async def _show_editor_main(
    bot: Bot,
    message: Message,
    *,
    mode: str,
    extra_service_data: dict,
    extra_service_id: int | None = None,
) -> None:
    await _set_editor_state(
        bot,
        message,
        VkAdminExtraServiceState.editor,
        mode=mode,
        extra_service_data=extra_service_data,
        extra_service_id=extra_service_id,
    )
    text = (
        build_add_extra_service_editor_text(extra_service_data)
        if mode == "add"
        else build_edit_extra_service_editor_text(extra_service_data)
    )
    await message.answer(
        _plain(text),
        keyboard=get_admin_extra_service_editor_keyboard(mode, extra_service_id),
    )


async def _save_field_input(bot: Bot, message: Message) -> None:
    mode, extra_service_data, extra_service_id, field = _get_editor_context(message)
    if not mode or not field:
        await bot.state_dispenser.delete(message.peer_id)
        await message.answer("Сессия редактирования устарела.", keyboard=get_admin_extra_services_keyboard())
        return

    raw_text = (message.text or "").strip()
    if not raw_text:
        await message.answer("Введите значение текстом.", keyboard=get_admin_extra_service_back_keyboard())
        return

    try:
        if field == "name":
            extra_service_data["name"] = raw_text
        elif field == "description":
            extra_service_data["description"] = raw_text
        elif field == "price_text":
            extra_service_data["price_text"] = raw_text
        elif field == "sort_order":
            extra_service_data["sort_order"] = parse_sort_order(raw_text)
        else:
            await message.answer("Поле не поддерживается.", keyboard=get_admin_extra_services_keyboard())
            return
    except ValueError:
        await message.answer("Неверный формат значения.", keyboard=get_admin_extra_service_back_keyboard())
        return

    await _show_editor_main(
        bot,
        message,
        mode=mode,
        extra_service_data=extra_service_data,
        extra_service_id=extra_service_id,
    )


async def _save_extra_service(bot: Bot, message: Message) -> None:
    mode, extra_service_data, extra_service_id, _ = _get_editor_context(message)
    if not mode:
        await bot.state_dispenser.delete(message.peer_id)
        await message.answer("Сессия редактирования устарела.", keyboard=get_admin_extra_services_keyboard())
        return

    missing_fields = get_missing_extra_service_field_labels(extra_service_data)
    if missing_fields:
        await message.answer(
            f"❌ Заполните обязательные поля: {', '.join(missing_fields)}",
            keyboard=get_admin_extra_service_editor_keyboard(mode, extra_service_id),
        )
        return

    if mode == "add":
        extra_service = build_extra_service_model(extra_service_data)
        created_id = await extra_service_repo.create(extra_service)
        summary = build_extra_service_save_summary(
            extra_service,
            title="Доп. услуга успешно создана!",
            extra_service_id=created_id,
        )
    else:
        if not extra_service_id:
            await message.answer("Не удалось определить доп. услугу.", keyboard=get_admin_extra_services_keyboard())
            return
        extra_service = build_extra_service_model(extra_service_data, extra_service_id=extra_service_id)
        extra_service.is_active = bool(extra_service_data.get("is_active", True))
        success = await extra_service_repo.update(extra_service)
        if not success:
            await message.answer("Не удалось обновить доп. услугу.", keyboard=get_admin_extra_services_keyboard())
            return
        summary = build_extra_service_save_summary(
            extra_service,
            title="Доп. услуга успешно обновлена!",
            extra_service_id=extra_service_id,
        )

    await bot.state_dispenser.delete(message.peer_id)
    await message.answer(
        _plain(build_extra_service_save_text(summary)),
        keyboard=get_admin_extra_services_keyboard(),
    )


async def _start_add_extra_service(bot: Bot, message: Message) -> None:
    await _show_editor_main(bot, message, mode="add", extra_service_data={})


async def _start_edit_extra_service(bot: Bot, message: Message, extra_service_id: int) -> None:
    extra_service = await extra_service_repo.get_by_id(extra_service_id)
    if not extra_service:
        await message.answer("Доп. услуга не найдена.", keyboard=get_admin_extra_services_keyboard())
        return
    extra_service_data = {
        "name": extra_service.name,
        "description": extra_service.description,
        "price_text": extra_service.price_text,
        "sort_order": extra_service.sort_order,
        "is_active": extra_service.is_active,
    }
    await _show_editor_main(
        bot,
        message,
        mode="edit",
        extra_service_data=extra_service_data,
        extra_service_id=extra_service_id,
    )


def register_admin_extra_service_handlers(bot: Bot) -> None:
    @bot.on.message(payload_contains={"a": "adm_extra_services"})
    async def admin_extra_services(message: Message):
        if not await _is_admin(message):
            await _deny(message)
            return
        await bot.state_dispenser.delete(message.peer_id)
        await _show_extra_services_management(message)

    @bot.on.message(payload_contains={"a": "adm_extra_services_list"})
    async def admin_extra_services_list(message: Message):
        if not await _is_admin(message):
            await _deny(message)
            return
        await bot.state_dispenser.delete(message.peer_id)
        await _show_extra_services_list(message)

    @bot.on.message(payload_contains={"a": "adm_extra_service_open"})
    async def admin_extra_service_open(message: Message):
        if not await _is_admin(message):
            await _deny(message)
            return
        payload = message.get_payload_json() or {}
        await _show_extra_service_detail(message, int(payload.get("id", 0)))

    @bot.on.message(payload_contains={"a": "adm_extra_service_toggle"})
    async def admin_extra_service_toggle(message: Message):
        if not await _is_admin(message):
            await _deny(message)
            return
        payload = message.get_payload_json() or {}
        extra_service = await extra_service_repo.get_by_id(int(payload.get("id", 0)))
        if not extra_service:
            await message.answer("Доп. услуга не найдена.", keyboard=get_admin_extra_services_keyboard())
            return
        extra_service.is_active = not extra_service.is_active
        await extra_service_repo.update(extra_service)
        await _show_extra_service_detail(message, int(payload.get("id", 0)))

    @bot.on.message(payload_contains={"a": "adm_extra_service_delete"})
    async def admin_extra_service_delete(message: Message):
        if not await _is_admin(message):
            await _deny(message)
            return
        payload = message.get_payload_json() or {}
        extra_service_id = int(payload.get("id", 0))
        extra_service = await extra_service_repo.get_by_id(extra_service_id)
        if not extra_service:
            await message.answer("Доп. услуга не найдена.", keyboard=get_admin_extra_services_keyboard())
            return
        affected_services = await cleanup_deleted_extra_service(service_repo, extra_service_id)
        await extra_service_repo.delete(extra_service_id)
        suffix = f"\nУдалена из {affected_services} услуг." if affected_services else ""
        await message.answer(
            f"Доп. услуга '{extra_service.name}' удалена.{suffix}",
            keyboard=get_admin_extra_services_keyboard(),
        )

    @bot.on.message(payload_contains={"a": "adm_extra_service_add"})
    async def admin_extra_service_add(message: Message):
        if not await _is_admin(message):
            await _deny(message)
            return
        await _start_add_extra_service(bot, message)

    @bot.on.message(payload_contains={"a": "adm_extra_service_edit"})
    async def admin_extra_service_edit(message: Message):
        if not await _is_admin(message):
            await _deny(message)
            return
        payload = message.get_payload_json() or {}
        await _start_edit_extra_service(bot, message, int(payload.get("id", 0)))

    @bot.on.message(payload_contains={"a": "adm_extra_service_editor_back"})
    async def admin_extra_service_editor_back(message: Message):
        if not await _is_admin(message):
            await _deny(message)
            return
        mode, extra_service_data, extra_service_id, _ = _get_editor_context(message)
        if not mode:
            await message.answer("Сессия редактирования устарела.", keyboard=get_admin_extra_services_keyboard())
            return
        await _show_editor_main(bot, message, mode=mode, extra_service_data=extra_service_data, extra_service_id=extra_service_id)

    @bot.on.message(payload_contains={"a": "adm_extra_service_field"})
    async def admin_extra_service_field(message: Message):
        if not await _is_admin(message):
            await _deny(message)
            return
        mode, extra_service_data, extra_service_id, _ = _get_editor_context(message)
        if not mode:
            await message.answer("Сессия редактирования устарела.", keyboard=get_admin_extra_services_keyboard())
            return
        payload = message.get_payload_json() or {}
        field = str(payload.get("f") or "")
        await _set_editor_state(
            bot,
            message,
            VkAdminExtraServiceState.waiting_for_text,
            mode=mode,
            extra_service_data=extra_service_data,
            extra_service_id=extra_service_id,
            field=field,
        )
        await message.answer(
            _plain(get_extra_service_field_prompt(mode, field)),
            keyboard=get_admin_extra_service_back_keyboard(),
        )

    @bot.on.message(payload_contains={"a": "adm_extra_service_save"})
    async def admin_extra_service_save(message: Message):
        if not await _is_admin(message):
            await _deny(message)
            return
        await _save_extra_service(bot, message)

    @bot.on.message(state=VkAdminExtraServiceState.waiting_for_text)
    async def admin_extra_service_text_input(message: Message):
        if not await _is_admin(message):
            await _deny(message)
            return
        await _save_field_input(bot, message)
