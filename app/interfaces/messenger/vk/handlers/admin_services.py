from __future__ import annotations

import html
import re
from enum import Enum

from vkbottle import BaseStateGroup
from vkbottle.bot import Bot, Message

from app.core.modules.admin.service_crud import (
    build_service_model,
    build_service_save_summary,
    build_service_save_text,
    get_missing_service_field_labels,
)
from app.core.modules.admin.service_editor import (
    build_add_service_editor_text,
    build_edit_service_editor_text,
    parse_duration_pair,
    parse_positive_int,
    parse_positive_price,
)
from app.core.modules.admin.service_extras import (
    format_selected_extras,
    get_active_extra_services,
    toggle_extra_service,
)
from app.core.modules.admin.service_photos import finalize_service_photo_dir, save_service_photo
from app.core.modules.admin.service_prompts import (
    ADMIN_DENIED_TEXT,
    get_service_extras_empty_text,
    get_service_extras_text,
    get_service_field_prompt,
    get_service_price_menu_text,
)
from app.integrations.local.db import service_repo
from app.interfaces.messenger.tg.utils.photos import (
    clear_dir,
    count_photos_in_dir,
    get_service_dir,
    get_temp_dir,
    move_dir_contents,
)
from app.interfaces.messenger.vk.auth import is_vk_admin_id
from app.interfaces.messenger.vk.keyboards import (
    get_admin_service_back_keyboard,
    get_admin_service_editor_keyboard,
    get_admin_service_extras_keyboard,
    get_admin_service_price_keyboard,
    get_admin_service_detail_keyboard,
    get_admin_services_keyboard,
)
from app.interfaces.messenger.vk.utils.photos import save_message_photo


class VkAdminServiceState(BaseStateGroup, Enum):
    service_editor = "service_editor"
    waiting_for_service_text = "waiting_for_service_text"
    waiting_for_service_photo = "waiting_for_service_photo"


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
    await message.answer(ADMIN_DENIED_TEXT)


def _normalize_plus_ids(value) -> list[int]:
    if value is None:
        return []
    if isinstance(value, int):
        return [value] if value > 0 else []
    if isinstance(value, str):
        parts = [part.strip() for part in value.split(",") if part.strip()]
        try:
            return [int(part) for part in parts]
        except ValueError:
            return []
    return []


async def _set_editor_state(
    bot: Bot,
    message: Message,
    state: VkAdminServiceState,
    *,
    mode: str,
    service_data: dict,
    service_id: int | None = None,
    field: str | None = None,
) -> None:
    payload = {
        "editor_mode": mode,
        "service_data": service_data,
    }
    if service_id is not None:
        payload["service_id"] = service_id
    if field is not None:
        payload["service_field"] = field
    await bot.state_dispenser.set(message.peer_id, state, **payload)


def _get_editor_context(message: Message) -> tuple[str | None, dict, int | None, str | None]:
    payload = _payload(message)
    mode = payload.get("editor_mode")
    service_data = dict(payload.get("service_data", {}))
    raw_service_id = payload.get("service_id")
    service_id = int(raw_service_id) if raw_service_id is not None else None
    field = payload.get("service_field")
    return mode, service_data, service_id, field


async def _show_editor_main(
    bot: Bot,
    message: Message,
    *,
    mode: str,
    service_data: dict,
    service_id: int | None = None,
) -> None:
    await _set_editor_state(
        bot,
        message,
        VkAdminServiceState.service_editor,
        mode=mode,
        service_data=service_data,
        service_id=service_id,
    )
    text = (
        build_add_service_editor_text(service_data)
        if mode == "add"
        else build_edit_service_editor_text(service_data)
    )
    await message.answer(
        _plain(text),
        keyboard=get_admin_service_editor_keyboard(mode, service_id),
    )


async def _show_price_menu(
    bot: Bot,
    message: Message,
    *,
    mode: str,
    service_data: dict,
    service_id: int | None = None,
) -> None:
    await _set_editor_state(
        bot,
        message,
        VkAdminServiceState.service_editor,
        mode=mode,
        service_data=service_data,
        service_id=service_id,
    )
    await message.answer(
        _plain(get_service_price_menu_text(mode)),
        keyboard=get_admin_service_price_keyboard(mode, service_id),
    )


async def _show_extras_picker(
    bot: Bot,
    message: Message,
    *,
    mode: str,
    service_data: dict,
    service_id: int | None = None,
) -> None:
    services = await service_repo.get_all()
    active_services = get_active_extra_services(
        services,
        exclude_service_id=service_id if mode == "edit" else None,
    )
    await _set_editor_state(
        bot,
        message,
        VkAdminServiceState.service_editor,
        mode=mode,
        service_data=service_data,
        service_id=service_id,
    )

    if not active_services:
        await message.answer(
            _plain(get_service_extras_empty_text()),
            keyboard=get_admin_service_editor_keyboard(mode, service_id),
        )
        return

    await message.answer(
        _plain(get_service_extras_text(mode)),
        keyboard=get_admin_service_extras_keyboard(
            active_services,
            service_data.get("extra_services", []),
            mode=mode,
            service_id=service_id,
        ),
    )


async def _build_edit_service_data(service_id: int) -> dict | None:
    service = await service_repo.get_by_id(service_id)
    if not service:
        return None

    services = await service_repo.get_all()
    extra_services = _normalize_plus_ids(service.plus_service_ids)
    return {
        "name": service.name,
        "description": service.description,
        "price_weekday": service.price_min,
        "price_weekend": service.price_min_weekend,
        "price_extra_weekday": service.price_for_extra_client,
        "price_extra_weekend": service.price_for_extra_client_weekend,
        "price_group": service.fix_price,
        "base_clients": service.base_num_clients,
        "max_clients": service.max_num_clients,
        "min_duration": service.min_duration_minutes,
        "step_duration": service.duration_step_minutes,
        "duration": f"{service.min_duration_minutes} мин (шаг {service.duration_step_minutes})",
        "extra_services": extra_services,
        "extras": format_selected_extras(extra_services, services),
        "photos_count": count_photos_in_dir(get_service_dir(service_id)),
        "photo_ids": service.photo_ids,
        "is_active": service.is_active,
    }


async def _start_add_service(bot: Bot, message: Message) -> None:
    clear_dir(get_temp_dir(message.from_id))
    await _show_editor_main(bot, message, mode="add", service_data={})


async def _start_edit_service(bot: Bot, message: Message, service_id: int) -> None:
    service_data = await _build_edit_service_data(service_id)
    if not service_data:
        await message.answer("Услуга не найдена.", keyboard=get_admin_services_keyboard())
        return
    await _show_editor_main(
        bot,
        message,
        mode="edit",
        service_data=service_data,
        service_id=service_id,
    )


async def _save_service_field_input(bot: Bot, message: Message) -> None:
    mode, service_data, service_id, field = _get_editor_context(message)
    if not mode or not field:
        await bot.state_dispenser.delete(message.peer_id)
        await message.answer("Сессия редактирования устарела.", keyboard=get_admin_services_keyboard())
        return

    raw_text = (message.text or "").strip()
    if not raw_text:
        await message.answer(
            "Введите значение текстом.",
            keyboard=get_admin_service_back_keyboard(mode, service_id),
        )
        return

    try:
        if field == "name":
            service_data["name"] = raw_text
        elif field == "description":
            service_data["description"] = raw_text
        elif field == "price_weekday":
            service_data["price_weekday"] = parse_positive_price(raw_text, allow_zero=mode == "edit")
        elif field == "price_weekend":
            service_data["price_weekend"] = parse_positive_price(raw_text, allow_zero=mode == "edit")
        elif field == "price_extra_weekday":
            service_data["price_extra_weekday"] = parse_positive_price(raw_text, allow_zero=True)
        elif field == "price_extra_weekend":
            service_data["price_extra_weekend"] = parse_positive_price(raw_text, allow_zero=True)
        elif field == "price_group":
            service_data["price_group"] = parse_positive_price(raw_text, allow_zero=True)
        elif field == "max_clients":
            service_data["max_clients"] = parse_positive_int(raw_text)
        elif field == "duration":
            min_duration, step_duration = parse_duration_pair(raw_text)
            service_data["min_duration"] = min_duration
            service_data["step_duration"] = step_duration
            service_data["duration"] = f"{min_duration} мин (шаг {step_duration})"
        else:
            await message.answer("Поле не поддерживается.", keyboard=get_admin_services_keyboard())
            return
    except ValueError:
        await message.answer(
            "Неверный формат значения.",
            keyboard=get_admin_service_back_keyboard(mode, service_id),
        )
        return

    await _show_editor_main(
        bot,
        message,
        mode=mode,
        service_data=service_data,
        service_id=service_id,
    )


async def _save_service_photo_input(bot: Bot, message: Message) -> None:
    mode, service_data, service_id, _ = _get_editor_context(message)
    if not mode:
        await bot.state_dispenser.delete(message.peer_id)
        await message.answer("Сессия редактирования устарела.", keyboard=get_admin_services_keyboard())
        return

    target_dir = get_temp_dir(message.from_id) if mode == "add" else get_service_dir(int(service_id or 0))
    try:
        photos_count = await save_service_photo(
            message,
            target_dir,
            save_photo_func=save_message_photo,
            count_photos_func=count_photos_in_dir,
            clear_dir_func=clear_dir if mode == "edit" else None,
            reset_before_save=mode == "edit" and not service_data.get("photos_updated"),
        )
    except Exception:
        await message.answer(
            "Не удалось сохранить фотографию. Отправьте фото ещё раз.",
            keyboard=get_admin_service_back_keyboard(mode, service_id),
        )
        return

    service_data["photos_count"] = photos_count
    if mode == "add":
        service_data["temp_photos_dir"] = str(target_dir)
    else:
        service_data["photos_updated"] = True

    await message.answer(f"✅ Фотография добавлена. Всего: {photos_count}")
    await _show_editor_main(
        bot,
        message,
        mode=mode,
        service_data=service_data,
        service_id=service_id,
    )


async def _save_service(bot: Bot, message: Message) -> None:
    mode, service_data, service_id, _ = _get_editor_context(message)
    if not mode:
        await bot.state_dispenser.delete(message.peer_id)
        await message.answer("Сессия редактирования устарела.", keyboard=get_admin_services_keyboard())
        return

    missing_fields = get_missing_service_field_labels(service_data)
    if missing_fields:
        await message.answer(
            f"❌ Заполните обязательные поля: {', '.join(missing_fields)}",
            keyboard=get_admin_service_editor_keyboard(mode, service_id),
        )
        return

    try:
        if mode == "add":
            service = build_service_model(service_data)
            created_id = await service_repo.create(service)
            finalize_service_photo_dir(
                service_data.get("temp_photos_dir"),
                get_service_dir(created_id),
                move_dir_contents_func=move_dir_contents,
            )
            summary = build_service_save_summary(
                service,
                service_data,
                title="Услуга успешно создана!",
                service_id=created_id,
            )
        else:
            if not service_id:
                await message.answer("Не удалось определить услугу.", keyboard=get_admin_services_keyboard())
                return
            service = build_service_model(service_data, service_id=service_id)
            service.is_active = bool(service_data.get("is_active", True))
            success = await service_repo.update(service)
            if not success:
                await message.answer("Не удалось обновить услугу.", keyboard=get_admin_services_keyboard())
                return
            summary = build_service_save_summary(
                service,
                service_data,
                title="Услуга успешно обновлена!",
                service_id=service_id,
            )
    except Exception as exc:
        await message.answer(f"Ошибка сохранения услуги: {exc}", keyboard=get_admin_services_keyboard())
        return

    await bot.state_dispenser.delete(message.peer_id)
    await message.answer(
        _plain(build_service_save_text(summary)),
        keyboard=get_admin_services_keyboard(),
    )


def register_admin_service_handlers(bot: Bot) -> None:
    @bot.on.message(payload_contains={"a": "adm_service_add"})
    async def admin_service_add(message: Message):
        if not await _is_admin(message):
            await _deny(message)
            return
        await _start_add_service(bot, message)

    @bot.on.message(payload_contains={"a": "adm_service_edit"})
    async def admin_service_edit(message: Message):
        if not await _is_admin(message):
            await _deny(message)
            return
        payload = message.get_payload_json() or {}
        await _start_edit_service(bot, message, int(payload.get("id", 0)))

    @bot.on.message(payload_contains={"a": "adm_service_price_menu"})
    async def admin_service_price_menu(message: Message):
        if not await _is_admin(message):
            await _deny(message)
            return
        mode, service_data, service_id, _ = _get_editor_context(message)
        if not mode:
            await message.answer("Сессия редактирования устарела.", keyboard=get_admin_services_keyboard())
            return
        await _show_price_menu(bot, message, mode=mode, service_data=service_data, service_id=service_id)

    @bot.on.message(payload_contains={"a": "adm_service_editor_back"})
    async def admin_service_editor_back(message: Message):
        if not await _is_admin(message):
            await _deny(message)
            return
        mode, service_data, service_id, _ = _get_editor_context(message)
        if not mode:
            await message.answer("Сессия редактирования устарела.", keyboard=get_admin_services_keyboard())
            return
        await _show_editor_main(bot, message, mode=mode, service_data=service_data, service_id=service_id)

    @bot.on.message(payload_contains={"a": "adm_service_field"})
    async def admin_service_field(message: Message):
        if not await _is_admin(message):
            await _deny(message)
            return
        mode, service_data, service_id, _ = _get_editor_context(message)
        if not mode:
            await message.answer("Сессия редактирования устарела.", keyboard=get_admin_services_keyboard())
            return
        payload = message.get_payload_json() or {}
        field = str(payload.get("f") or "")
        state = VkAdminServiceState.waiting_for_service_photo if field == "photos" else VkAdminServiceState.waiting_for_service_text
        await _set_editor_state(
            bot,
            message,
            state,
            mode=mode,
            service_data=service_data,
            service_id=service_id,
            field=field,
        )
        await message.answer(
            _plain(get_service_field_prompt(mode, field)),
            keyboard=get_admin_service_back_keyboard(mode, service_id),
        )

    @bot.on.message(payload_contains={"a": "adm_service_extras"})
    async def admin_service_extras(message: Message):
        if not await _is_admin(message):
            await _deny(message)
            return
        mode, service_data, service_id, _ = _get_editor_context(message)
        if not mode:
            await message.answer("Сессия редактирования устарела.", keyboard=get_admin_services_keyboard())
            return
        await _show_extras_picker(bot, message, mode=mode, service_data=service_data, service_id=service_id)

    @bot.on.message(payload_contains={"a": "adm_service_extra_toggle"})
    async def admin_service_extra_toggle(message: Message):
        if not await _is_admin(message):
            await _deny(message)
            return
        mode, service_data, service_id, _ = _get_editor_context(message)
        if not mode:
            await message.answer("Сессия редактирования устарела.", keyboard=get_admin_services_keyboard())
            return
        payload = message.get_payload_json() or {}
        extra_id = int(payload.get("id", 0))
        selected_ids = list(service_data.get("extra_services", []))
        selected_ids, _ = toggle_extra_service(selected_ids, extra_id)
        services = await service_repo.get_all()
        service_data["extra_services"] = selected_ids
        service_data["extras"] = format_selected_extras(selected_ids, services)
        await _show_extras_picker(bot, message, mode=mode, service_data=service_data, service_id=service_id)

    @bot.on.message(payload_contains={"a": "adm_service_extras_done"})
    async def admin_service_extras_done(message: Message):
        if not await _is_admin(message):
            await _deny(message)
            return
        mode, service_data, service_id, _ = _get_editor_context(message)
        if not mode:
            await message.answer("Сессия редактирования устарела.", keyboard=get_admin_services_keyboard())
            return
        await _show_editor_main(bot, message, mode=mode, service_data=service_data, service_id=service_id)

    @bot.on.message(payload_contains={"a": "adm_service_save"})
    async def admin_service_save(message: Message):
        if not await _is_admin(message):
            await _deny(message)
            return
        await _save_service(bot, message)

    @bot.on.message(state=VkAdminServiceState.waiting_for_service_text)
    async def admin_service_text_input(message: Message):
        if not await _is_admin(message):
            await _deny(message)
            return
        await _save_service_field_input(bot, message)

    @bot.on.message(state=VkAdminServiceState.waiting_for_service_photo)
    async def admin_service_photo_input(message: Message):
        if not await _is_admin(message):
            await _deny(message)
            return
        await _save_service_photo_input(bot, message)
