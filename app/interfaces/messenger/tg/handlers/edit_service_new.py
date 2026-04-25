from aiogram import Dispatcher, F
from aiogram.types import CallbackQuery, FSInputFile, InputMediaPhoto, Message
from aiogram.fsm.context import FSMContext

from app.interfaces.messenger.tg.keyboards import (
    get_edit_service_main_keyboard, get_edit_service_price_keyboard,
    get_add_service_extras_keyboard, get_services_management_keyboard,
    get_existing_services_keyboard, get_service_photo_delete_keyboard,
    get_service_photo_management_keyboard,
    get_service_photo_prompt_keyboard,
)
from app.interfaces.messenger.tg.states import AdminStates
from app.integrations.local.db import extra_service_repo, service_repo
from app.core.modules.admin.service_editor import (
    build_edit_service_editor_text,
    parse_duration_pair,
    parse_positive_int,
    parse_positive_price,
)
from app.core.modules.admin.service_crud import (
    build_service_model,
    build_service_save_summary,
    build_service_save_text,
)
from app.core.modules.admin.service_editor_state import update_nested_state_data
from app.core.modules.admin.service_extras import format_selected_extras, get_active_extra_services, toggle_extra_service
from app.core.modules.admin.service_prompts import (
    ADMIN_DENIED_TEXT,
    get_service_extras_text,
    get_service_field_prompt,
    get_service_price_menu_text,
)
from app.core.modules.admin.service_photo_menu import (
    build_service_photo_delete_text,
    build_service_photo_menu_text,
    get_service_photo_preview,
)
from app.core.modules.admin.service_photos import save_service_photo
from app.interfaces.messenger.tg.utils.photos import (
    get_service_dir,
    count_photos_in_dir,
    clear_dir,
    delete_photo_by_index,
    list_photo_files,
    save_message_photo,
)

async def start_edit_service_new(callback: CallbackQuery, state: FSMContext, is_admin: bool):
    """РќР°С‡Р°Р»Рѕ СЂРµРґР°РєС‚РёСЂРѕРІР°РЅРёСЏ СѓСЃР»СѓРіРё СЃ РЅРѕРІС‹Рј РёРЅС‚РµСЂС„РµР№СЃРѕРј"""
    if not is_admin:
        await callback.answer(ADMIN_DENIED_TEXT, show_alert=True)
        return
    
    # РР·РІР»РµРєР°РµРј ID СѓСЃР»СѓРіРё РёР· callback_data
    service_id = int(callback.data.split("_")[-1])
    
    # РџРѕР»СѓС‡Р°РµРј СѓСЃР»СѓРіСѓ РёР· Р±Р°Р·С‹ РґР°РЅРЅС‹С…
    service = await service_repo.get_by_id(service_id)
    if not service:
        await callback.answer("вќЊ РЈСЃР»СѓРіР° РЅРµ РЅР°Р№РґРµРЅР°", show_alert=True)
        return
    
    # РЎРѕС…СЂР°РЅСЏРµРј ID СѓСЃР»СѓРіРё РІ СЃРѕСЃС‚РѕСЏРЅРёРё
    await state.update_data(edit_service_id=service_id)
    
    # РљРѕРЅРІРµСЂС‚РёСЂСѓРµРј РґР°РЅРЅС‹Рµ СѓСЃР»СѓРіРё РІ С„РѕСЂРјР°С‚ РґР»СЏ СЂРµРґР°РєС‚РёСЂРѕРІР°РЅРёСЏ
    # РђРєРєСѓСЂР°С‚РЅРѕ РЅРѕСЂРјР°Р»РёР·СѓРµРј plus_service_ids Рё photo_ids, С‚.Рє. РѕРЅРё РјРѕРіСѓС‚ Р±С‹С‚СЊ РєР°Рє СЃС‚СЂРѕРєРѕР№ CSV, С‚Р°Рє Рё С‡РёСЃР»РѕРј/None
    def _normalize_plus_ids(value):
        if value is None:
            return []
        if isinstance(value, int):
            return [value] if value > 0 else []
        if isinstance(value, str):
            parts = [p.strip() for p in value.split(',') if p.strip()]
            try:
                return [int(p) for p in parts]
            except ValueError:
                return []
        return []

    extra_services = _normalize_plus_ids(service.plus_service_ids)
    photos_count = count_photos_in_dir(get_service_dir(service_id))

    extra_catalog = await extra_service_repo.get_all()
    service_data = {
        'name': service.name,
        'description': service.description,
        'price_weekday': service.price_min,
        'price_weekend': service.price_min_weekend,
        'price_extra_weekday': service.price_for_extra_client,
        'price_extra_weekend': service.price_for_extra_client_weekend,
        'price_group': service.fix_price,
        'base_clients': service.base_num_clients,
        'max_clients': service.max_num_clients,
        'min_duration': service.min_duration_minutes,
        'step_duration': service.duration_step_minutes,
        'extra_services': extra_services,
        'extras': format_selected_extras(extra_services, extra_catalog),
        'photos_count': photos_count,
        'photo_ids': service.photo_ids,
    }
    
    # РЎРѕС…СЂР°РЅСЏРµРј РґР°РЅРЅС‹Рµ РІ СЃРѕСЃС‚РѕСЏРЅРёРё
    await state.update_data(edit_service_data=service_data)
    
    # РџРѕРєР°Р·С‹РІР°РµРј РіР»Р°РІРЅРѕРµ РјРµРЅСЋ СЂРµРґР°РєС‚РёСЂРѕРІР°РЅРёСЏ
    await show_edit_service_main(callback, state, is_admin)

async def show_edit_service_main(callback: CallbackQuery, state: FSMContext, is_admin: bool):
    """РџРѕРєР°Р· РіР»Р°РІРЅРѕРіРѕ РјРµРЅСЋ СЂРµРґР°РєС‚РёСЂРѕРІР°РЅРёСЏ СѓСЃР»СѓРіРё."""
    if not is_admin:
        await callback.answer(ADMIN_DENIED_TEXT, show_alert=True)
        return

    data = await state.get_data()
    service_data = data.get("edit_service_data", {})
    await callback.message.edit_text(
        build_edit_service_editor_text(service_data),
        reply_markup=get_edit_service_main_keyboard(),
        parse_mode="HTML"
    )

async def _show_edit_service_photo_manager_for_callback(
    callback: CallbackQuery,
    state: FSMContext,
) -> None:
    data = await state.get_data()
    service_data = data.get("edit_service_data", {})
    service_id = data.get("edit_service_id")
    if not service_id:
        await callback.answer("вќЊ РќРµ СѓРґР°Р»РѕСЃСЊ РѕРїСЂРµРґРµР»РёС‚СЊ СѓСЃР»СѓРіСѓ", show_alert=True)
        return

    photo_paths = list_photo_files(get_service_dir(int(service_id)))
    service_data["photos_count"] = len(photo_paths)
    service_data["photo_ids"] = None
    await state.update_data(edit_service_data=service_data)
    text = build_service_photo_menu_text(photo_paths, mode="edit")
    keyboard = get_service_photo_management_keyboard("edit", photo_paths)
    if getattr(callback.message, "photo", None):
        try:
            await callback.message.delete()
        except Exception:
            pass
        await callback.message.answer(text, reply_markup=keyboard, parse_mode="HTML")
        return

    await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")


async def _show_edit_service_photo_manager_for_message(
    message: Message,
    state: FSMContext,
) -> None:
    data = await state.get_data()
    service_data = data.get("edit_service_data", {})
    service_id = data.get("edit_service_id")
    if not service_id:
        await message.answer("вќЊ РќРµ СѓРґР°Р»РѕСЃСЊ РѕРїСЂРµРґРµР»РёС‚СЊ СѓСЃР»СѓРіСѓ")
        return

    photo_paths = list_photo_files(get_service_dir(int(service_id)))
    service_data["photos_count"] = len(photo_paths)
    service_data["photo_ids"] = None
    await state.update_data(edit_service_data=service_data)
    await message.answer(
        build_service_photo_menu_text(photo_paths, mode="edit"),
        reply_markup=get_service_photo_management_keyboard("edit", photo_paths),
        parse_mode="HTML",
    )


async def _show_edit_service_photo_delete_preview(
    callback: CallbackQuery,
    state: FSMContext,
    *,
    index: int,
) -> None:
    data = await state.get_data()
    service_id = data.get("edit_service_id")
    if not service_id:
        await callback.answer("❌ Не удалось определить услугу", show_alert=True)
        return

    photo_paths = list_photo_files(get_service_dir(int(service_id)))
    photo_path, index, total = get_service_photo_preview(photo_paths, index)
    if not photo_path:
        await _show_edit_service_photo_manager_for_callback(callback, state)
        return

    caption = build_service_photo_delete_text(photo_paths, index)
    keyboard = get_service_photo_delete_keyboard("edit", index, total)
    if getattr(callback.message, "photo", None):
        await callback.message.edit_media(
            media=InputMediaPhoto(
                media=FSInputFile(photo_path),
                caption=caption,
                parse_mode="HTML",
            ),
            reply_markup=keyboard,
        )
        return

    try:
        await callback.message.delete()
    except Exception:
        pass
    await callback.message.answer_photo(
        photo=FSInputFile(photo_path),
        caption=caption,
        parse_mode="HTML",
        reply_markup=keyboard,
    )


async def edit_service_name_callback(callback: CallbackQuery, state: FSMContext, is_admin: bool):
    """РћР±СЂР°Р±РѕС‚С‡РёРє СЂРµРґР°РєС‚РёСЂРѕРІР°РЅРёСЏ РЅР°Р·РІР°РЅРёСЏ СѓСЃР»СѓРіРё"""
    if not is_admin:
        await callback.answer(ADMIN_DENIED_TEXT, show_alert=True)
        return
    
    await callback.message.edit_text(
        get_service_field_prompt("edit", "name"),
        parse_mode="HTML"
    )
    await state.set_state(AdminStates.waiting_for_edit_service_name)

async def edit_service_description_callback(callback: CallbackQuery, state: FSMContext, is_admin: bool):
    """РћР±СЂР°Р±РѕС‚С‡РёРє СЂРµРґР°РєС‚РёСЂРѕРІР°РЅРёСЏ РѕРїРёСЃР°РЅРёСЏ СѓСЃР»СѓРіРё"""
    if not is_admin:
        await callback.answer(ADMIN_DENIED_TEXT, show_alert=True)
        return
    
    await callback.message.edit_text(
        get_service_field_prompt("edit", "description"),
        parse_mode="HTML"
    )
    await state.set_state(AdminStates.waiting_for_edit_service_description)

async def edit_service_price_menu_callback(callback: CallbackQuery, state: FSMContext, is_admin: bool):
    """РћР±СЂР°Р±РѕС‚С‡РёРє РјРµРЅСЋ С†РµРЅ РґР»СЏ СЂРµРґР°РєС‚РёСЂРѕРІР°РЅРёСЏ"""
    if not is_admin:
        await callback.answer(ADMIN_DENIED_TEXT, show_alert=True)
        return
    
    await callback.message.edit_text(
        get_service_price_menu_text("edit"),
        reply_markup=get_edit_service_price_keyboard(),
        parse_mode="HTML"
    )

async def edit_service_max_clients_callback(callback: CallbackQuery, state: FSMContext, is_admin: bool):
    """РћР±СЂР°Р±РѕС‚С‡РёРє СЂРµРґР°РєС‚РёСЂРѕРІР°РЅРёСЏ РјР°РєСЃРёРјР°Р»СЊРЅРѕРіРѕ РєРѕР»РёС‡РµСЃС‚РІР° РєР»РёРµРЅС‚РѕРІ"""
    if not is_admin:
        await callback.answer(ADMIN_DENIED_TEXT, show_alert=True)
        return
    
    await callback.message.edit_text(
        get_service_field_prompt("edit", "max_clients"),
        parse_mode="HTML"
    )
    await state.set_state(AdminStates.waiting_for_edit_service_max_clients)

async def edit_service_extras_callback(callback: CallbackQuery, state: FSMContext, is_admin: bool):
    """РћР±СЂР°Р±РѕС‚С‡РёРє СЂРµРґР°РєС‚РёСЂРѕРІР°РЅРёСЏ РґРѕРїРѕР»РЅРёС‚РµР»СЊРЅС‹С… СѓСЃР»СѓРі"""
    if not is_admin:
        await callback.answer(ADMIN_DENIED_TEXT, show_alert=True)
        return
    
    data = await state.get_data()
    services = await extra_service_repo.get_all()
    active_services = get_active_extra_services(services)
    
    if not active_services:
        await callback.answer("вќЊ РќРµС‚ РґРѕСЃС‚СѓРїРЅС‹С… СѓСЃР»СѓРі РґР»СЏ РІС‹Р±РѕСЂР°", show_alert=True)
        return
    
    service_data = data.get("edit_service_data", {})
    selected_services = service_data.get("extra_services", [])
    
    await callback.message.edit_text(
        get_service_extras_text("edit"),
        reply_markup=get_existing_services_keyboard(
            active_services,
            selected_services,
            select_prefix="select_edit_extra_service_",
            done_callback="edit_extras_done",
            back_callback="show_edit_service_main",
        ),
        parse_mode="HTML"
    )

async def edit_service_duration_callback(callback: CallbackQuery, state: FSMContext, is_admin: bool):
    """РћР±СЂР°Р±РѕС‚С‡РёРє СЂРµРґР°РєС‚РёСЂРѕРІР°РЅРёСЏ РґР»РёС‚РµР»СЊРЅРѕСЃС‚Рё СѓСЃР»СѓРіРё"""
    if not is_admin:
        await callback.answer(ADMIN_DENIED_TEXT, show_alert=True)
        return
    
    await callback.message.edit_text(
        get_service_field_prompt("edit", "duration"),
        parse_mode="HTML"
    )
    await state.set_state(AdminStates.waiting_for_edit_service_duration)

async def edit_service_photos_callback(callback: CallbackQuery, state: FSMContext, is_admin: bool):
    """РћР±СЂР°Р±РѕС‚С‡РёРє СЂРµРґР°РєС‚РёСЂРѕРІР°РЅРёСЏ С„РѕС‚РѕРіСЂР°С„РёР№ СѓСЃР»СѓРіРё"""
    if not is_admin:
        await callback.answer(ADMIN_DENIED_TEXT, show_alert=True)
        return

    await _show_edit_service_photo_manager_for_callback(callback, state)


async def edit_service_photo_add_callback(callback: CallbackQuery, state: FSMContext, is_admin: bool):
    if not is_admin:
        await callback.answer(ADMIN_DENIED_TEXT, show_alert=True)
        return

    await callback.message.edit_text(
        get_service_field_prompt("edit", "photos"),
        reply_markup=get_service_photo_prompt_keyboard("edit"),
        parse_mode="HTML",
    )
    await state.set_state(AdminStates.waiting_for_edit_service_photos)


async def edit_service_photo_page_callback(callback: CallbackQuery, state: FSMContext, is_admin: bool):
    if not is_admin:
        await callback.answer(ADMIN_DENIED_TEXT, show_alert=True)
        return

    index = int(callback.data.split("_")[-1])
    await _show_edit_service_photo_delete_preview(callback, state, index=index)


async def edit_service_photo_delete_callback(callback: CallbackQuery, state: FSMContext, is_admin: bool):
    if not is_admin:
        await callback.answer(ADMIN_DENIED_TEXT, show_alert=True)
        return

    data = await state.get_data()
    service_id = data.get("edit_service_id")
    if not service_id:
        await callback.answer("❌ Не удалось определить услугу", show_alert=True)
        return

    index = int(callback.data.split("_")[-1])
    deleted = delete_photo_by_index(get_service_dir(int(service_id)), index)
    if not deleted:
        await callback.answer("Фото не найдено", show_alert=True)
        return

    await service_repo.update_photo_ids(int(service_id), None)
    await callback.answer("Фото удалено")
    remaining_paths = list_photo_files(get_service_dir(int(service_id)))
    if remaining_paths:
        await _show_edit_service_photo_delete_preview(
            callback,
            state,
            index=min(index, len(remaining_paths) - 1),
        )
        return

    await _show_edit_service_photo_manager_for_callback(callback, state)


async def edit_service_photo_clear_callback(callback: CallbackQuery, state: FSMContext, is_admin: bool):
    if not is_admin:
        await callback.answer(ADMIN_DENIED_TEXT, show_alert=True)
        return

    data = await state.get_data()
    service_id = data.get("edit_service_id")
    if not service_id:
        await callback.answer("❌ Не удалось определить услугу", show_alert=True)
        return

    clear_dir(get_service_dir(int(service_id)))
    await service_repo.update_photo_ids(int(service_id), None)
    await callback.answer("Все фото удалены")
    await _show_edit_service_photo_manager_for_callback(callback, state)
# РћР±СЂР°Р±РѕС‚С‡РёРєРё С†РµРЅ
async def edit_service_price_weekday_callback(callback: CallbackQuery, state: FSMContext, is_admin: bool):
    """РћР±СЂР°Р±РѕС‚С‡РёРє СЂРµРґР°РєС‚РёСЂРѕРІР°РЅРёСЏ С†РµРЅС‹ РІ Р±СѓРґРЅРё"""
    if not is_admin:
        await callback.answer(ADMIN_DENIED_TEXT, show_alert=True)
        return
    
    await callback.message.edit_text(
        get_service_field_prompt("edit", "price_weekday"),
        parse_mode="HTML"
    )
    await state.set_state(AdminStates.waiting_for_edit_service_price_weekday)

async def edit_service_price_weekend_callback(callback: CallbackQuery, state: FSMContext, is_admin: bool):
    """РћР±СЂР°Р±РѕС‚С‡РёРє СЂРµРґР°РєС‚РёСЂРѕРІР°РЅРёСЏ С†РµРЅС‹ РІ РІС‹С…РѕРґРЅС‹Рµ"""
    if not is_admin:
        await callback.answer(ADMIN_DENIED_TEXT, show_alert=True)
        return
    
    await callback.message.edit_text(
        get_service_field_prompt("edit", "price_weekend"),
        parse_mode="HTML"
    )
    await state.set_state(AdminStates.waiting_for_edit_service_price_weekend)

async def edit_service_price_extra_weekday_callback(callback: CallbackQuery, state: FSMContext, is_admin: bool):
    """РћР±СЂР°Р±РѕС‚С‡РёРє СЂРµРґР°РєС‚РёСЂРѕРІР°РЅРёСЏ С†РµРЅС‹ Р·Р° РґРѕРїРѕР»РЅРёС‚РµР»СЊРЅРѕРіРѕ РєР»РёРµРЅС‚Р° РІ Р±СѓРґРЅРё"""
    if not is_admin:
        await callback.answer(ADMIN_DENIED_TEXT, show_alert=True)
        return
    
    await callback.message.edit_text(
        get_service_field_prompt("edit", "price_extra_weekday"),
        parse_mode="HTML"
    )
    await state.set_state(AdminStates.waiting_for_edit_service_price_extra_weekday)

async def edit_service_price_extra_weekend_callback(callback: CallbackQuery, state: FSMContext, is_admin: bool):
    """РћР±СЂР°Р±РѕС‚С‡РёРє СЂРµРґР°РєС‚РёСЂРѕРІР°РЅРёСЏ С†РµРЅС‹ Р·Р° РґРѕРїРѕР»РЅРёС‚РµР»СЊРЅРѕРіРѕ РєР»РёРµРЅС‚Р° РІ РІС‹С…РѕРґРЅС‹Рµ"""
    if not is_admin:
        await callback.answer(ADMIN_DENIED_TEXT, show_alert=True)
        return
    
    await callback.message.edit_text(
        get_service_field_prompt("edit", "price_extra_weekend"),
        parse_mode="HTML"
    )
    await state.set_state(AdminStates.waiting_for_edit_service_price_extra_weekend)

async def edit_service_price_group_callback(callback: CallbackQuery, state: FSMContext, is_admin: bool):
    """РћР±СЂР°Р±РѕС‚С‡РёРє СЂРµРґР°РєС‚РёСЂРѕРІР°РЅРёСЏ РіСЂСѓРїРїРѕРІРѕР№ С†РµРЅС‹"""
    if not is_admin:
        await callback.answer(ADMIN_DENIED_TEXT, show_alert=True)
        return
    
    await callback.message.edit_text(
        get_service_field_prompt("edit", "price_group"),
        parse_mode="HTML"
    )
    await state.set_state(AdminStates.waiting_for_edit_service_price_group)

# РћР±СЂР°Р±РѕС‚С‡РёРєРё РІС‹Р±РѕСЂР° РґРѕРїРѕР»РЅРёС‚РµР»СЊРЅС‹С… СѓСЃР»СѓРі
async def select_edit_extra_service_callback(callback: CallbackQuery, state: FSMContext, is_admin: bool):
    """РћР±СЂР°Р±РѕС‚С‡РёРє РІС‹Р±РѕСЂР° РґРѕРїРѕР»РЅРёС‚РµР»СЊРЅРѕР№ СѓСЃР»СѓРіРё РїСЂРё СЂРµРґР°РєС‚РёСЂРѕРІР°РЅРёРё"""
    if not is_admin:
        await callback.answer(ADMIN_DENIED_TEXT, show_alert=True)
        return
    
    service_id = int(callback.data.split("_")[-1])
    data = await state.get_data()
    service_data = data.get("edit_service_data", {})
    selected_services = service_data.get("extra_services", [])
    selected_services, _ = toggle_extra_service(selected_services, service_id)

    await update_nested_state_data(
        state,
        "edit_service_data",
        {"extra_services": selected_services},
    )

    services = await extra_service_repo.get_all()
    active_services = get_active_extra_services(services)
    service_data["extras"] = format_selected_extras(selected_services, services)

    await callback.message.edit_text(
        get_service_extras_text("edit"),
        reply_markup=get_existing_services_keyboard(
            active_services,
            selected_services,
            select_prefix="select_edit_extra_service_",
            done_callback="edit_extras_done",
            back_callback="show_edit_service_main",
        ),
        parse_mode="HTML"
    )

async def edit_extras_done_callback(callback: CallbackQuery, state: FSMContext, is_admin: bool):
    """РћР±СЂР°Р±РѕС‚С‡РёРє Р·Р°РІРµСЂС€РµРЅРёСЏ РІС‹Р±РѕСЂР° РґРѕРїРѕР»РЅРёС‚РµР»СЊРЅС‹С… СѓСЃР»СѓРі РїСЂРё СЂРµРґР°РєС‚РёСЂРѕРІР°РЅРёРё"""
    if not is_admin:
        await callback.answer("РЈ РІР°СЃ РЅРµС‚ РїСЂР°РІ Р°РґРјРёРЅРёСЃС‚СЂР°С‚РѕСЂР°", show_alert=True)
        return
    
    # Р’РѕР·РІСЂР°С‰Р°РµРјСЃСЏ Рє РіР»Р°РІРЅРѕРјСѓ РјРµРЅСЋ СЂРµРґР°РєС‚РёСЂРѕРІР°РЅРёСЏ
    await show_edit_service_main(callback, state, is_admin)

# РћР±СЂР°Р±РѕС‚С‡РёРєРё С‚РµРєСЃС‚РѕРІС‹С… СЃРѕРѕР±С‰РµРЅРёР№
async def process_edit_service_name(message: Message, state: FSMContext, is_admin: bool):
    """РћР±СЂР°Р±РѕС‚РєР° РЅРѕРІРѕРіРѕ РЅР°Р·РІР°РЅРёСЏ СѓСЃР»СѓРіРё."""
    if not is_admin:
        return

    new_name = message.text.strip()
    if not new_name:
        await message.answer("вќЊ РќР°Р·РІР°РЅРёРµ РЅРµ РјРѕР¶РµС‚ Р±С‹С‚СЊ РїСѓСЃС‚С‹Рј")
        return

    await update_nested_state_data(
        state,
        "edit_service_data",
        {},
        field_name="name",
        field_value=new_name,
    )
    await show_edit_service_main_after_edit(message, state, is_admin)


async def process_edit_service_description(message: Message, state: FSMContext, is_admin: bool):
    """РћР±СЂР°Р±РѕС‚РєР° РЅРѕРІРѕРіРѕ РѕРїРёСЃР°РЅРёСЏ СѓСЃР»СѓРіРё."""
    if not is_admin:
        return

    new_description = message.text.strip()
    if not new_description:
        await message.answer("вќЊ РћРїРёСЃР°РЅРёРµ РЅРµ РјРѕР¶РµС‚ Р±С‹С‚СЊ РїСѓСЃС‚С‹Рј")
        return

    await update_nested_state_data(
        state,
        "edit_service_data",
        {},
        field_name="description",
        field_value=new_description,
    )
    await show_edit_service_main_after_edit(message, state, is_admin)


async def process_edit_service_price_weekday(message: Message, state: FSMContext, is_admin: bool):
    """РћР±СЂР°Р±РѕС‚РєР° РЅРѕРІРѕР№ С†РµРЅС‹ РІ Р±СѓРґРЅРё."""
    if not is_admin:
        return

    try:
        new_price = parse_positive_price(message.text, allow_zero=True)
        await update_nested_state_data(
            state,
            "edit_service_data",
            {},
            field_name="price_weekday",
            field_value=new_price,
        )
        await show_edit_service_main_after_edit(message, state, is_admin)
    except ValueError:
        await message.answer("вќЊ Р’РІРµРґРёС‚Рµ РєРѕСЂСЂРµРєС‚РЅСѓСЋ С†РµРЅСѓ (С‡РёСЃР»Рѕ)")


async def process_edit_service_price_weekend(message: Message, state: FSMContext, is_admin: bool):
    """РћР±СЂР°Р±РѕС‚РєР° РЅРѕРІРѕР№ С†РµРЅС‹ РІ РІС‹С…РѕРґРЅС‹Рµ."""
    if not is_admin:
        return

    try:
        new_price = parse_positive_price(message.text, allow_zero=True)
        await update_nested_state_data(
            state,
            "edit_service_data",
            {},
            field_name="price_weekend",
            field_value=new_price,
        )
        await show_edit_service_main_after_edit(message, state, is_admin)
    except ValueError:
        await message.answer("вќЊ Р’РІРµРґРёС‚Рµ РєРѕСЂСЂРµРєС‚РЅСѓСЋ С†РµРЅСѓ (С‡РёСЃР»Рѕ)")


async def process_edit_service_price_extra_weekday(message: Message, state: FSMContext, is_admin: bool):
    """РћР±СЂР°Р±РѕС‚РєР° РЅРѕРІРѕР№ С†РµРЅС‹ Р·Р° РґРѕРїРѕР»РЅРёС‚РµР»СЊРЅРѕРіРѕ РєР»РёРµРЅС‚Р° РІ Р±СѓРґРЅРё."""
    if not is_admin:
        return

    try:
        new_price = parse_positive_price(message.text, allow_zero=True)
        await update_nested_state_data(
            state,
            "edit_service_data",
            {},
            field_name="price_extra_weekday",
            field_value=new_price,
        )
        await show_edit_service_main_after_edit(message, state, is_admin)
    except ValueError:
        await message.answer("вќЊ Р’РІРµРґРёС‚Рµ РєРѕСЂСЂРµРєС‚РЅСѓСЋ С†РµРЅСѓ (С‡РёСЃР»Рѕ)")


async def process_edit_service_price_extra_weekend(message: Message, state: FSMContext, is_admin: bool):
    """РћР±СЂР°Р±РѕС‚РєР° РЅРѕРІРѕР№ С†РµРЅС‹ Р·Р° РґРѕРїРѕР»РЅРёС‚РµР»СЊРЅРѕРіРѕ РєР»РёРµРЅС‚Р° РІ РІС‹С…РѕРґРЅС‹Рµ."""
    if not is_admin:
        return

    try:
        new_price = parse_positive_price(message.text, allow_zero=True)
        await update_nested_state_data(
            state,
            "edit_service_data",
            {},
            field_name="price_extra_weekend",
            field_value=new_price,
        )
        await show_edit_service_main_after_edit(message, state, is_admin)
    except ValueError:
        await message.answer("вќЊ Р’РІРµРґРёС‚Рµ РєРѕСЂСЂРµРєС‚РЅСѓСЋ С†РµРЅСѓ (С‡РёСЃР»Рѕ)")


async def process_edit_service_price_group(message: Message, state: FSMContext, is_admin: bool):
    """РћР±СЂР°Р±РѕС‚РєР° РЅРѕРІРѕР№ РіСЂСѓРїРїРѕРІРѕР№ С†РµРЅС‹."""
    if not is_admin:
        return

    try:
        new_price = parse_positive_price(message.text, allow_zero=True)
        await update_nested_state_data(
            state,
            "edit_service_data",
            {},
            field_name="price_group",
            field_value=new_price,
        )
        await show_edit_service_main_after_edit(message, state, is_admin)
    except ValueError:
        await message.answer("вќЊ Р’РІРµРґРёС‚Рµ РєРѕСЂСЂРµРєС‚РЅСѓСЋ С†РµРЅСѓ (С‡РёСЃР»Рѕ)")


async def process_edit_service_max_clients(message: Message, state: FSMContext, is_admin: bool):
    """РћР±СЂР°Р±РѕС‚РєР° РЅРѕРІРѕРіРѕ РјР°РєСЃРёРјР°Р»СЊРЅРѕРіРѕ РєРѕР»РёС‡РµСЃС‚РІР° РєР»РёРµРЅС‚РѕРІ."""
    if not is_admin:
        return

    try:
        new_max_clients = parse_positive_int(message.text)
        await update_nested_state_data(
            state,
            "edit_service_data",
            {},
            field_name="max_clients",
            field_value=new_max_clients,
        )
        await show_edit_service_main_after_edit(message, state, is_admin)
    except ValueError:
        await message.answer("вќЊ Р’РІРµРґРёС‚Рµ РєРѕСЂСЂРµРєС‚РЅС‹Рµ Р·РЅР°С‡РµРЅРёСЏ (С†РµР»С‹Рµ С‡РёСЃР»Р°)")


async def process_edit_service_duration(message: Message, state: FSMContext, is_admin: bool):
    """РћР±СЂР°Р±РѕС‚РєР° РЅРѕРІРѕР№ РґР»РёС‚РµР»СЊРЅРѕСЃС‚Рё СѓСЃР»СѓРіРё."""
    if not is_admin:
        return

    try:
        min_duration, step_duration = parse_duration_pair(message.text)
        await update_nested_state_data(
            state,
            "edit_service_data",
            {
                "min_duration": min_duration,
                "step_duration": step_duration,
            },
        )
        await show_edit_service_main_after_edit(message, state, is_admin)
    except ValueError:
        await message.answer("вќЊ Р’РІРµРґРёС‚Рµ РєРѕСЂСЂРµРєС‚РЅС‹Рµ Р·РЅР°С‡РµРЅРёСЏ (С†РµР»С‹Рµ С‡РёСЃР»Р°)")


async def process_edit_service_photos(message: Message, state: FSMContext, is_admin: bool):
    """РћР±СЂР°Р±РѕС‚РєР° РЅРѕРІС‹С… С„РѕС‚РѕРіСЂР°С„РёР№ СѓСЃР»СѓРіРё."""
    if not is_admin:
        return

    if not message.photo:
        await message.answer("вќЊ РћС‚РїСЂР°РІСЊС‚Рµ С„РѕС‚РѕРіСЂР°С„РёСЋ")
        return

    data = await state.get_data()
    service_data = data.get("edit_service_data", {})
    service_id = data.get("edit_service_id")
    if not service_id:
        await message.answer("вќЊ РќРµ СѓРґР°Р»РѕСЃСЊ РѕРїСЂРµРґРµР»РёС‚СЊ СѓСЃР»СѓРіСѓ")
        return

    service_dir = get_service_dir(service_id)
    try:
        photos_count = await save_service_photo(
            message,
            service_dir,
            save_photo_func=save_message_photo,
            count_photos_func=count_photos_in_dir,
        )
    except Exception:
        await message.answer("вќЊ РќРµ СѓРґР°Р»РѕСЃСЊ СЃРѕС…СЂР°РЅРёС‚СЊ С„РѕС‚РѕРіСЂР°С„РёСЋ")
        return

    service_data["photos_updated"] = True
    service_data["photos_count"] = photos_count
    service_data["photo_ids"] = None
    await state.update_data(edit_service_data=service_data)
    await service_repo.update_photo_ids(int(service_id), None)
    await message.answer(f"вњ… Р¤РѕС‚РѕРіСЂР°С„РёРё РґРѕР±Р°РІР»РµРЅС‹. Р’СЃРµРіРѕ: {photos_count}")
    await _show_edit_service_photo_manager_for_message(message, state)

async def show_edit_service_main_after_edit(message: Message, state: FSMContext, is_admin: bool):
    """РџРѕРєР°Р· РіР»Р°РІРЅРѕРіРѕ РјРµРЅСЋ РїРѕСЃР»Рµ СЂРµРґР°РєС‚РёСЂРѕРІР°РЅРёСЏ РїР°СЂР°РјРµС‚СЂР°."""
    data = await state.get_data()
    service_data = data.get("edit_service_data", {})
    await message.answer(
        build_edit_service_editor_text(service_data),
        reply_markup=get_edit_service_main_keyboard(),
        parse_mode="HTML",
    )


async def save_edit_service_callback(callback: CallbackQuery, state: FSMContext, is_admin: bool):
    """РћР±СЂР°Р±РѕС‚С‡РёРє СЃРѕС…СЂР°РЅРµРЅРёСЏ РёР·РјРµРЅРµРЅРёР№ СѓСЃР»СѓРіРё."""
    if not is_admin:
        await callback.answer("РЈ РІР°СЃ РЅРµС‚ РїСЂР°РІ Р°РґРјРёРЅРёСЃС‚СЂР°С‚РѕСЂР°", show_alert=True)
        return

    data = await state.get_data()
    service_data = data.get("edit_service_data", {})
    service_id = data.get("edit_service_id")

    try:
        service = build_service_model(service_data, service_id=service_id)
        success = await service_repo.update(service)

        if success:
            await state.clear()
            summary = build_service_save_summary(
                service,
                service_data,
                title="РЈСЃР»СѓРіР° СѓСЃРїРµС€РЅРѕ РѕР±РЅРѕРІР»РµРЅР°!",
                service_id=service_id,
            )
            await callback.message.edit_text(
                build_service_save_text(summary),
                reply_markup=get_services_management_keyboard(),
                parse_mode="HTML",
            )
        else:
            await callback.answer("вќЊ РћС€РёР±РєР° РїСЂРё РѕР±РЅРѕРІР»РµРЅРёРё СѓСЃР»СѓРіРё", show_alert=True)
    except Exception as e:
        await callback.answer(f"вќЊ РћС€РёР±РєР° РїСЂРё РѕР±РЅРѕРІР»РµРЅРёРё СѓСЃР»СѓРіРё: {e}", show_alert=True)


def register_edit_service_new_handlers(dp: Dispatcher):
    """Р РµРіРёСЃС‚СЂР°С†РёСЏ РѕР±СЂР°Р±РѕС‚С‡РёРєРѕРІ СЂРµРґР°РєС‚РёСЂРѕРІР°РЅРёСЏ СѓСЃР»СѓРі."""

    dp.callback_query.register(start_edit_service_new, F.data.startswith("edit_service_new_"))
    dp.callback_query.register(show_edit_service_main, F.data == "show_edit_service_main")

    dp.callback_query.register(edit_service_name_callback, F.data == "edit_service_name")
    dp.callback_query.register(edit_service_description_callback, F.data == "edit_service_description")
    dp.callback_query.register(edit_service_price_menu_callback, F.data == "edit_service_price")
    dp.callback_query.register(edit_service_max_clients_callback, F.data == "edit_service_max_clients")
    dp.callback_query.register(edit_service_extras_callback, F.data == "edit_service_extras")
    dp.callback_query.register(edit_service_duration_callback, F.data == "edit_service_duration")
    dp.callback_query.register(edit_service_photos_callback, F.data == "edit_service_photos")
    dp.callback_query.register(edit_service_photo_add_callback, F.data == "edit_service_photo_add")
    dp.callback_query.register(edit_service_photo_clear_callback, F.data == "edit_service_photo_clear")
    dp.callback_query.register(edit_service_photo_page_callback, F.data.startswith("edit_service_photo_page_"))
    dp.callback_query.register(edit_service_photo_delete_callback, F.data.startswith("edit_service_photo_delete_"))

    dp.callback_query.register(edit_service_price_weekday_callback, F.data == "edit_service_price_weekday")
    dp.callback_query.register(edit_service_price_weekend_callback, F.data == "edit_service_price_weekend")
    dp.callback_query.register(edit_service_price_extra_weekday_callback, F.data == "edit_service_price_extra_weekday")
    dp.callback_query.register(edit_service_price_extra_weekend_callback, F.data == "edit_service_price_extra_weekend")
    dp.callback_query.register(edit_service_price_group_callback, F.data == "edit_service_price_group")

    dp.callback_query.register(select_edit_extra_service_callback, F.data.startswith("select_edit_extra_service_"))
    dp.callback_query.register(edit_extras_done_callback, F.data == "edit_extras_done")

    dp.callback_query.register(save_edit_service_callback, F.data == "save_edit_service")

    dp.message.register(process_edit_service_name, AdminStates.waiting_for_edit_service_name)
    dp.message.register(process_edit_service_description, AdminStates.waiting_for_edit_service_description)
    dp.message.register(process_edit_service_price_weekday, AdminStates.waiting_for_edit_service_price_weekday)
    dp.message.register(process_edit_service_price_weekend, AdminStates.waiting_for_edit_service_price_weekend)
    dp.message.register(process_edit_service_price_extra_weekday, AdminStates.waiting_for_edit_service_price_extra_weekday)
    dp.message.register(process_edit_service_price_extra_weekend, AdminStates.waiting_for_edit_service_price_extra_weekend)
    dp.message.register(process_edit_service_price_group, AdminStates.waiting_for_edit_service_price_group)
    dp.message.register(process_edit_service_max_clients, AdminStates.waiting_for_edit_service_max_clients)
    dp.message.register(process_edit_service_duration, AdminStates.waiting_for_edit_service_duration)
    dp.message.register(process_edit_service_photos, AdminStates.waiting_for_edit_service_photos)

