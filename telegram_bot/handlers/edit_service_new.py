from aiogram import Dispatcher, F
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext

from telegram_bot.keyboards import (
    get_edit_service_main_keyboard, get_add_service_price_keyboard, 
    get_add_service_extras_keyboard, get_services_management_keyboard,
    get_existing_services_keyboard
)
from telegram_bot.states import AdminStates
from database import service_repo
from database.models import Service
from telegram_bot.utils.photos import (
    get_service_dir,
    count_photos_in_dir,
    clear_dir,
    save_message_photo,
)

async def start_edit_service_new(callback: CallbackQuery, state: FSMContext, is_admin: bool):
    """Начало редактирования услуги с новым интерфейсом"""
    if not is_admin:
        await callback.answer("У вас нет прав администратора", show_alert=True)
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
        'photos_count': photos_count
    }
    
    # Сохраняем данные в состоянии
    await state.update_data(edit_service_data=service_data)
    
    # Показываем главное меню редактирования
    await show_edit_service_main(callback, state, is_admin)

async def show_edit_service_main(callback: CallbackQuery, state: FSMContext, is_admin: bool):
    """Показ главного меню редактирования услуги"""
    data = await state.get_data()
    service_data = data.get("edit_service_data", {})
    
    # Формируем текст с текущими данными
    text = "🔧 <b>Редактирование услуги</b>\n\n"
    text += f"📸 <b>Название:</b> {service_data.get('name', 'Не указано')}\n"
    text += f"📝 <b>Описание:</b> {service_data.get('description', 'Не указано')[:50]}...\n" if len(service_data.get('description', '')) > 50 else f"📝 <b>Описание:</b> {service_data.get('description', 'Не указано')}\n"
    
    # Цены
    price_text = f"{service_data.get('price_weekday', 0)}₽ - {service_data.get('price_weekend', 0)}₽"
    if service_data.get('price_extra_weekday', 0) > 0:
        price_text += f" (+{service_data.get('price_extra_weekday', 0)}₽ доп.)"
    text += f"💰 <b>Цены:</b> {price_text}\n"
    
    text += f"👥 <b>Макс. человек:</b> {service_data.get('max_clients', 'Не указано')}\n"
    
    # Дополнительные услуги
    extras_text = service_data.get('extras', 'Не выбрано')
    if service_data.get('extra_services'):
        extras_text = f"{len(service_data.get('extra_services', []))} услуг"
    text += f"🔧 <b>Доп. услуги:</b> {extras_text}\n"
    
    # Длительность
    duration_text = f"{service_data.get('min_duration', 0)} мин. (шаг {service_data.get('step_duration', 0)})"
    text += f"⏰ <b>Длительность:</b> {duration_text}\n"
    
    # Фото
    photos_count = service_data.get('photos_count', 0)
    if photos_count > 0:
        text += f"📸 <b>Фото:</b> {photos_count} шт.\n"
    else:
        text += f"📸 <b>Фото:</b> Не загружены\n"
    text += "\n"
    text += "Выберите параметр для редактирования:"
    
    await callback.message.edit_text(
        text,
        reply_markup=get_edit_service_main_keyboard(),
        parse_mode="HTML"
    )

async def edit_service_name_callback(callback: CallbackQuery, state: FSMContext, is_admin: bool):
    """Обработчик редактирования названия услуги"""
    if not is_admin:
        await callback.answer("У вас нет прав администратора", show_alert=True)
        return
    
    await callback.message.edit_text(
        "📸 <b>Редактирование названия</b>\n\nВведите новое название услуги:",
        parse_mode="HTML"
    )
    await state.set_state(AdminStates.waiting_for_edit_service_name)

async def edit_service_description_callback(callback: CallbackQuery, state: FSMContext, is_admin: bool):
    """Обработчик редактирования описания услуги"""
    if not is_admin:
        await callback.answer("У вас нет прав администратора", show_alert=True)
        return
    
    await callback.message.edit_text(
        "📝 <b>Редактирование описания</b>\n\nВведите новое описание услуги:",
        parse_mode="HTML"
    )
    await state.set_state(AdminStates.waiting_for_edit_service_description)

async def edit_service_price_menu_callback(callback: CallbackQuery, state: FSMContext, is_admin: bool):
    """Обработчик меню цен для редактирования"""
    if not is_admin:
        await callback.answer("У вас нет прав администратора", show_alert=True)
        return
    
    await callback.message.edit_text(
        "💰 <b>Редактирование цен</b>\n\nВыберите тип цены для редактирования:",
        reply_markup=get_add_service_price_keyboard(),
        parse_mode="HTML"
    )

async def edit_service_max_clients_callback(callback: CallbackQuery, state: FSMContext, is_admin: bool):
    """Обработчик редактирования максимального количества клиентов"""
    if not is_admin:
        await callback.answer("У вас нет прав администратора", show_alert=True)
        return
    
    await callback.message.edit_text(
        "👥 <b>Редактирование максимального количества клиентов</b>\n\nВведите максимальное количество клиентов:",
        parse_mode="HTML"
    )
    await state.set_state(AdminStates.waiting_for_edit_service_max_clients)

async def edit_service_extras_callback(callback: CallbackQuery, state: FSMContext, is_admin: bool):
    """Обработчик редактирования дополнительных услуг"""
    if not is_admin:
        await callback.answer("У вас нет прав администратора", show_alert=True)
        return
    
    # Получаем все активные услуги
    data = await state.get_data()
    services = await service_repo.get_all()
    active_services = [s for s in services if s.is_active and s.id != data.get("edit_service_id")]
    
    if not active_services:
        await callback.answer("❌ Нет доступных услуг для выбора", show_alert=True)
        return
    
    # Получаем текущие выбранные услуги
    data = await state.get_data()
    service_data = data.get("edit_service_data", {})
    selected_services = service_data.get('extra_services', [])
    
    await callback.message.edit_text(
        "🔧 <b>Редактирование дополнительных услуг</b>\n\nВыберите дополнительные услуги:",
        reply_markup=get_existing_services_keyboard(active_services, selected_services),
        parse_mode="HTML"
    )

async def edit_service_duration_callback(callback: CallbackQuery, state: FSMContext, is_admin: bool):
    """Обработчик редактирования длительности услуги"""
    if not is_admin:
        await callback.answer("У вас нет прав администратора", show_alert=True)
        return
    
    await callback.message.edit_text(
        "⏰ <b>Редактирование длительности</b>\n\nВведите длительность в формате: минимальная_длительность шаг_длительности\nНапример: 60 30",
        parse_mode="HTML"
    )
    await state.set_state(AdminStates.waiting_for_edit_service_duration)

async def edit_service_photos_callback(callback: CallbackQuery, state: FSMContext, is_admin: bool):
    """Обработчик редактирования фотографий услуги"""
    if not is_admin:
        await callback.answer("У вас нет прав администратора", show_alert=True)
        return
    
    await callback.message.edit_text(
        "📸 <b>Редактирование фотографий</b>\n\nОтправьте новые фотографии услуги (можно несколько). Новые фотографии заменят старые:",
        parse_mode="HTML"
    )
    await state.set_state(AdminStates.waiting_for_edit_service_photos)

# Обработчики цен
async def edit_service_price_weekday_callback(callback: CallbackQuery, state: FSMContext, is_admin: bool):
    """Обработчик редактирования цены в будни"""
    if not is_admin:
        await callback.answer("У вас нет прав администратора", show_alert=True)
        return
    
    await callback.message.edit_text(
        "💰 <b>Цена в будни</b>\n\nВведите цену в будни:",
        parse_mode="HTML"
    )
    await state.set_state(AdminStates.waiting_for_edit_service_price_weekday)

async def edit_service_price_weekend_callback(callback: CallbackQuery, state: FSMContext, is_admin: bool):
    """Обработчик редактирования цены в выходные"""
    if not is_admin:
        await callback.answer("У вас нет прав администратора", show_alert=True)
        return
    
    await callback.message.edit_text(
        "💰 <b>Цена в выходные</b>\n\nВведите цену в выходные:",
        parse_mode="HTML"
    )
    await state.set_state(AdminStates.waiting_for_edit_service_price_weekend)

async def edit_service_price_extra_weekday_callback(callback: CallbackQuery, state: FSMContext, is_admin: bool):
    """Обработчик редактирования цены за дополнительного клиента в будни"""
    if not is_admin:
        await callback.answer("У вас нет прав администратора", show_alert=True)
        return
    
    await callback.message.edit_text(
        "💰 <b>Цена за дополнительного клиента (будни)</b>\n\nВведите цену за дополнительного клиента в будни:",
        parse_mode="HTML"
    )
    await state.set_state(AdminStates.waiting_for_edit_service_price_extra_weekday)

async def edit_service_price_extra_weekend_callback(callback: CallbackQuery, state: FSMContext, is_admin: bool):
    """Обработчик редактирования цены за дополнительного клиента в выходные"""
    if not is_admin:
        await callback.answer("У вас нет прав администратора", show_alert=True)
        return
    
    await callback.message.edit_text(
        "💰 <b>Цена за дополнительного клиента (выходные)</b>\n\nВведите цену за дополнительного клиента в выходные:",
        parse_mode="HTML"
    )
    await state.set_state(AdminStates.waiting_for_edit_service_price_extra_weekend)

async def edit_service_price_group_callback(callback: CallbackQuery, state: FSMContext, is_admin: bool):
    """Обработчик редактирования групповой цены"""
    if not is_admin:
        await callback.answer("У вас нет прав администратора", show_alert=True)
        return
    
    await callback.message.edit_text(
        "💰 <b>Групповая цена</b>\n\nВведите групповую цену (от 10 человек):",
        parse_mode="HTML"
    )
    await state.set_state(AdminStates.waiting_for_edit_service_price_group)

# Обработчики выбора дополнительных услуг
async def select_edit_extra_service_callback(callback: CallbackQuery, state: FSMContext, is_admin: bool):
    """Обработчик выбора дополнительной услуги при редактировании"""
    if not is_admin:
        await callback.answer("У вас нет прав администратора", show_alert=True)
        return
    
    service_id = int(callback.data.split("_")[-1])
    
    # Получаем текущие данные
    data = await state.get_data()
    service_data = data.get("edit_service_data", {})
    selected_services = service_data.get('extra_services', [])
    
    # Переключаем выбор
    if service_id in selected_services:
        selected_services.remove(service_id)
    else:
        selected_services.append(service_id)
    
    # Обновляем данные
    service_data['extra_services'] = selected_services
    await state.update_data(edit_service_data=service_data)
    
    # Получаем услуги для обновления клавиатуры
    services = await service_repo.get_all()
    active_services = [s for s in services if s.is_active and s.id != data.get("edit_service_id")]
    
    await callback.message.edit_text(
        "🔧 <b>Редактирование дополнительных услуг</b>\n\nВыберите дополнительные услуги:",
        reply_markup=get_existing_services_keyboard(active_services, selected_services),
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
    """Обработка нового названия услуги"""
    if not is_admin:
        return
    
    new_name = message.text.strip()
    if not new_name:
        await message.answer("❌ Название не может быть пустым")
        return
    
    # Обновляем данные
    data = await state.get_data()
    service_data = data.get("edit_service_data", {})
    service_data['name'] = new_name
    await state.update_data(edit_service_data=service_data)
    
    # Показываем обновленное меню
    await show_edit_service_main_after_edit(message, state, is_admin)

async def process_edit_service_description(message: Message, state: FSMContext, is_admin: bool):
    """Обработка нового описания услуги"""
    if not is_admin:
        return
    
    new_description = message.text.strip()
    if not new_description:
        await message.answer("❌ Описание не может быть пустым")
        return
    
    # Обновляем данные
    data = await state.get_data()
    service_data = data.get("edit_service_data", {})
    service_data['description'] = new_description
    await state.update_data(edit_service_data=service_data)
    
    # Показываем обновленное меню
    await show_edit_service_main_after_edit(message, state, is_admin)

async def process_edit_service_price_weekday(message: Message, state: FSMContext, is_admin: bool):
    """Обработка новой цены в будни"""
    if not is_admin:
        return
    
    try:
        new_price = float(message.text.strip())
        if new_price < 0:
            await message.answer("❌ Цена не может быть отрицательной")
            return
        
        # Обновляем данные
        data = await state.get_data()
        service_data = data.get("edit_service_data", {})
        service_data['price_weekday'] = new_price
        await state.update_data(edit_service_data=service_data)
        
        # Показываем обновленное меню
        await show_edit_service_main_after_edit(message, state, is_admin)
        
    except ValueError:
        await message.answer("❌ Введите корректную цену (число)")

async def process_edit_service_price_weekend(message: Message, state: FSMContext, is_admin: bool):
    """Обработка новой цены в выходные"""
    if not is_admin:
        return
    
    try:
        new_price = float(message.text.strip())
        if new_price < 0:
            await message.answer("❌ Цена не может быть отрицательной")
            return
        
        # Обновляем данные
        data = await state.get_data()
        service_data = data.get("edit_service_data", {})
        service_data['price_weekend'] = new_price
        await state.update_data(edit_service_data=service_data)
        
        # Показываем обновленное меню
        await show_edit_service_main_after_edit(message, state, is_admin)
        
    except ValueError:
        await message.answer("❌ Введите корректную цену (число)")

async def process_edit_service_price_extra_weekday(message: Message, state: FSMContext, is_admin: bool):
    """Обработка новой цены за дополнительного клиента в будни"""
    if not is_admin:
        return
    
    try:
        new_price = float(message.text.strip())
        if new_price < 0:
            await message.answer("❌ Цена не может быть отрицательной")
            return
        
        # Обновляем данные
        data = await state.get_data()
        service_data = data.get("edit_service_data", {})
        service_data['price_extra_weekday'] = new_price
        await state.update_data(edit_service_data=service_data)
        
        # Показываем обновленное меню
        await show_edit_service_main_after_edit(message, state, is_admin)
        
    except ValueError:
        await message.answer("❌ Введите корректную цену (число)")

async def process_edit_service_price_extra_weekend(message: Message, state: FSMContext, is_admin: bool):
    """Обработка новой цены за дополнительного клиента в выходные"""
    if not is_admin:
        return
    
    try:
        new_price = float(message.text.strip())
        if new_price < 0:
            await message.answer("❌ Цена не может быть отрицательной")
            return
        
        # Обновляем данные
        data = await state.get_data()
        service_data = data.get("edit_service_data", {})
        service_data['price_extra_weekend'] = new_price
        await state.update_data(edit_service_data=service_data)
        
        # Показываем обновленное меню
        await show_edit_service_main_after_edit(message, state, is_admin)
        
    except ValueError:
        await message.answer("❌ Введите корректную цену (число)")

async def process_edit_service_price_group(message: Message, state: FSMContext, is_admin: bool):
    """Обработка новой групповой цены"""
    if not is_admin:
        return
    
    try:
        new_price = float(message.text.strip())
        if new_price < 0:
            await message.answer("❌ Цена не может быть отрицательной")
            return
        
        # Обновляем данные
        data = await state.get_data()
        service_data = data.get("edit_service_data", {})
        service_data['price_group'] = new_price
        await state.update_data(edit_service_data=service_data)
        
        # Показываем обновленное меню
        await show_edit_service_main_after_edit(message, state, is_admin)
        
    except ValueError:
        await message.answer("❌ Введите корректную цену (число)")

async def process_edit_service_max_clients(message: Message, state: FSMContext, is_admin: bool):
    """Обработка нового максимального количества клиентов"""
    if not is_admin:
        return
    
    try:
        new_max_clients = int(message.text.strip())
        if new_max_clients < 1:
            await message.answer("❌ Количество клиентов должно быть больше 0")
            return
        
        # Обновляем данные
        data = await state.get_data()
        service_data = data.get("edit_service_data", {})
        service_data['max_clients'] = new_max_clients
        await state.update_data(edit_service_data=service_data)
        
        # Показываем обновленное меню
        await show_edit_service_main_after_edit(message, state, is_admin)
        
    except ValueError:
        await message.answer("❌ Введите корректное количество клиентов (целое число)")

async def process_edit_service_duration(message: Message, state: FSMContext, is_admin: bool):
    """Обработка новой длительности услуги"""
    if not is_admin:
        return
    
    try:
        parts = message.text.strip().split()
        if len(parts) != 2:
            await message.answer("❌ Введите длительность в формате: минимальная_длительность шаг_длительности")
            return
        
        min_duration = int(parts[0])
        step_duration = int(parts[1])
        
        if min_duration < 1 or step_duration < 1:
            await message.answer("❌ Длительность и шаг должны быть больше 0")
            return
        
        # Обновляем данные
        data = await state.get_data()
        service_data = data.get("edit_service_data", {})
        service_data['min_duration'] = min_duration
        service_data['step_duration'] = step_duration
        await state.update_data(edit_service_data=service_data)
        
        # Показываем обновленное меню
        await show_edit_service_main_after_edit(message, state, is_admin)
        
    except ValueError:
        await message.answer("❌ Введите корректные значения (целые числа)")

async def process_edit_service_photos(message: Message, state: FSMContext, is_admin: bool):
    """Обработка новых фотографий услуги"""
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

    # Если это первая фотография, очищаем старые
    if 'photos_updated' not in service_data:
        clear_dir(service_dir)
        service_data['photos_updated'] = True

    try:
        await save_message_photo(message, service_dir)
    except Exception:
        await message.answer("❌ Не удалось сохранить фотографию")
        return

    service_data['photos_count'] = count_photos_in_dir(service_dir)
    await state.update_data(edit_service_data=service_data)
    
    # Показываем обновленное меню
    await show_edit_service_main_after_edit(message, state, is_admin)

async def show_edit_service_main_after_edit(message: Message, state: FSMContext, is_admin: bool):
    """Показ главного меню после редактирования параметра"""
    # Получаем данные из состояния
    data = await state.get_data()
    service_data = data.get("edit_service_data", {})
    
    # Формируем текст с текущими данными
    text = "🔧 <b>Редактирование услуги</b>\n\n"
    text += f"📸 <b>Название:</b> {service_data.get('name', 'Не указано')}\n"
    text += f"📝 <b>Описание:</b> {service_data.get('description', 'Не указано')[:50]}...\n" if len(service_data.get('description', '')) > 50 else f"📝 <b>Описание:</b> {service_data.get('description', 'Не указано')}\n"
    
    # Цены
    price_text = f"{service_data.get('price_weekday', 0)}₽ - {service_data.get('price_weekend', 0)}₽"
    if service_data.get('price_extra_weekday', 0) > 0:
        price_text += f" (+{service_data.get('price_extra_weekday', 0)}₽ доп.)"
    text += f"💰 <b>Цены:</b> {price_text}\n"
    
    text += f"👥 <b>Макс. человек:</b> {service_data.get('max_clients', 'Не указано')}\n"
    
    # Дополнительные услуги
    extras_text = service_data.get('extras', 'Не выбрано')
    if service_data.get('extra_services'):
        extras_text = f"{len(service_data.get('extra_services', []))} услуг"
    text += f"🔧 <b>Доп. услуги:</b> {extras_text}\n"
    
    # Длительность
    duration_text = f"{service_data.get('min_duration', 0)} мин. (шаг {service_data.get('step_duration', 0)})"
    text += f"⏰ <b>Длительность:</b> {duration_text}\n"
    
    # Фото
    photos_count = service_data.get('photos_count', 0)
    if photos_count > 0:
        text += f"📸 <b>Фото:</b> {photos_count} шт.\n"
    else:
        text += f"📸 <b>Фото:</b> Не загружены\n"
    text += "\n"
    text += "Выберите параметр для редактирования:"
    
    await message.answer(
        text,
        reply_markup=get_edit_service_main_keyboard(),
        parse_mode="HTML"
    )

async def save_edit_service_callback(callback: CallbackQuery, state: FSMContext, is_admin: bool):
    """Обработчик сохранения изменений услуги"""
    if not is_admin:
        await callback.answer("У вас нет прав администратора", show_alert=True)
        return
    
    # Получаем данные из состояния
    data = await state.get_data()
    service_data = data.get("edit_service_data", {})
    service_id = data.get("edit_service_id")
    
    try:
        # Создаем объект услуги с обновленными данными
        service = Service(
            id=service_id,
            name=service_data['name'],
            description=service_data['description'],
            base_num_clients=service_data.get('base_clients', service_data['max_clients']),
            max_num_clients=service_data['max_clients'],
            plus_service_ids=','.join(map(str, service_data.get('extra_services', []))),
            price_min=service_data['price_weekday'],
            price_min_weekend=service_data['price_weekend'],
            fix_price=service_data.get('price_group', 0),
            price_for_extra_client=service_data.get('price_extra_weekday', 0),
            price_for_extra_client_weekend=service_data.get('price_extra_weekend', 0),
            min_duration_minutes=service_data['min_duration'],
            duration_step_minutes=service_data['step_duration'],
            photo_ids=None,
            is_active=True
        )
        
        # Обновляем в базе данных
        success = await service_repo.update(service)
        
        if success:
            # Очищаем состояние
            await state.clear()
            
            # Показываем результат
            await callback.message.edit_text(
                f"✅ <b>Услуга успешно обновлена!</b>\n\n"
                f"📸 <b>Название:</b> {service.name}\n"
                f"📝 <b>Описание:</b> {service.description}\n"
                f"💰 <b>Цены:</b> {service.price_min}₽ - {service.price_min_weekend}₽\n"
                f"👥 <b>Макс. человек:</b> {service.max_num_clients}\n"
                f"⏰ <b>Длительность:</b> {service.min_duration_minutes} мин. (шаг {service.duration_step_minutes})\n"
                f"🔧 <b>Доп. услуги:</b> {len(service_data.get('extra_services', []))} услуг\n"
                f"📸 <b>Фото:</b> {service_data.get('photos_count', 0)} шт.\n\n"
                f"🆔 <b>ID услуги:</b> {service_id}",
                reply_markup=get_services_management_keyboard(),
                parse_mode="HTML"
            )
        else:
            await callback.answer("❌ Ошибка при обновлении услуги", show_alert=True)
        
    except Exception as e:
        await callback.answer(f"❌ Ошибка при обновлении услуги: {e}", show_alert=True)

def register_edit_service_new_handlers(dp: Dispatcher):
    """Регистрация обработчиков для нового редактирования услуг"""
    
    # Основные обработчики
    dp.callback_query.register(start_edit_service_new, F.data.startswith("edit_service_new_"))
    dp.callback_query.register(show_edit_service_main, F.data == "show_edit_service_main")
    
    # Обработчики параметров
    dp.callback_query.register(edit_service_name_callback, F.data == "edit_service_name")
    dp.callback_query.register(edit_service_description_callback, F.data == "edit_service_description")
    dp.callback_query.register(edit_service_price_menu_callback, F.data == "edit_service_price")
    dp.callback_query.register(edit_service_max_clients_callback, F.data == "edit_service_max_clients")
    dp.callback_query.register(edit_service_extras_callback, F.data == "edit_service_extras")
    dp.callback_query.register(edit_service_duration_callback, F.data == "edit_service_duration")
    dp.callback_query.register(edit_service_photos_callback, F.data == "edit_service_photos")
    
    # Меню цен
    dp.callback_query.register(edit_service_price_weekday_callback, F.data == "edit_service_price_weekday")
    dp.callback_query.register(edit_service_price_weekend_callback, F.data == "edit_service_price_weekend")
    dp.callback_query.register(edit_service_price_extra_weekday_callback, F.data == "edit_service_price_extra_weekday")
    dp.callback_query.register(edit_service_price_extra_weekend_callback, F.data == "edit_service_price_extra_weekend")
    dp.callback_query.register(edit_service_price_group_callback, F.data == "edit_service_price_group")
    
    # Дополнительные услуги
    dp.callback_query.register(select_edit_extra_service_callback, F.data.startswith("select_edit_extra_service_"))
    dp.callback_query.register(edit_extras_done_callback, F.data == "edit_extras_done")
    
    # Сохранение
    dp.callback_query.register(save_edit_service_callback, F.data == "save_edit_service")
    
    # Обработка текстовых сообщений
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
