from aiogram import Dispatcher, F
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext

from app.interfaces.messenger.tg.keyboards import (
    get_edit_service_main_keyboard, get_edit_service_price_keyboard,
    get_add_service_extras_keyboard, get_services_management_keyboard,
    get_existing_services_keyboard
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
from app.core.modules.admin.service_photos import save_service_photo
from app.interfaces.messenger.tg.utils.photos import (
    get_service_dir,
    count_photos_in_dir,
    clear_dir,
    save_message_photo,
)

async def start_edit_service_new(callback: CallbackQuery, state: FSMContext, is_admin: bool):
    """Начало редактирования услуги с новым интерфейсом"""
    if not is_admin:
        await callback.answer(ADMIN_DENIED_TEXT, show_alert=True)
        return
    
    # Извлекаем ID услуги из callback_data
    service_id = int(callback.data.split("_")[-1])
    
    # Получаем услугу из базы данных
    service = await service_repo.get_by_id(service_id)
    if not service:
        await callback.answer("❌ Услуга не найдена", show_alert=True)
        return
    
    # Сохраняем ID услуги в состоянии
    await state.update_data(edit_service_id=service_id)
    
    # Конвертируем данные услуги в формат для редактирования
    # Аккуратно нормализуем plus_service_ids и photo_ids, т.к. они могут быть как строкой CSV, так и числом/None
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
    
    # Сохраняем данные в состоянии
    await state.update_data(edit_service_data=service_data)
    
    # Показываем главное меню редактирования
    await show_edit_service_main(callback, state, is_admin)

async def show_edit_service_main(callback: CallbackQuery, state: FSMContext, is_admin: bool):
    """Показ главного меню редактирования услуги."""
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

async def edit_service_name_callback(callback: CallbackQuery, state: FSMContext, is_admin: bool):
    """Обработчик редактирования названия услуги"""
    if not is_admin:
        await callback.answer(ADMIN_DENIED_TEXT, show_alert=True)
        return
    
    await callback.message.edit_text(
        get_service_field_prompt("edit", "name"),
        parse_mode="HTML"
    )
    await state.set_state(AdminStates.waiting_for_edit_service_name)

async def edit_service_description_callback(callback: CallbackQuery, state: FSMContext, is_admin: bool):
    """Обработчик редактирования описания услуги"""
    if not is_admin:
        await callback.answer(ADMIN_DENIED_TEXT, show_alert=True)
        return
    
    await callback.message.edit_text(
        get_service_field_prompt("edit", "description"),
        parse_mode="HTML"
    )
    await state.set_state(AdminStates.waiting_for_edit_service_description)

async def edit_service_price_menu_callback(callback: CallbackQuery, state: FSMContext, is_admin: bool):
    """Обработчик меню цен для редактирования"""
    if not is_admin:
        await callback.answer(ADMIN_DENIED_TEXT, show_alert=True)
        return
    
    await callback.message.edit_text(
        get_service_price_menu_text("edit"),
        reply_markup=get_edit_service_price_keyboard(),
        parse_mode="HTML"
    )

async def edit_service_max_clients_callback(callback: CallbackQuery, state: FSMContext, is_admin: bool):
    """Обработчик редактирования максимального количества клиентов"""
    if not is_admin:
        await callback.answer(ADMIN_DENIED_TEXT, show_alert=True)
        return
    
    await callback.message.edit_text(
        get_service_field_prompt("edit", "max_clients"),
        parse_mode="HTML"
    )
    await state.set_state(AdminStates.waiting_for_edit_service_max_clients)

async def edit_service_extras_callback(callback: CallbackQuery, state: FSMContext, is_admin: bool):
    """Обработчик редактирования дополнительных услуг"""
    if not is_admin:
        await callback.answer(ADMIN_DENIED_TEXT, show_alert=True)
        return
    
    data = await state.get_data()
    services = await extra_service_repo.get_all()
    active_services = get_active_extra_services(services)
    
    if not active_services:
        await callback.answer("❌ Нет доступных услуг для выбора", show_alert=True)
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
    """Обработчик редактирования длительности услуги"""
    if not is_admin:
        await callback.answer(ADMIN_DENIED_TEXT, show_alert=True)
        return
    
    await callback.message.edit_text(
        get_service_field_prompt("edit", "duration"),
        parse_mode="HTML"
    )
    await state.set_state(AdminStates.waiting_for_edit_service_duration)

async def edit_service_photos_callback(callback: CallbackQuery, state: FSMContext, is_admin: bool):
    """Обработчик редактирования фотографий услуги"""
    if not is_admin:
        await callback.answer(ADMIN_DENIED_TEXT, show_alert=True)
        return
    
    await callback.message.edit_text(
        get_service_field_prompt("edit", "photos"),
        parse_mode="HTML"
    )
    await state.set_state(AdminStates.waiting_for_edit_service_photos)

# Обработчики цен
async def edit_service_price_weekday_callback(callback: CallbackQuery, state: FSMContext, is_admin: bool):
    """Обработчик редактирования цены в будни"""
    if not is_admin:
        await callback.answer(ADMIN_DENIED_TEXT, show_alert=True)
        return
    
    await callback.message.edit_text(
        get_service_field_prompt("edit", "price_weekday"),
        parse_mode="HTML"
    )
    await state.set_state(AdminStates.waiting_for_edit_service_price_weekday)

async def edit_service_price_weekend_callback(callback: CallbackQuery, state: FSMContext, is_admin: bool):
    """Обработчик редактирования цены в выходные"""
    if not is_admin:
        await callback.answer(ADMIN_DENIED_TEXT, show_alert=True)
        return
    
    await callback.message.edit_text(
        get_service_field_prompt("edit", "price_weekend"),
        parse_mode="HTML"
    )
    await state.set_state(AdminStates.waiting_for_edit_service_price_weekend)

async def edit_service_price_extra_weekday_callback(callback: CallbackQuery, state: FSMContext, is_admin: bool):
    """Обработчик редактирования цены за дополнительного клиента в будни"""
    if not is_admin:
        await callback.answer(ADMIN_DENIED_TEXT, show_alert=True)
        return
    
    await callback.message.edit_text(
        get_service_field_prompt("edit", "price_extra_weekday"),
        parse_mode="HTML"
    )
    await state.set_state(AdminStates.waiting_for_edit_service_price_extra_weekday)

async def edit_service_price_extra_weekend_callback(callback: CallbackQuery, state: FSMContext, is_admin: bool):
    """Обработчик редактирования цены за дополнительного клиента в выходные"""
    if not is_admin:
        await callback.answer(ADMIN_DENIED_TEXT, show_alert=True)
        return
    
    await callback.message.edit_text(
        get_service_field_prompt("edit", "price_extra_weekend"),
        parse_mode="HTML"
    )
    await state.set_state(AdminStates.waiting_for_edit_service_price_extra_weekend)

async def edit_service_price_group_callback(callback: CallbackQuery, state: FSMContext, is_admin: bool):
    """Обработчик редактирования групповой цены"""
    if not is_admin:
        await callback.answer(ADMIN_DENIED_TEXT, show_alert=True)
        return
    
    await callback.message.edit_text(
        get_service_field_prompt("edit", "price_group"),
        parse_mode="HTML"
    )
    await state.set_state(AdminStates.waiting_for_edit_service_price_group)

# Обработчики выбора дополнительных услуг
async def select_edit_extra_service_callback(callback: CallbackQuery, state: FSMContext, is_admin: bool):
    """Обработчик выбора дополнительной услуги при редактировании"""
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
    """Обработчик завершения выбора дополнительных услуг при редактировании"""
    if not is_admin:
        await callback.answer("У вас нет прав администратора", show_alert=True)
        return
    
    # Возвращаемся к главному меню редактирования
    await show_edit_service_main(callback, state, is_admin)

# Обработчики текстовых сообщений
async def process_edit_service_name(message: Message, state: FSMContext, is_admin: bool):
    """Обработка нового названия услуги."""
    if not is_admin:
        return

    new_name = message.text.strip()
    if not new_name:
        await message.answer("❌ Название не может быть пустым")
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
    """Обработка нового описания услуги."""
    if not is_admin:
        return

    new_description = message.text.strip()
    if not new_description:
        await message.answer("❌ Описание не может быть пустым")
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
    """Обработка новой цены в будни."""
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
        await message.answer("❌ Введите корректную цену (число)")


async def process_edit_service_price_weekend(message: Message, state: FSMContext, is_admin: bool):
    """Обработка новой цены в выходные."""
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
        await message.answer("❌ Введите корректную цену (число)")


async def process_edit_service_price_extra_weekday(message: Message, state: FSMContext, is_admin: bool):
    """Обработка новой цены за дополнительного клиента в будни."""
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
        await message.answer("❌ Введите корректную цену (число)")


async def process_edit_service_price_extra_weekend(message: Message, state: FSMContext, is_admin: bool):
    """Обработка новой цены за дополнительного клиента в выходные."""
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
        await message.answer("❌ Введите корректную цену (число)")


async def process_edit_service_price_group(message: Message, state: FSMContext, is_admin: bool):
    """Обработка новой групповой цены."""
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
        await message.answer("❌ Введите корректную цену (число)")


async def process_edit_service_max_clients(message: Message, state: FSMContext, is_admin: bool):
    """Обработка нового максимального количества клиентов."""
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
        await message.answer("❌ Введите корректные значения (целые числа)")


async def process_edit_service_duration(message: Message, state: FSMContext, is_admin: bool):
    """Обработка новой длительности услуги."""
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
        await message.answer("❌ Введите корректные значения (целые числа)")


async def process_edit_service_photos(message: Message, state: FSMContext, is_admin: bool):
    """Обработка новых фотографий услуги."""
    if not is_admin:
        return

    if not message.photo:
        await message.answer("❌ Отправьте фотографию")
        return

    data = await state.get_data()
    service_data = data.get("edit_service_data", {})
    service_id = data.get("edit_service_id")
    if not service_id:
        await message.answer("❌ Не удалось определить услугу")
        return

    service_dir = get_service_dir(service_id)
    try:
        photos_count = await save_service_photo(
            message,
            service_dir,
            save_photo_func=save_message_photo,
            count_photos_func=count_photos_in_dir,
            clear_dir_func=clear_dir,
            reset_before_save="photos_updated" not in service_data,
        )
    except Exception:
        await message.answer("❌ Не удалось сохранить фотографию")
        return

    service_data["photos_updated"] = True
    service_data["photos_count"] = photos_count
    await state.update_data(edit_service_data=service_data)
    await show_edit_service_main_after_edit(message, state, is_admin)


async def show_edit_service_main_after_edit(message: Message, state: FSMContext, is_admin: bool):
    """Показ главного меню после редактирования параметра."""
    data = await state.get_data()
    service_data = data.get("edit_service_data", {})
    await message.answer(
        build_edit_service_editor_text(service_data),
        reply_markup=get_edit_service_main_keyboard(),
        parse_mode="HTML",
    )


async def save_edit_service_callback(callback: CallbackQuery, state: FSMContext, is_admin: bool):
    """Обработчик сохранения изменений услуги."""
    if not is_admin:
        await callback.answer("У вас нет прав администратора", show_alert=True)
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
                title="Услуга успешно обновлена!",
                service_id=service_id,
            )
            await callback.message.edit_text(
                build_service_save_text(summary),
                reply_markup=get_services_management_keyboard(),
                parse_mode="HTML",
            )
        else:
            await callback.answer("❌ Ошибка при обновлении услуги", show_alert=True)
    except Exception as e:
        await callback.answer(f"❌ Ошибка при обновлении услуги: {e}", show_alert=True)


def register_edit_service_new_handlers(dp: Dispatcher):
    """Регистрация обработчиков редактирования услуг."""

    dp.callback_query.register(start_edit_service_new, F.data.startswith("edit_service_new_"))
    dp.callback_query.register(show_edit_service_main, F.data == "show_edit_service_main")

    dp.callback_query.register(edit_service_name_callback, F.data == "edit_service_name")
    dp.callback_query.register(edit_service_description_callback, F.data == "edit_service_description")
    dp.callback_query.register(edit_service_price_menu_callback, F.data == "edit_service_price")
    dp.callback_query.register(edit_service_max_clients_callback, F.data == "edit_service_max_clients")
    dp.callback_query.register(edit_service_extras_callback, F.data == "edit_service_extras")
    dp.callback_query.register(edit_service_duration_callback, F.data == "edit_service_duration")
    dp.callback_query.register(edit_service_photos_callback, F.data == "edit_service_photos")

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
