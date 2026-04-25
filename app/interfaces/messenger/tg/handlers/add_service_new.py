from aiogram import Dispatcher, F
from aiogram.types import CallbackQuery, FSInputFile, InputMediaPhoto, Message
from aiogram.fsm.context import FSMContext

from app.interfaces.messenger.tg.keyboards import (
    get_add_service_main_keyboard, get_add_service_price_keyboard, 
    get_add_service_extras_keyboard, get_services_management_keyboard,
    get_existing_services_keyboard, get_service_photo_delete_keyboard,
    get_service_photo_management_keyboard,
    get_service_photo_prompt_keyboard,
)
from app.interfaces.messenger.tg.states import AdminStates
from app.integrations.local.db import extra_service_repo, service_repo
from app.core.modules.admin.service_editor import (
    build_add_service_editor_text,
    parse_duration_pair,
    parse_positive_int,
    parse_positive_price,
)
from app.core.modules.admin.service_crud import (
    build_service_model,
    build_service_save_summary,
    build_service_save_text,
    get_missing_service_field_labels,
)
from app.core.modules.admin.service_editor_state import update_nested_state_data
from app.core.modules.admin.service_extras import (
    format_selected_extras,
    get_active_extra_services,
    toggle_extra_service,
)
from app.core.modules.admin.service_prompts import (
    ADMIN_DENIED_TEXT,
    get_service_extras_empty_text,
    get_service_extras_text,
    get_service_field_prompt,
    get_service_price_menu_text,
    get_service_start_text,
)
from app.core.modules.admin.service_photo_menu import (
    build_service_photo_delete_text,
    build_service_photo_menu_text,
    get_service_photo_preview,
)
from app.core.modules.admin.service_photos import finalize_service_photo_dir, save_service_photo
from app.interfaces.messenger.tg.utils.photos import (
    get_temp_dir,
    get_service_dir,
    count_photos_in_dir,
    clear_dir,
    delete_photo_by_index,
    list_photo_files,
    save_message_photo,
    move_dir_contents,
)


async def _show_add_service_photo_manager_for_callback(
    callback: CallbackQuery,
    state: FSMContext,
) -> None:
    data = await state.get_data()
    service_data = data.get("new_service_data", {})
    temp_dir = get_temp_dir(callback.from_user.id)
    photo_paths = list_photo_files(temp_dir)
    service_data["photos_count"] = len(photo_paths)
    service_data["photo_ids"] = None
    if photo_paths:
        service_data["temp_photos_dir"] = str(temp_dir)
    else:
        service_data.pop("temp_photos_dir", None)
    await state.update_data(new_service_data=service_data)
    text = build_service_photo_menu_text(photo_paths, mode="add")
    keyboard = get_service_photo_management_keyboard("add", photo_paths)
    if getattr(callback.message, "photo", None):
        try:
            await callback.message.delete()
        except Exception:
            pass
        await callback.message.answer(text, reply_markup=keyboard, parse_mode="HTML")
        return

    await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")


async def _show_add_service_photo_manager_for_message(
    message: Message,
    state: FSMContext,
) -> None:
    data = await state.get_data()
    service_data = data.get("new_service_data", {})
    temp_dir = get_temp_dir(message.from_user.id)
    photo_paths = list_photo_files(temp_dir)
    service_data["photos_count"] = len(photo_paths)
    service_data["photo_ids"] = None
    if photo_paths:
        service_data["temp_photos_dir"] = str(temp_dir)
    else:
        service_data.pop("temp_photos_dir", None)
    await state.update_data(new_service_data=service_data)
    await message.answer(
        build_service_photo_menu_text(photo_paths, mode="add"),
        reply_markup=get_service_photo_management_keyboard("add", photo_paths),
        parse_mode="HTML",
    )


async def _show_add_service_photo_delete_preview(
    callback: CallbackQuery,
    state: FSMContext,
    *,
    index: int,
) -> None:
    photo_paths = list_photo_files(get_temp_dir(callback.from_user.id))
    photo_path, index, total = get_service_photo_preview(photo_paths, index)
    if not photo_path:
        await _show_add_service_photo_manager_for_callback(callback, state)
        return

    caption = build_service_photo_delete_text(photo_paths, index)
    keyboard = get_service_photo_delete_keyboard("add", index, total)
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

async def start_add_service_new(callback: CallbackQuery, state: FSMContext, is_admin: bool):
    """РќР°С‡Р°Р»Рѕ РґРѕР±Р°РІР»РµРЅРёСЏ РЅРѕРІРѕР№ СѓСЃР»СѓРіРё СЃ РЅРѕРІС‹Рј РёРЅС‚РµСЂС„РµР№СЃРѕРј"""
    if not is_admin:
        await callback.answer(ADMIN_DENIED_TEXT, show_alert=True)
        return
    
    # РћС‡РёС‰Р°РµРј РїСЂРµРґС‹РґСѓС‰РёРµ РґР°РЅРЅС‹Рµ
    await state.clear()
    # РћС‡РёС‰Р°РµРј РІСЂРµРјРµРЅРЅС‹Рµ С„РѕС‚Рѕ РґР»СЏ С‚РµРєСѓС‰РµРіРѕ Р°РґРјРёРЅРёСЃС‚СЂР°С‚РѕСЂР°
    temp_dir = get_temp_dir(callback.from_user.id)
    clear_dir(temp_dir)
    
    await callback.message.edit_text(
        get_service_start_text("add"),
        reply_markup=get_add_service_main_keyboard(),
        parse_mode="HTML",
    )

async def show_add_service_main(callback: CallbackQuery, state: FSMContext, is_admin: bool):
    """РџРѕРєР°Р· РіР»Р°РІРЅРѕРіРѕ РјРµРЅСЋ РґРѕР±Р°РІР»РµРЅРёСЏ СѓСЃР»СѓРіРё СЃ С‚РµРєСѓС‰РёРјРё РґР°РЅРЅС‹РјРё."""
    if not is_admin:
        await callback.answer(ADMIN_DENIED_TEXT, show_alert=True)
        return

    data = await state.get_data()
    service_data = data.get("new_service_data", {})
    await callback.message.edit_text(
        build_add_service_editor_text(service_data),
        reply_markup=get_add_service_main_keyboard(),
        parse_mode="HTML",
    )

async def add_service_name_callback(callback: CallbackQuery, state: FSMContext, is_admin: bool):
    """РћР±СЂР°Р±РѕС‚С‡РёРє РєРЅРѕРїРєРё 'РќР°Р·РІР°РЅРёРµ'"""
    if not is_admin:
        await callback.answer(ADMIN_DENIED_TEXT, show_alert=True)
        return
    
    await callback.message.edit_text(
        get_service_field_prompt("add", "name"),
        parse_mode="HTML"
    )
    await state.set_state(AdminStates.waiting_for_new_service_name)

async def add_service_description_callback(callback: CallbackQuery, state: FSMContext, is_admin: bool):
    """РћР±СЂР°Р±РѕС‚С‡РёРє РєРЅРѕРїРєРё 'РћРїРёСЃР°РЅРёРµ'"""
    if not is_admin:
        await callback.answer(ADMIN_DENIED_TEXT, show_alert=True)
        return
    
    await callback.message.edit_text(
        get_service_field_prompt("add", "description"),
        parse_mode="HTML"
    )
    await state.set_state(AdminStates.waiting_for_new_service_description)

async def add_service_price_menu_callback(callback: CallbackQuery, state: FSMContext, is_admin: bool):
    """РћР±СЂР°Р±РѕС‚С‡РёРє РєРЅРѕРїРєРё 'Р¦РµРЅР°' - РїРѕРєР°Р· РјРµРЅСЋ С†РµРЅ"""
    if not is_admin:
        await callback.answer(ADMIN_DENIED_TEXT, show_alert=True)
        return
    
    await callback.message.edit_text(
        get_service_price_menu_text("add"),
        reply_markup=get_add_service_price_keyboard(),
        parse_mode="HTML"
    )

async def add_service_price_weekday_callback(callback: CallbackQuery, state: FSMContext, is_admin: bool):
    """РћР±СЂР°Р±РѕС‚С‡РёРє РєРЅРѕРїРєРё 'Р¦РµРЅР° (Р±СѓРґРЅРё)'"""
    if not is_admin:
        await callback.answer(ADMIN_DENIED_TEXT, show_alert=True)
        return
    
    await callback.message.edit_text(
        get_service_field_prompt("add", "price_weekday"),
        parse_mode="HTML"
    )
    await state.set_state(AdminStates.waiting_for_new_service_price_weekday)

async def add_service_price_weekend_callback(callback: CallbackQuery, state: FSMContext, is_admin: bool):
    """РћР±СЂР°Р±РѕС‚С‡РёРє РєРЅРѕРїРєРё 'Р¦РµРЅР° (РІС‹С…РѕРґРЅС‹Рµ)'"""
    if not is_admin:
        await callback.answer(ADMIN_DENIED_TEXT, show_alert=True)
        return
    
    await callback.message.edit_text(
        get_service_field_prompt("add", "price_weekend"),
        parse_mode="HTML"
    )
    await state.set_state(AdminStates.waiting_for_new_service_price_weekend)

async def add_service_price_extra_weekday_callback(callback: CallbackQuery, state: FSMContext, is_admin: bool):
    """РћР±СЂР°Р±РѕС‚С‡РёРє РєРЅРѕРїРєРё С†РµРЅС‹ Р·Р° РґРѕРїРѕР»РЅРёС‚РµР»СЊРЅРѕРіРѕ РєР»РёРµРЅС‚Р° РІ Р±СѓРґРЅРё."""
    if not is_admin:
        await callback.answer(ADMIN_DENIED_TEXT, show_alert=True)
        return

    await callback.message.edit_text(
        get_service_field_prompt("add", "price_extra_weekday"),
        parse_mode="HTML",
    )
    await state.set_state(AdminStates.waiting_for_new_service_price_extra_weekday)


async def add_service_price_extra_weekend_callback(callback: CallbackQuery, state: FSMContext, is_admin: bool):
    """РћР±СЂР°Р±РѕС‚С‡РёРє РєРЅРѕРїРєРё С†РµРЅС‹ Р·Р° РґРѕРїРѕР»РЅРёС‚РµР»СЊРЅРѕРіРѕ РєР»РёРµРЅС‚Р° РІ РІС‹С…РѕРґРЅС‹Рµ."""
    if not is_admin:
        await callback.answer(ADMIN_DENIED_TEXT, show_alert=True)
        return

    await callback.message.edit_text(
        get_service_field_prompt("add", "price_extra_weekend"),
        parse_mode="HTML",
    )
    await state.set_state(AdminStates.waiting_for_new_service_price_extra_weekend)


async def add_service_price_group_callback(callback: CallbackQuery, state: FSMContext, is_admin: bool):
    """РћР±СЂР°Р±РѕС‚С‡РёРє РєРЅРѕРїРєРё С†РµРЅС‹ РґР»СЏ РіСЂСѓРїРїС‹ (РѕС‚ 10 С‡РµР»РѕРІРµРє)."""
    if not is_admin:
        await callback.answer(ADMIN_DENIED_TEXT, show_alert=True)
        return

    await callback.message.edit_text(
        get_service_field_prompt("add", "price_group"),
        parse_mode="HTML",
    )
    await state.set_state(AdminStates.waiting_for_new_service_price_group)

async def add_service_max_clients_callback(callback: CallbackQuery, state: FSMContext, is_admin: bool):
    """РћР±СЂР°Р±РѕС‚С‡РёРє РєРЅРѕРїРєРё 'РњР°РєСЃ. С‡РµР»РѕРІРµРє'"""
    if not is_admin:
        await callback.answer(ADMIN_DENIED_TEXT, show_alert=True)
        return
    
    await callback.message.edit_text(
        get_service_field_prompt("add", "max_clients"),
        parse_mode="HTML"
    )
    await state.set_state(AdminStates.waiting_for_new_service_max_clients)

async def add_service_extras_callback(callback: CallbackQuery, state: FSMContext, is_admin: bool):
    """РћР±СЂР°Р±РѕС‚С‡РёРє РєРЅРѕРїРєРё 'Р”РѕРї. СѓСЃР»СѓРіРё'"""
    if not is_admin:
        await callback.answer(ADMIN_DENIED_TEXT, show_alert=True)
        return
    
    services = await extra_service_repo.get_all()
    active_services = get_active_extra_services(services)
    data = await state.get_data()
    service_data = data.get("new_service_data", {})
    selected_ids = service_data.get("extra_services", [])
    
    if not active_services:
        await callback.message.edit_text(
            get_service_extras_empty_text(),
            reply_markup=get_add_service_extras_keyboard(),
            parse_mode="HTML"
        )
        return
    
    await callback.message.edit_text(
        get_service_extras_text("add"),
        reply_markup=get_existing_services_keyboard(active_services, selected_ids),
        parse_mode="HTML"
    )

async def add_service_duration_callback(callback: CallbackQuery, state: FSMContext, is_admin: bool):
    """РћР±СЂР°Р±РѕС‚С‡РёРє РєРЅРѕРїРєРё 'Р”Р»РёС‚РµР»СЊРЅРѕСЃС‚СЊ'"""
    if not is_admin:
        await callback.answer(ADMIN_DENIED_TEXT, show_alert=True)
        return
    
    await callback.message.edit_text(
        get_service_field_prompt("add", "duration"),
        parse_mode="HTML"
    )
    await state.set_state(AdminStates.waiting_for_new_service_duration)

async def add_service_photos_callback(callback: CallbackQuery, state: FSMContext, is_admin: bool):
    """РћР±СЂР°Р±РѕС‚С‡РёРє РєРЅРѕРїРєРё ''Р¤РѕС‚Рѕ''"""
    if not is_admin:
        await callback.answer(ADMIN_DENIED_TEXT, show_alert=True)
        return

    await _show_add_service_photo_manager_for_callback(callback, state)


async def add_service_photo_add_callback(callback: CallbackQuery, state: FSMContext, is_admin: bool):
    if not is_admin:
        await callback.answer(ADMIN_DENIED_TEXT, show_alert=True)
        return

    await callback.message.edit_text(
        get_service_field_prompt("add", "photos"),
        reply_markup=get_service_photo_prompt_keyboard("add"),
        parse_mode="HTML",
    )
    await state.set_state(AdminStates.waiting_for_new_service_photos)


async def add_service_photo_page_callback(callback: CallbackQuery, state: FSMContext, is_admin: bool):
    if not is_admin:
        await callback.answer(ADMIN_DENIED_TEXT, show_alert=True)
        return

    index = int(callback.data.split("_")[-1])
    await _show_add_service_photo_delete_preview(callback, state, index=index)


async def add_service_photo_delete_callback(callback: CallbackQuery, state: FSMContext, is_admin: bool):
    if not is_admin:
        await callback.answer(ADMIN_DENIED_TEXT, show_alert=True)
        return

    index = int(callback.data.split("_")[-1])
    deleted = delete_photo_by_index(get_temp_dir(callback.from_user.id), index)
    if not deleted:
        await callback.answer("Фото не найдено", show_alert=True)
        return

    await callback.answer("Фото удалено")
    remaining_paths = list_photo_files(get_temp_dir(callback.from_user.id))
    if remaining_paths:
        await _show_add_service_photo_delete_preview(
            callback,
            state,
            index=min(index, len(remaining_paths) - 1),
        )
        return

    await _show_add_service_photo_manager_for_callback(callback, state)


async def add_service_photo_clear_callback(callback: CallbackQuery, state: FSMContext, is_admin: bool):
    if not is_admin:
        await callback.answer(ADMIN_DENIED_TEXT, show_alert=True)
        return

    clear_dir(get_temp_dir(callback.from_user.id))
    await callback.answer("Все фото удалены")
    await _show_add_service_photo_manager_for_callback(callback, state)
# РћР±СЂР°Р±РѕС‚С‡РёРєРё С‚РµРєСЃС‚РѕРІС‹С… СЃРѕРѕР±С‰РµРЅРёР№
async def process_new_service_name(message: Message, state: FSMContext, is_admin: bool):
    """РћР±СЂР°Р±РѕС‚РєР° РЅР°Р·РІР°РЅРёСЏ РЅРѕРІРѕР№ СѓСЃР»СѓРіРё"""
    if not is_admin:
        await message.answer("РЈ РІР°СЃ РЅРµС‚ РїСЂР°РІ Р°РґРјРёРЅРёСЃС‚СЂР°С‚РѕСЂР°")
        return
    
    await update_nested_state_data(
        state,
        "new_service_data",
        {},
        field_name="name",
        field_value=message.text.strip(),
    )
    await show_add_service_main_after_edit(message, state, is_admin)

async def process_new_service_description(message: Message, state: FSMContext, is_admin: bool):
    """РћР±СЂР°Р±РѕС‚РєР° РѕРїРёСЃР°РЅРёСЏ РЅРѕРІРѕР№ СѓСЃР»СѓРіРё"""
    if not is_admin:
        await message.answer("РЈ РІР°СЃ РЅРµС‚ РїСЂР°РІ Р°РґРјРёРЅРёСЃС‚СЂР°С‚РѕСЂР°")
        return
    
    await update_nested_state_data(
        state,
        "new_service_data",
        {},
        field_name="description",
        field_value=message.text.strip(),
    )
    await show_add_service_main_after_edit(message, state, is_admin)

async def process_new_service_price_weekday(message: Message, state: FSMContext, is_admin: bool):
    """РћР±СЂР°Р±РѕС‚РєР° С†РµРЅС‹ РІ Р±СѓРґРЅРё"""
    if not is_admin:
        await message.answer("РЈ РІР°СЃ РЅРµС‚ РїСЂР°РІ Р°РґРјРёРЅРёСЃС‚СЂР°С‚РѕСЂР°")
        return
    
    try:
        price = parse_positive_price(message.text, allow_zero=False)
        await update_nested_state_data(
            state,
            "new_service_data",
            {},
            field_name="price_weekday",
            field_value=price,
        )
        await show_add_service_main_after_edit(message, state, is_admin)
        
    except ValueError:
        await message.answer("вќЊ РќРµРІРµСЂРЅС‹Р№ С„РѕСЂРјР°С‚ С†РµРЅС‹. Р’РІРµРґРёС‚Рµ С‚РѕР»СЊРєРѕ С‡РёСЃР»Рѕ:")

async def process_new_service_price_weekend(message: Message, state: FSMContext, is_admin: bool):
    """РћР±СЂР°Р±РѕС‚РєР° С†РµРЅС‹ РІ РІС‹С…РѕРґРЅС‹Рµ"""
    if not is_admin:
        await message.answer("РЈ РІР°СЃ РЅРµС‚ РїСЂР°РІ Р°РґРјРёРЅРёСЃС‚СЂР°С‚РѕСЂР°")
        return
    
    try:
        price = parse_positive_price(message.text, allow_zero=False)
        await update_nested_state_data(
            state,
            "new_service_data",
            {},
            field_name="price_weekend",
            field_value=price,
        )
        await show_add_service_main_after_edit(message, state, is_admin)
        
    except ValueError:
        await message.answer("вќЊ РќРµРІРµСЂРЅС‹Р№ С„РѕСЂРјР°С‚ С†РµРЅС‹. Р’РІРµРґРёС‚Рµ С‚РѕР»СЊРєРѕ С‡РёСЃР»Рѕ:")

async def process_new_service_price_extra_weekday(message: Message, state: FSMContext, is_admin: bool):
    """РћР±СЂР°Р±РѕС‚РєР° С†РµРЅС‹ Р·Р° РґРѕРї. С‡РµР»РѕРІРµРєР° РІ Р±СѓРґРЅРё."""
    if not is_admin:
        await message.answer("РЈ РІР°СЃ РЅРµС‚ РїСЂР°РІ Р°РґРјРёРЅРёСЃС‚СЂР°С‚РѕСЂР°")
        return

    try:
        price = parse_positive_price(message.text, allow_zero=True)
        await update_nested_state_data(
            state,
            "new_service_data",
            {},
            field_name="price_extra_weekday",
            field_value=price,
        )
        await show_add_service_main_after_edit(message, state, is_admin)
    except ValueError:
        await message.answer("вќЊ РќРµРІРµСЂРЅС‹Р№ С„РѕСЂРјР°С‚ С†РµРЅС‹. Р’РІРµРґРёС‚Рµ С‡РёСЃР»Рѕ:")


async def process_new_service_price_extra_weekend(message: Message, state: FSMContext, is_admin: bool):
    """РћР±СЂР°Р±РѕС‚РєР° С†РµРЅС‹ Р·Р° РґРѕРї. С‡РµР»РѕРІРµРєР° РІ РІС‹С…РѕРґРЅС‹Рµ."""
    if not is_admin:
        await message.answer("РЈ РІР°СЃ РЅРµС‚ РїСЂР°РІ Р°РґРјРёРЅРёСЃС‚СЂР°С‚РѕСЂР°")
        return

    try:
        price = parse_positive_price(message.text, allow_zero=True)
        await update_nested_state_data(
            state,
            "new_service_data",
            {},
            field_name="price_extra_weekend",
            field_value=price,
        )
        await show_add_service_main_after_edit(message, state, is_admin)
    except ValueError:
        await message.answer("вќЊ РќРµРІРµСЂРЅС‹Р№ С„РѕСЂРјР°С‚ С†РµРЅС‹. Р’РІРµРґРёС‚Рµ С‡РёСЃР»Рѕ:")


async def process_new_service_price_group(message: Message, state: FSMContext, is_admin: bool):
    """РћР±СЂР°Р±РѕС‚РєР° С†РµРЅС‹ РѕС‚ 10 С‡РµР»РѕРІРµРє."""
    if not is_admin:
        await message.answer("РЈ РІР°СЃ РЅРµС‚ РїСЂР°РІ Р°РґРјРёРЅРёСЃС‚СЂР°С‚РѕСЂР°")
        return

    try:
        price = parse_positive_price(message.text, allow_zero=True)
        await update_nested_state_data(
            state,
            "new_service_data",
            {},
            field_name="price_group",
            field_value=price,
        )
        await show_add_service_main_after_edit(message, state, is_admin)
    except ValueError:
        await message.answer("вќЊ РќРµРІРµСЂРЅС‹Р№ С„РѕСЂРјР°С‚ С†РµРЅС‹. Р’РІРµРґРёС‚Рµ С‡РёСЃР»Рѕ:")


async def process_new_service_max_clients(message: Message, state: FSMContext, is_admin: bool):
    """РћР±СЂР°Р±РѕС‚РєР° РјР°РєСЃРёРјР°Р»СЊРЅРѕРіРѕ РєРѕР»РёС‡РµСЃС‚РІР° РєР»РёРµРЅС‚РѕРІ"""
    if not is_admin:
        await message.answer("РЈ РІР°СЃ РЅРµС‚ РїСЂР°РІ Р°РґРјРёРЅРёСЃС‚СЂР°С‚РѕСЂР°")
        return
    
    try:
        max_clients = parse_positive_int(message.text)
        await update_nested_state_data(
            state,
            "new_service_data",
            {},
            field_name="max_clients",
            field_value=max_clients,
        )
        await show_add_service_main_after_edit(message, state, is_admin)
        
    except ValueError:
        await message.answer("вќЊ РќРµРІРµСЂРЅС‹Р№ С„РѕСЂРјР°С‚. Р’РІРµРґРёС‚Рµ С‚РѕР»СЊРєРѕ С‡РёСЃР»Рѕ:")

async def process_new_service_duration(message: Message, state: FSMContext, is_admin: bool):
    """РћР±СЂР°Р±РѕС‚РєР° РґР»РёС‚РµР»СЊРЅРѕСЃС‚Рё СѓСЃР»СѓРіРё"""
    if not is_admin:
        await message.answer("РЈ РІР°СЃ РЅРµС‚ РїСЂР°РІ Р°РґРјРёРЅРёСЃС‚СЂР°С‚РѕСЂР°")
        return
    
    try:
        min_duration, step_duration = parse_duration_pair(message.text)
        await update_nested_state_data(
            state,
            "new_service_data",
            {
                "duration": f"{min_duration} РјРёРЅ (С€Р°Рі {step_duration})",
                "min_duration": min_duration,
                "step_duration": step_duration,
            },
        )
        await show_add_service_main_after_edit(message, state, is_admin)
        
    except ValueError:
        await message.answer("вќЊ РќРµРІРµСЂРЅС‹Р№ С„РѕСЂРјР°С‚. Р’РІРµРґРёС‚Рµ РІ С„РѕСЂРјР°С‚Рµ: РјРёРЅ_РґР»РёС‚РµР»СЊРЅРѕСЃС‚СЊ С€Р°Рі_РґР»РёС‚РµР»СЊРЅРѕСЃС‚Рё")

async def process_new_service_photos(message: Message, state: FSMContext, is_admin: bool):
    """РћР±СЂР°Р±РѕС‚РєР° С„РѕС‚РѕРіСЂР°С„РёР№ СѓСЃР»СѓРіРё"""
    if not is_admin:
        await message.answer("РЈ РІР°СЃ РЅРµС‚ РїСЂР°РІ Р°РґРјРёРЅРёСЃС‚СЂР°С‚РѕСЂР°")
        return

    if not message.photo:
        await message.answer("вќЊ РџРѕР¶Р°Р»СѓР№СЃС‚Р°, РѕС‚РїСЂР°РІСЊС‚Рµ С„РѕС‚РѕРіСЂР°С„РёСЋ")
        return

    temp_dir = get_temp_dir(message.from_user.id)
    try:
        photos_count = await save_service_photo(
            message,
            temp_dir,
            save_photo_func=save_message_photo,
            count_photos_func=count_photos_in_dir,
        )
    except Exception:
        await message.answer("вќЊ РќРµ СѓРґР°Р»РѕСЃСЊ СЃРѕС…СЂР°РЅРёС‚СЊ С„РѕС‚РѕРіСЂР°С„РёСЋ")
        return

    await update_nested_state_data(
        state,
        "new_service_data",
        {
            "photos_count": photos_count,
            "temp_photos_dir": str(temp_dir),
            "photo_ids": None,
        },
    )

    await message.answer(f"вњ… Р¤РѕС‚РѕРіСЂР°С„РёРё РґРѕР±Р°РІР»РµРЅС‹. Р’СЃРµРіРѕ: {photos_count}")
    await _show_add_service_photo_manager_for_message(message, state)
async def select_extra_service_callback(callback: CallbackQuery, state: FSMContext, is_admin: bool):
    """РћР±СЂР°Р±РѕС‚С‡РёРє РІС‹Р±РѕСЂР° РґРѕРїРѕР»РЅРёС‚РµР»СЊРЅРѕР№ СѓСЃР»СѓРіРё"""
    if not is_admin:
        await callback.answer("РЈ РІР°СЃ РЅРµС‚ РїСЂР°РІ Р°РґРјРёРЅРёСЃС‚СЂР°С‚РѕСЂР°", show_alert=True)
        return
    
    service_id = int(callback.data.split("_")[-1])
    data = await state.get_data()
    service_data = data.get("new_service_data", {})
    selected_ids = service_data.get("extra_services", [])
    selected_ids, was_added = toggle_extra_service(selected_ids, service_id)

    if was_added:
        await callback.answer("вњ… РЈСЃР»СѓРіР° РґРѕР±Р°РІР»РµРЅР° РІ РґРѕРїРѕР»РЅРёС‚РµР»СЊРЅС‹Рµ")
    else:
        await callback.answer("вќЊ РЈСЃР»СѓРіР° СѓРґР°Р»РµРЅР° РёР· РґРѕРїРѕР»РЅРёС‚РµР»СЊРЅС‹С…")

    await update_nested_state_data(
        state,
        "new_service_data",
        {"extra_services": selected_ids},
    )

    services = await extra_service_repo.get_all()
    active_services = get_active_extra_services(services)

    await callback.message.edit_text(
        "рџ”§ <b>Р”РѕРїРѕР»РЅРёС‚РµР»СЊРЅС‹Рµ СѓСЃР»СѓРіРё</b>\n\n"
        "Р’С‹Р±РµСЂРёС‚Рµ СѓСЃР»СѓРіРё, РєРѕС‚РѕСЂС‹Рµ РјРѕР¶РЅРѕ РґРѕР±Р°РІРёС‚СЊ Рє СЌС‚РѕР№ СѓСЃР»СѓРіРµ:",
        reply_markup=get_existing_services_keyboard(active_services, selected_ids),
        parse_mode="HTML"
    )

async def extras_done_callback(callback: CallbackQuery, state: FSMContext, is_admin: bool):
    """РћР±СЂР°Р±РѕС‚С‡РёРє РєРЅРѕРїРєРё 'Р“РѕС‚РѕРІРѕ' РґР»СЏ РґРѕРїРѕР»РЅРёС‚РµР»СЊРЅС‹С… СѓСЃР»СѓРі"""
    if not is_admin:
        await callback.answer("РЈ РІР°СЃ РЅРµС‚ РїСЂР°РІ Р°РґРјРёРЅРёСЃС‚СЂР°С‚РѕСЂР°", show_alert=True)
        return
    
    data = await state.get_data()
    service_data = data.get("new_service_data", {})
    selected_ids = service_data.get("extra_services", [])
    services = await extra_service_repo.get_all()

    await update_nested_state_data(
        state,
        "new_service_data",
        {"extras": format_selected_extras(selected_ids, services)},
    )

    await show_add_service_main_after_edit_callback(callback, state, is_admin)

async def show_add_service_main_after_edit_callback(callback: CallbackQuery, state: FSMContext, is_admin: bool):
    """РџРѕРєР°Р· РіР»Р°РІРЅРѕРіРѕ РјРµРЅСЋ РїРѕСЃР»Рµ СЂРµРґР°РєС‚РёСЂРѕРІР°РЅРёСЏ РїР°СЂР°РјРµС‚СЂР° РґР»СЏ callback."""
    data = await state.get_data()
    service_data = data.get("new_service_data", {})
    await callback.message.edit_text(
        build_add_service_editor_text(service_data),
        reply_markup=get_add_service_main_keyboard(),
        parse_mode="HTML"
    )

async def create_service_final_callback(callback: CallbackQuery, state: FSMContext, is_admin: bool):
    """РћР±СЂР°Р±РѕС‚С‡РёРє С„РёРЅР°Р»СЊРЅРѕРіРѕ СЃРѕР·РґР°РЅРёСЏ СѓСЃР»СѓРіРё."""
    if not is_admin:
        await callback.answer("РЈ РІР°СЃ РЅРµС‚ РїСЂР°РІ Р°РґРјРёРЅРёСЃС‚СЂР°С‚РѕСЂР°", show_alert=True)
        return

    data = await state.get_data()
    service_data = data.get("new_service_data", {})
    missing_list = get_missing_service_field_labels(service_data)
    if missing_list:
        await callback.answer(
            f"вќЊ Р—Р°РїРѕР»РЅРёС‚Рµ РѕР±СЏР·Р°С‚РµР»СЊРЅС‹Рµ РїРѕР»СЏ: {', '.join(missing_list)}",
            show_alert=True,
        )
        return

    try:
        service = build_service_model(service_data)
        service_id = await service_repo.create(service)

        finalize_service_photo_dir(
            service_data.get("temp_photos_dir"),
            get_service_dir(service_id),
            move_dir_contents_func=move_dir_contents,
        )

        await state.clear()
        summary = build_service_save_summary(
            service,
            service_data,
            title="РЈСЃР»СѓРіР° СѓСЃРїРµС€РЅРѕ СЃРѕР·РґР°РЅР°!",
            service_id=service_id,
        )
        await callback.message.edit_text(
            build_service_save_text(summary),
            reply_markup=get_services_management_keyboard(),
            parse_mode="HTML",
        )
    except Exception as e:
        await callback.answer(f"вќЊ РћС€РёР±РєР° РїСЂРё СЃРѕР·РґР°РЅРёРё СѓСЃР»СѓРіРё: {e}", show_alert=True)

async def show_add_service_main_after_edit(message: Message, state: FSMContext, is_admin: bool):
    """РџРѕРєР°Р· РіР»Р°РІРЅРѕРіРѕ РјРµРЅСЋ РїРѕСЃР»Рµ СЂРµРґР°РєС‚РёСЂРѕРІР°РЅРёСЏ РїР°СЂР°РјРµС‚СЂР°."""
    data = await state.get_data()
    service_data = data.get("new_service_data", {})
    await message.answer(
        build_add_service_editor_text(service_data),
        reply_markup=get_add_service_main_keyboard(),
        parse_mode="HTML"
    )

def register_add_service_new_handlers(dp: Dispatcher):
    """Р РµРіРёСЃС‚СЂР°С†РёСЏ РѕР±СЂР°Р±РѕС‚С‡РёРєРѕРІ РЅРѕРІРѕРіРѕ РґРѕР±Р°РІР»РµРЅРёСЏ СѓСЃР»СѓРі"""
    # Р“Р»Р°РІРЅРѕРµ РјРµРЅСЋ
    dp.callback_query.register(start_add_service_new, F.data == "add_service_new")
    dp.callback_query.register(show_add_service_main, F.data == "add_service_main")
    
    # РџР°СЂР°РјРµС‚СЂС‹ СѓСЃР»СѓРіРё
    dp.callback_query.register(add_service_name_callback, F.data == "add_service_name")
    dp.callback_query.register(add_service_description_callback, F.data == "add_service_description")
    dp.callback_query.register(add_service_price_menu_callback, F.data == "add_service_price_menu")
    dp.callback_query.register(add_service_max_clients_callback, F.data == "add_service_max_clients")
    dp.callback_query.register(add_service_extras_callback, F.data == "add_service_extras")
    dp.callback_query.register(add_service_duration_callback, F.data == "add_service_duration")
    dp.callback_query.register(add_service_photos_callback, F.data == "add_service_photos")
    dp.callback_query.register(add_service_photo_add_callback, F.data == "add_service_photo_add")
    dp.callback_query.register(add_service_photo_clear_callback, F.data == "add_service_photo_clear")
    dp.callback_query.register(add_service_photo_page_callback, F.data.startswith("add_service_photo_page_"))
    dp.callback_query.register(add_service_photo_delete_callback, F.data.startswith("add_service_photo_delete_"))
    
    # РњРµРЅСЋ С†РµРЅ
    dp.callback_query.register(add_service_price_weekday_callback, F.data == "add_service_price_weekday")
    dp.callback_query.register(add_service_price_weekend_callback, F.data == "add_service_price_weekend")
    dp.callback_query.register(add_service_price_extra_weekday_callback, F.data == "add_service_price_extra_weekday")
    dp.callback_query.register(add_service_price_extra_weekend_callback, F.data == "add_service_price_extra_weekend")
    dp.callback_query.register(add_service_price_group_callback, F.data == "add_service_price_group")
    
    # Р”РѕРїРѕР»РЅРёС‚РµР»СЊРЅС‹Рµ СѓСЃР»СѓРіРё
    dp.callback_query.register(select_extra_service_callback, F.data.startswith("select_extra_service_"))
    dp.callback_query.register(extras_done_callback, F.data == "extras_done")
    
    # РЎРѕР·РґР°РЅРёРµ СѓСЃР»СѓРіРё
    dp.callback_query.register(create_service_final_callback, F.data == "create_service_final")
    
    # РћР±СЂР°Р±РѕС‚РєР° С‚РµРєСЃС‚РѕРІС‹С… СЃРѕРѕР±С‰РµРЅРёР№
    dp.message.register(process_new_service_name, AdminStates.waiting_for_new_service_name)
    dp.message.register(process_new_service_description, AdminStates.waiting_for_new_service_description)
    dp.message.register(process_new_service_price_weekday, AdminStates.waiting_for_new_service_price_weekday)
    dp.message.register(process_new_service_price_weekend, AdminStates.waiting_for_new_service_price_weekend)
    dp.message.register(process_new_service_price_extra_weekday, AdminStates.waiting_for_new_service_price_extra_weekday)
    dp.message.register(process_new_service_price_extra_weekend, AdminStates.waiting_for_new_service_price_extra_weekend)
    dp.message.register(process_new_service_price_group, AdminStates.waiting_for_new_service_price_group)
    dp.message.register(process_new_service_max_clients, AdminStates.waiting_for_new_service_max_clients)
    dp.message.register(process_new_service_duration, AdminStates.waiting_for_new_service_duration)
    dp.message.register(process_new_service_photos, AdminStates.waiting_for_new_service_photos)

