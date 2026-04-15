from aiogram import Dispatcher, F
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext

from app.interfaces.messenger.tg.keyboards import (
    get_add_service_main_keyboard, get_add_service_price_keyboard, 
    get_add_service_extras_keyboard, get_services_management_keyboard,
    get_existing_services_keyboard
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
from app.core.modules.admin.service_photos import finalize_service_photo_dir, save_service_photo
from app.interfaces.messenger.tg.utils.photos import (
    get_temp_dir,
    get_service_dir,
    count_photos_in_dir,
    clear_dir,
    save_message_photo,
    move_dir_contents,
)

async def start_add_service_new(callback: CallbackQuery, state: FSMContext, is_admin: bool):
    """Начало добавления новой услуги с новым интерфейсом"""
    if not is_admin:
        await callback.answer(ADMIN_DENIED_TEXT, show_alert=True)
        return
    
    # Очищаем предыдущие данные
    await state.clear()
    # Очищаем временные фото для текущего администратора
    temp_dir = get_temp_dir(callback.from_user.id)
    clear_dir(temp_dir)
    
    await callback.message.edit_text(
        get_service_start_text("add"),
        reply_markup=get_add_service_main_keyboard(),
        parse_mode="HTML",
    )

async def show_add_service_main(callback: CallbackQuery, state: FSMContext, is_admin: bool):
    """Показ главного меню добавления услуги с текущими данными."""
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
    """Обработчик кнопки 'Название'"""
    if not is_admin:
        await callback.answer(ADMIN_DENIED_TEXT, show_alert=True)
        return
    
    await callback.message.edit_text(
        get_service_field_prompt("add", "name"),
        parse_mode="HTML"
    )
    await state.set_state(AdminStates.waiting_for_new_service_name)

async def add_service_description_callback(callback: CallbackQuery, state: FSMContext, is_admin: bool):
    """Обработчик кнопки 'Описание'"""
    if not is_admin:
        await callback.answer(ADMIN_DENIED_TEXT, show_alert=True)
        return
    
    await callback.message.edit_text(
        get_service_field_prompt("add", "description"),
        parse_mode="HTML"
    )
    await state.set_state(AdminStates.waiting_for_new_service_description)

async def add_service_price_menu_callback(callback: CallbackQuery, state: FSMContext, is_admin: bool):
    """Обработчик кнопки 'Цена' - показ меню цен"""
    if not is_admin:
        await callback.answer(ADMIN_DENIED_TEXT, show_alert=True)
        return
    
    await callback.message.edit_text(
        get_service_price_menu_text("add"),
        reply_markup=get_add_service_price_keyboard(),
        parse_mode="HTML"
    )

async def add_service_price_weekday_callback(callback: CallbackQuery, state: FSMContext, is_admin: bool):
    """Обработчик кнопки 'Цена (будни)'"""
    if not is_admin:
        await callback.answer(ADMIN_DENIED_TEXT, show_alert=True)
        return
    
    await callback.message.edit_text(
        get_service_field_prompt("add", "price_weekday"),
        parse_mode="HTML"
    )
    await state.set_state(AdminStates.waiting_for_new_service_price_weekday)

async def add_service_price_weekend_callback(callback: CallbackQuery, state: FSMContext, is_admin: bool):
    """Обработчик кнопки 'Цена (выходные)'"""
    if not is_admin:
        await callback.answer(ADMIN_DENIED_TEXT, show_alert=True)
        return
    
    await callback.message.edit_text(
        get_service_field_prompt("add", "price_weekend"),
        parse_mode="HTML"
    )
    await state.set_state(AdminStates.waiting_for_new_service_price_weekend)

async def add_service_price_extra_weekday_callback(callback: CallbackQuery, state: FSMContext, is_admin: bool):
    """Обработчик кнопки цены за дополнительного клиента в будни."""
    if not is_admin:
        await callback.answer(ADMIN_DENIED_TEXT, show_alert=True)
        return

    await callback.message.edit_text(
        get_service_field_prompt("add", "price_extra_weekday"),
        parse_mode="HTML",
    )
    await state.set_state(AdminStates.waiting_for_new_service_price_extra_weekday)


async def add_service_price_extra_weekend_callback(callback: CallbackQuery, state: FSMContext, is_admin: bool):
    """Обработчик кнопки цены за дополнительного клиента в выходные."""
    if not is_admin:
        await callback.answer(ADMIN_DENIED_TEXT, show_alert=True)
        return

    await callback.message.edit_text(
        get_service_field_prompt("add", "price_extra_weekend"),
        parse_mode="HTML",
    )
    await state.set_state(AdminStates.waiting_for_new_service_price_extra_weekend)


async def add_service_price_group_callback(callback: CallbackQuery, state: FSMContext, is_admin: bool):
    """Обработчик кнопки цены для группы (от 10 человек)."""
    if not is_admin:
        await callback.answer(ADMIN_DENIED_TEXT, show_alert=True)
        return

    await callback.message.edit_text(
        get_service_field_prompt("add", "price_group"),
        parse_mode="HTML",
    )
    await state.set_state(AdminStates.waiting_for_new_service_price_group)

async def add_service_max_clients_callback(callback: CallbackQuery, state: FSMContext, is_admin: bool):
    """Обработчик кнопки 'Макс. человек'"""
    if not is_admin:
        await callback.answer(ADMIN_DENIED_TEXT, show_alert=True)
        return
    
    await callback.message.edit_text(
        get_service_field_prompt("add", "max_clients"),
        parse_mode="HTML"
    )
    await state.set_state(AdminStates.waiting_for_new_service_max_clients)

async def add_service_extras_callback(callback: CallbackQuery, state: FSMContext, is_admin: bool):
    """Обработчик кнопки 'Доп. услуги'"""
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
    """Обработчик кнопки 'Длительность'"""
    if not is_admin:
        await callback.answer(ADMIN_DENIED_TEXT, show_alert=True)
        return
    
    await callback.message.edit_text(
        get_service_field_prompt("add", "duration"),
        parse_mode="HTML"
    )
    await state.set_state(AdminStates.waiting_for_new_service_duration)

async def add_service_photos_callback(callback: CallbackQuery, state: FSMContext, is_admin: bool):
    """Обработчик кнопки 'Фото'"""
    if not is_admin:
        await callback.answer(ADMIN_DENIED_TEXT, show_alert=True)
        return
    
    await callback.message.edit_text(
        get_service_field_prompt("add", "photos"),
        parse_mode="HTML"
    )
    await state.set_state(AdminStates.waiting_for_new_service_photos)

# Обработчики текстовых сообщений
async def process_new_service_name(message: Message, state: FSMContext, is_admin: bool):
    """Обработка названия новой услуги"""
    if not is_admin:
        await message.answer("У вас нет прав администратора")
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
    """Обработка описания новой услуги"""
    if not is_admin:
        await message.answer("У вас нет прав администратора")
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
    """Обработка цены в будни"""
    if not is_admin:
        await message.answer("У вас нет прав администратора")
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
        await message.answer("❌ Неверный формат цены. Введите только число:")

async def process_new_service_price_weekend(message: Message, state: FSMContext, is_admin: bool):
    """Обработка цены в выходные"""
    if not is_admin:
        await message.answer("У вас нет прав администратора")
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
        await message.answer("❌ Неверный формат цены. Введите только число:")

async def process_new_service_price_extra_weekday(message: Message, state: FSMContext, is_admin: bool):
    """Обработка цены за доп. человека в будни."""
    if not is_admin:
        await message.answer("У вас нет прав администратора")
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
        await message.answer("❌ Неверный формат цены. Введите число:")


async def process_new_service_price_extra_weekend(message: Message, state: FSMContext, is_admin: bool):
    """Обработка цены за доп. человека в выходные."""
    if not is_admin:
        await message.answer("У вас нет прав администратора")
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
        await message.answer("❌ Неверный формат цены. Введите число:")


async def process_new_service_price_group(message: Message, state: FSMContext, is_admin: bool):
    """Обработка цены от 10 человек."""
    if not is_admin:
        await message.answer("У вас нет прав администратора")
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
        await message.answer("❌ Неверный формат цены. Введите число:")


async def process_new_service_max_clients(message: Message, state: FSMContext, is_admin: bool):
    """Обработка максимального количества клиентов"""
    if not is_admin:
        await message.answer("У вас нет прав администратора")
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
        await message.answer("❌ Неверный формат. Введите только число:")

async def process_new_service_duration(message: Message, state: FSMContext, is_admin: bool):
    """Обработка длительности услуги"""
    if not is_admin:
        await message.answer("У вас нет прав администратора")
        return
    
    try:
        min_duration, step_duration = parse_duration_pair(message.text)
        await update_nested_state_data(
            state,
            "new_service_data",
            {
                "duration": f"{min_duration} мин (шаг {step_duration})",
                "min_duration": min_duration,
                "step_duration": step_duration,
            },
        )
        await show_add_service_main_after_edit(message, state, is_admin)
        
    except ValueError:
        await message.answer("❌ Неверный формат. Введите в формате: мин_длительность шаг_длительности")

async def process_new_service_photos(message: Message, state: FSMContext, is_admin: bool):
    """Обработка фотографий услуги"""
    if not is_admin:
        await message.answer("У вас нет прав администратора")
        return
    
    if not message.photo:
        await message.answer("❌ Пожалуйста, отправьте фотографию")
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
        await message.answer("❌ Не удалось сохранить фотографию")
        return

    await update_nested_state_data(
        state,
        "new_service_data",
        {
            "photos_count": photos_count,
            "temp_photos_dir": str(temp_dir),
        },
    )

    await message.answer(f"✅ Фотография добавлена! Всего: {photos_count}")

    # Возвращаемся к главному меню
    await show_add_service_main_after_edit(message, state, is_admin)

async def select_extra_service_callback(callback: CallbackQuery, state: FSMContext, is_admin: bool):
    """Обработчик выбора дополнительной услуги"""
    if not is_admin:
        await callback.answer("У вас нет прав администратора", show_alert=True)
        return
    
    service_id = int(callback.data.split("_")[-1])
    data = await state.get_data()
    service_data = data.get("new_service_data", {})
    selected_ids = service_data.get("extra_services", [])
    selected_ids, was_added = toggle_extra_service(selected_ids, service_id)

    if was_added:
        await callback.answer("✅ Услуга добавлена в дополнительные")
    else:
        await callback.answer("❌ Услуга удалена из дополнительных")

    await update_nested_state_data(
        state,
        "new_service_data",
        {"extra_services": selected_ids},
    )

    services = await extra_service_repo.get_all()
    active_services = get_active_extra_services(services)

    await callback.message.edit_text(
        "🔧 <b>Дополнительные услуги</b>\n\n"
        "Выберите услуги, которые можно добавить к этой услуге:",
        reply_markup=get_existing_services_keyboard(active_services, selected_ids),
        parse_mode="HTML"
    )

async def extras_done_callback(callback: CallbackQuery, state: FSMContext, is_admin: bool):
    """Обработчик кнопки 'Готово' для дополнительных услуг"""
    if not is_admin:
        await callback.answer("У вас нет прав администратора", show_alert=True)
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
    """Показ главного меню после редактирования параметра для callback."""
    data = await state.get_data()
    service_data = data.get("new_service_data", {})
    await callback.message.edit_text(
        build_add_service_editor_text(service_data),
        reply_markup=get_add_service_main_keyboard(),
        parse_mode="HTML"
    )

async def create_service_final_callback(callback: CallbackQuery, state: FSMContext, is_admin: bool):
    """Обработчик финального создания услуги."""
    if not is_admin:
        await callback.answer("У вас нет прав администратора", show_alert=True)
        return

    data = await state.get_data()
    service_data = data.get("new_service_data", {})
    missing_list = get_missing_service_field_labels(service_data)
    if missing_list:
        await callback.answer(
            f"❌ Заполните обязательные поля: {', '.join(missing_list)}",
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
            title="Услуга успешно создана!",
            service_id=service_id,
        )
        await callback.message.edit_text(
            build_service_save_text(summary),
            reply_markup=get_services_management_keyboard(),
            parse_mode="HTML",
        )
    except Exception as e:
        await callback.answer(f"❌ Ошибка при создании услуги: {e}", show_alert=True)

async def show_add_service_main_after_edit(message: Message, state: FSMContext, is_admin: bool):
    """Показ главного меню после редактирования параметра."""
    data = await state.get_data()
    service_data = data.get("new_service_data", {})
    await message.answer(
        build_add_service_editor_text(service_data),
        reply_markup=get_add_service_main_keyboard(),
        parse_mode="HTML"
    )

def register_add_service_new_handlers(dp: Dispatcher):
    """Регистрация обработчиков нового добавления услуг"""
    # Главное меню
    dp.callback_query.register(start_add_service_new, F.data == "add_service_new")
    dp.callback_query.register(show_add_service_main, F.data == "add_service_main")
    
    # Параметры услуги
    dp.callback_query.register(add_service_name_callback, F.data == "add_service_name")
    dp.callback_query.register(add_service_description_callback, F.data == "add_service_description")
    dp.callback_query.register(add_service_price_menu_callback, F.data == "add_service_price_menu")
    dp.callback_query.register(add_service_max_clients_callback, F.data == "add_service_max_clients")
    dp.callback_query.register(add_service_extras_callback, F.data == "add_service_extras")
    dp.callback_query.register(add_service_duration_callback, F.data == "add_service_duration")
    dp.callback_query.register(add_service_photos_callback, F.data == "add_service_photos")
    
    # Меню цен
    dp.callback_query.register(add_service_price_weekday_callback, F.data == "add_service_price_weekday")
    dp.callback_query.register(add_service_price_weekend_callback, F.data == "add_service_price_weekend")
    dp.callback_query.register(add_service_price_extra_weekday_callback, F.data == "add_service_price_extra_weekday")
    dp.callback_query.register(add_service_price_extra_weekend_callback, F.data == "add_service_price_extra_weekend")
    dp.callback_query.register(add_service_price_group_callback, F.data == "add_service_price_group")
    
    # Дополнительные услуги
    dp.callback_query.register(select_extra_service_callback, F.data.startswith("select_extra_service_"))
    dp.callback_query.register(extras_done_callback, F.data == "extras_done")
    
    # Создание услуги
    dp.callback_query.register(create_service_final_callback, F.data == "create_service_final")
    
    # Обработка текстовых сообщений
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
