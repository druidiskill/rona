from aiogram import Dispatcher, F
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext

from telegram_bot.keyboards import (
    get_add_service_main_keyboard, get_add_service_price_keyboard, 
    get_add_service_extras_keyboard, get_services_management_keyboard,
    get_existing_services_keyboard
)
from telegram_bot.states import AdminStates
from database import service_repo
from database.models import Service
from telegram_bot.utils.photos import (
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
        await callback.answer("У вас нет прав администратора", show_alert=True)
        return
    
    # Очищаем предыдущие данные
    await state.clear()
    # Очищаем временные фото для текущего администратора
    temp_dir = get_temp_dir(callback.from_user.id)
    clear_dir(temp_dir)
    
    await callback.message.edit_text(
        "📸 <b>Добавление новой услуги</b>\n\n"
        "Выберите параметр для настройки:",
        reply_markup=get_add_service_main_keyboard(),
        parse_mode="HTML"
    )

async def show_add_service_main(callback: CallbackQuery, state: FSMContext, is_admin: bool):
    """Показ главного меню добавления услуги с текущими данными"""
    if not is_admin:
        await callback.answer("У вас нет прав администратора", show_alert=True)
        return
    
    # Получаем данные из состояния
    data = await state.get_data()
    service_data = data.get("new_service_data", {})
    
    # Формируем текст с текущими данными
    text = "📸 <b>Добавление новой услуги</b>\n\n"
    text += f"📝 <b>Название:</b> {service_data.get('name', 'Не указано')}\n"
    text += f"📄 <b>Описание:</b> {service_data.get('description', 'Не указано')}\n"
    text += f"💰 <b>Цена (будни):</b> {service_data.get('price_weekday', 'Не указано')}₽\n"
    text += f"💰 <b>Цена (выходные):</b> {service_data.get('price_weekend', 'Не указано')}₽\n"
    text += f"👤 <b>Цена за доп. человека (будни):</b> {service_data.get('price_extra_weekday', 'Не указано')}₽\n"
    text += f"👤 <b>Цена за доп. человека (выходные):</b> {service_data.get('price_extra_weekend', 'Не указано')}₽\n"
    text += f"👥 <b>Цена от 10 человек:</b> {service_data.get('price_group', 'Не указано')}₽\n"
    text += f"👥 <b>Макс. человек:</b> {service_data.get('max_clients', 'Не указано')}\n"
    text += f"🔧 <b>Доп. услуги:</b> {service_data.get('extras', 'Не указано')}\n"
    text += f"⏰ <b>Длительность:</b> {service_data.get('duration', 'Не указано')}\n"
    photos_count = service_data.get('photos_count', 0)
    text += f"📸 <b>Фото:</b> {photos_count} шт.\n\n"
    text += "Выберите параметр для настройки:"
    
    await callback.message.edit_text(
        text,
        reply_markup=get_add_service_main_keyboard(),
        parse_mode="HTML"
    )

async def add_service_name_callback(callback: CallbackQuery, state: FSMContext, is_admin: bool):
    """Обработчик кнопки 'Название'"""
    if not is_admin:
        await callback.answer("У вас нет прав администратора", show_alert=True)
        return
    
    await callback.message.edit_text(
        "📝 <b>Название услуги</b>\n\nВведите название услуги:",
        parse_mode="HTML"
    )
    await state.set_state(AdminStates.waiting_for_new_service_name)

async def add_service_description_callback(callback: CallbackQuery, state: FSMContext, is_admin: bool):
    """Обработчик кнопки 'Описание'"""
    if not is_admin:
        await callback.answer("У вас нет прав администратора", show_alert=True)
        return
    
    await callback.message.edit_text(
        "📄 <b>Описание услуги</b>\n\nВведите описание услуги:",
        parse_mode="HTML"
    )
    await state.set_state(AdminStates.waiting_for_new_service_description)

async def add_service_price_menu_callback(callback: CallbackQuery, state: FSMContext, is_admin: bool):
    """Обработчик кнопки 'Цена' - показ меню цен"""
    if not is_admin:
        await callback.answer("У вас нет прав администратора", show_alert=True)
        return
    
    await callback.message.edit_text(
        "💰 <b>Настройка цен</b>\n\nВыберите тип цены для настройки:",
        reply_markup=get_add_service_price_keyboard(),
        parse_mode="HTML"
    )

async def add_service_price_weekday_callback(callback: CallbackQuery, state: FSMContext, is_admin: bool):
    """Обработчик кнопки 'Цена (будни)'"""
    if not is_admin:
        await callback.answer("У вас нет прав администратора", show_alert=True)
        return
    
    await callback.message.edit_text(
        "💰 <b>Цена в будни</b>\n\nВведите цену в будни (только число):",
        parse_mode="HTML"
    )
    await state.set_state(AdminStates.waiting_for_new_service_price_weekday)

async def add_service_price_weekend_callback(callback: CallbackQuery, state: FSMContext, is_admin: bool):
    """Обработчик кнопки 'Цена (выходные)'"""
    if not is_admin:
        await callback.answer("У вас нет прав администратора", show_alert=True)
        return
    
    await callback.message.edit_text(
        "💰 <b>Цена в выходные</b>\n\nВведите цену в выходные (только число):",
        parse_mode="HTML"
    )
    await state.set_state(AdminStates.waiting_for_new_service_price_weekend)

async def add_service_max_clients_callback(callback: CallbackQuery, state: FSMContext, is_admin: bool):
    """Обработчик кнопки 'Макс. человек'"""
    if not is_admin:
        await callback.answer("У вас нет прав администратора", show_alert=True)
        return
    
    await callback.message.edit_text(
        "👥 <b>Максимальное количество человек</b>\n\nВведите максимальное количество человек:",
        parse_mode="HTML"
    )
    await state.set_state(AdminStates.waiting_for_new_service_max_clients)

async def add_service_extras_callback(callback: CallbackQuery, state: FSMContext, is_admin: bool):
    """Обработчик кнопки 'Доп. услуги'"""
    if not is_admin:
        await callback.answer("У вас нет прав администратора", show_alert=True)
        return
    
    # Получаем список существующих услуг
    services = await service_repo.get_all()
    active_services = [s for s in services if s.is_active]
    
    # Получаем уже выбранные услуги
    data = await state.get_data()
    service_data = data.get("new_service_data", {})
    selected_ids = service_data.get("extra_services", [])
    
    if not active_services:
        await callback.message.edit_text(
            "🔧 <b>Дополнительные услуги</b>\n\n"
            "❌ Нет доступных услуг для выбора.\n"
            "Сначала создайте другие услуги.",
            reply_markup=get_add_service_extras_keyboard(),
            parse_mode="HTML"
        )
        return
    
    await callback.message.edit_text(
        "🔧 <b>Дополнительные услуги</b>\n\n"
        "Выберите услуги, которые можно добавить к этой услуге:",
        reply_markup=get_existing_services_keyboard(active_services, selected_ids),
        parse_mode="HTML"
    )

async def add_service_duration_callback(callback: CallbackQuery, state: FSMContext, is_admin: bool):
    """Обработчик кнопки 'Длительность'"""
    if not is_admin:
        await callback.answer("У вас нет прав администратора", show_alert=True)
        return
    
    await callback.message.edit_text(
        "⏰ <b>Длительность услуги</b>\n\nВведите длительность в формате: мин_длительность шаг_длительности\nНапример: 60 30",
        parse_mode="HTML"
    )
    await state.set_state(AdminStates.waiting_for_new_service_duration)

async def add_service_photos_callback(callback: CallbackQuery, state: FSMContext, is_admin: bool):
    """Обработчик кнопки 'Фото'"""
    if not is_admin:
        await callback.answer("У вас нет прав администратора", show_alert=True)
        return
    
    await callback.message.edit_text(
        "📸 <b>Фотографии услуги</b>\n\nОтправьте фотографии услуги (можно несколько):",
        parse_mode="HTML"
    )
    await state.set_state(AdminStates.waiting_for_new_service_photos)

# Обработчики текстовых сообщений
async def process_new_service_name(message: Message, state: FSMContext, is_admin: bool):
    """Обработка названия новой услуги"""
    if not is_admin:
        await message.answer("У вас нет прав администратора")
        return
    
    # Сохраняем название
    data = await state.get_data()
    if "new_service_data" not in data:
        data["new_service_data"] = {}
    data["new_service_data"]["name"] = message.text.strip()
    await state.update_data(data)
    
    # Возвращаемся к главному меню
    await show_add_service_main_after_edit(message, state, is_admin)

async def process_new_service_description(message: Message, state: FSMContext, is_admin: bool):
    """Обработка описания новой услуги"""
    if not is_admin:
        await message.answer("У вас нет прав администратора")
        return
    
    # Сохраняем описание
    data = await state.get_data()
    if "new_service_data" not in data:
        data["new_service_data"] = {}
    data["new_service_data"]["description"] = message.text.strip()
    await state.update_data(data)
    
    # Возвращаемся к главному меню
    await show_add_service_main_after_edit(message, state, is_admin)

async def process_new_service_price_weekday(message: Message, state: FSMContext, is_admin: bool):
    """Обработка цены в будни"""
    if not is_admin:
        await message.answer("У вас нет прав администратора")
        return
    
    try:
        price = float(message.text.strip())
        if price <= 0:
            raise ValueError("Цена должна быть положительной")
        
        # Сохраняем цену
        data = await state.get_data()
        if "new_service_data" not in data:
            data["new_service_data"] = {}
        data["new_service_data"]["price_weekday"] = price
        await state.update_data(data)
        
        # Возвращаемся к главному меню
        await show_add_service_main_after_edit(message, state, is_admin)
        
    except ValueError:
        await message.answer("❌ Неверный формат цены. Введите только число:")

async def process_new_service_price_weekend(message: Message, state: FSMContext, is_admin: bool):
    """Обработка цены в выходные"""
    if not is_admin:
        await message.answer("У вас нет прав администратора")
        return
    
    try:
        price = float(message.text.strip())
        if price <= 0:
            raise ValueError("Цена должна быть положительной")
        
        # Сохраняем цену
        data = await state.get_data()
        if "new_service_data" not in data:
            data["new_service_data"] = {}
        data["new_service_data"]["price_weekend"] = price
        await state.update_data(data)
        
        # Возвращаемся к главному меню
        await show_add_service_main_after_edit(message, state, is_admin)
        
    except ValueError:
        await message.answer("❌ Неверный формат цены. Введите только число:")

async def process_new_service_max_clients(message: Message, state: FSMContext, is_admin: bool):
    """Обработка максимального количества клиентов"""
    if not is_admin:
        await message.answer("У вас нет прав администратора")
        return
    
    try:
        max_clients = int(message.text.strip())
        if max_clients <= 0:
            raise ValueError("Количество должно быть положительным")
        
        # Сохраняем количество
        data = await state.get_data()
        if "new_service_data" not in data:
            data["new_service_data"] = {}
        data["new_service_data"]["max_clients"] = max_clients
        await state.update_data(data)
        
        # Возвращаемся к главному меню
        await show_add_service_main_after_edit(message, state, is_admin)
        
    except ValueError:
        await message.answer("❌ Неверный формат. Введите только число:")

async def process_new_service_duration(message: Message, state: FSMContext, is_admin: bool):
    """Обработка длительности услуги"""
    if not is_admin:
        await message.answer("У вас нет прав администратора")
        return
    
    try:
        durations = message.text.strip().split()
        if len(durations) != 2:
            raise ValueError("Неверный формат")
        
        min_duration = int(durations[0])
        step_duration = int(durations[1])
        
        if min_duration <= 0 or step_duration <= 0:
            raise ValueError("Значения должны быть положительными")
        
        # Сохраняем длительность
        data = await state.get_data()
        if "new_service_data" not in data:
            data["new_service_data"] = {}
        data["new_service_data"]["duration"] = f"{min_duration} мин (шаг {step_duration})"
        data["new_service_data"]["min_duration"] = min_duration
        data["new_service_data"]["step_duration"] = step_duration
        await state.update_data(data)
        
        # Возвращаемся к главному меню
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

    data = await state.get_data()
    if "new_service_data" not in data:
        data["new_service_data"] = {}

    temp_dir = get_temp_dir(message.from_user.id)
    try:
        await save_message_photo(message, temp_dir)
    except Exception:
        await message.answer("❌ Не удалось сохранить фотографию")
        return

    photos_count = count_photos_in_dir(temp_dir)
    data["new_service_data"]["photos_count"] = photos_count
    data["new_service_data"]["temp_photos_dir"] = str(temp_dir)
    await state.update_data(data)

    await message.answer(f"✅ Фотография добавлена! Всего: {photos_count}")

    # Возвращаемся к главному меню
    await show_add_service_main_after_edit(message, state, is_admin)

async def select_extra_service_callback(callback: CallbackQuery, state: FSMContext, is_admin: bool):
    """Обработчик выбора дополнительной услуги"""
    if not is_admin:
        await callback.answer("У вас нет прав администратора", show_alert=True)
        return
    
    # Извлекаем ID услуги из callback_data
    service_id = int(callback.data.split("_")[-1])
    
    # Получаем текущие данные
    data = await state.get_data()
    service_data = data.get("new_service_data", {})
    selected_ids = service_data.get("extra_services", [])
    
    # Переключаем выбор услуги
    if service_id in selected_ids:
        selected_ids.remove(service_id)
        await callback.answer("❌ Услуга удалена из дополнительных")
    else:
        selected_ids.append(service_id)
        await callback.answer("✅ Услуга добавлена в дополнительные")
    
    # Сохраняем обновленный список
    service_data["extra_services"] = selected_ids
    await state.update_data({"new_service_data": service_data})
    
    # Обновляем клавиатуру
    services = await service_repo.get_all()
    active_services = [s for s in services if s.is_active]
    
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
    
    # Получаем выбранные услуги
    data = await state.get_data()
    service_data = data.get("new_service_data", {})
    selected_ids = service_data.get("extra_services", [])
    
    # Формируем список названий выбранных услуг
    if selected_ids:
        services = await service_repo.get_all()
        selected_services = [s for s in services if s.id in selected_ids]
        service_names = [s.name for s in selected_services]
        service_data["extras"] = ", ".join(service_names)
    else:
        service_data["extras"] = "Не выбрано"
    
    await state.update_data({"new_service_data": service_data})
    
    # Возвращаемся к главному меню
    await show_add_service_main_after_edit_callback(callback, state, is_admin)

async def show_add_service_main_after_edit_callback(callback: CallbackQuery, state: FSMContext, is_admin: bool):
    """Показ главного меню после редактирования параметра (для callback)"""
    # Получаем данные из состояния
    data = await state.get_data()
    service_data = data.get("new_service_data", {})
    
    # Формируем текст с текущими данными
    text = "📸 <b>Добавление новой услуги</b>\n\n"
    text += f"📝 <b>Название:</b> {service_data.get('name', 'Не указано')}\n"
    text += f"📄 <b>Описание:</b> {service_data.get('description', 'Не указано')}\n"
    text += f"💰 <b>Цена (будни):</b> {service_data.get('price_weekday', 'Не указано')}₽\n"
    text += f"💰 <b>Цена (выходные):</b> {service_data.get('price_weekend', 'Не указано')}₽\n"
    text += f"👤 <b>Цена за доп. человека (будни):</b> {service_data.get('price_extra_weekday', 'Не указано')}₽\n"
    text += f"👤 <b>Цена за доп. человека (выходные):</b> {service_data.get('price_extra_weekend', 'Не указано')}₽\n"
    text += f"👥 <b>Цена от 10 человек:</b> {service_data.get('price_group', 'Не указано')}₽\n"
    text += f"👥 <b>Макс. человек:</b> {service_data.get('max_clients', 'Не указано')}\n"
    text += f"🔧 <b>Доп. услуги:</b> {service_data.get('extras', 'Не указано')}\n"
    text += f"⏰ <b>Длительность:</b> {service_data.get('duration', 'Не указано')}\n"
    photos_count = service_data.get('photos_count', 0)
    text += f"📸 <b>Фото:</b> {photos_count} шт.\n\n"
    text += "Выберите параметр для настройки:"
    
    await callback.message.edit_text(
        text,
        reply_markup=get_add_service_main_keyboard(),
        parse_mode="HTML"
    )

async def create_service_final_callback(callback: CallbackQuery, state: FSMContext, is_admin: bool):
    """Обработчик финального создания услуги"""
    if not is_admin:
        await callback.answer("У вас нет прав администратора", show_alert=True)
        return
    
    # Получаем данные из состояния
    data = await state.get_data()
    service_data = data.get("new_service_data", {})
    
    # Проверяем обязательные поля
    required_fields = ['name', 'description', 'price_weekday', 'price_weekend', 'max_clients', 'min_duration']
    missing_fields = [field for field in required_fields if not service_data.get(field)]
    
    if missing_fields:
        missing_names = {
            'name': 'Название',
            'description': 'Описание', 
            'price_weekday': 'Цена (будни)',
            'price_weekend': 'Цена (выходные)',
            'max_clients': 'Макс. человек',
            'min_duration': 'Длительность'
        }
        missing_list = [missing_names[field] for field in missing_fields]
        
        await callback.answer(
            f"❌ Заполните обязательные поля: {', '.join(missing_list)}",
            show_alert=True
        )
        return
    
    try:
        # Создаем объект услуги
        service = Service(
            name=service_data['name'],
            description=service_data['description'],
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
        
        # Сохраняем в базу данных
        service_id = await service_repo.create(service)

        # Перемещаем временные фото в директорию услуги
        temp_dir = service_data.get("temp_photos_dir")
        if temp_dir:
            move_dir_contents(get_temp_dir(callback.from_user.id), get_service_dir(service_id))
        
        # Очищаем состояние
        await state.clear()
        
        # Показываем результат
        await callback.message.edit_text(
            f"✅ <b>Услуга успешно создана!</b>\n\n"
            f"📸 <b>Название:</b> {service.name}\n"
            f"📝 <b>Описание:</b> {service.description}\n"
            f"💰 <b>Цены:</b> {service.price_min}₽ - {service.price_min_weekend}₽\n"
            f"👥 <b>Макс. человек:</b> {service.max_num_clients}\n"
            f"⏰ <b>Длительность:</b> {service.min_duration_minutes} мин. (шаг {service.duration_step_minutes})\n"
            f"🔧 <b>Доп. услуги:</b> {service_data.get('extras', 'Не выбрано')}\n"
            f"📸 <b>Фото:</b> {service_data.get('photos_count', 0)} шт.\n\n"
            f"🆔 <b>ID услуги:</b> {service_id}",
            reply_markup=get_services_management_keyboard(),
            parse_mode="HTML"
        )
        
    except Exception as e:
        await callback.answer(f"❌ Ошибка при создании услуги: {e}", show_alert=True)

async def show_add_service_main_after_edit(message: Message, state: FSMContext, is_admin: bool):
    """Показ главного меню после редактирования параметра"""
    # Получаем данные из состояния
    data = await state.get_data()
    service_data = data.get("new_service_data", {})
    
    # Формируем текст с текущими данными
    text = "📸 <b>Добавление новой услуги</b>\n\n"
    text += f"📝 <b>Название:</b> {service_data.get('name', 'Не указано')}\n"
    text += f"📄 <b>Описание:</b> {service_data.get('description', 'Не указано')}\n"
    text += f"💰 <b>Цена (будни):</b> {service_data.get('price_weekday', 'Не указано')}₽\n"
    text += f"💰 <b>Цена (выходные):</b> {service_data.get('price_weekend', 'Не указано')}₽\n"
    text += f"👤 <b>Цена за доп. человека (будни):</b> {service_data.get('price_extra_weekday', 'Не указано')}₽\n"
    text += f"👤 <b>Цена за доп. человека (выходные):</b> {service_data.get('price_extra_weekend', 'Не указано')}₽\n"
    text += f"👥 <b>Цена от 10 человек:</b> {service_data.get('price_group', 'Не указано')}₽\n"
    text += f"👥 <b>Макс. человек:</b> {service_data.get('max_clients', 'Не указано')}\n"
    text += f"🔧 <b>Доп. услуги:</b> {service_data.get('extras', 'Не указано')}\n"
    text += f"⏰ <b>Длительность:</b> {service_data.get('duration', 'Не указано')}\n"
    photos_count = service_data.get('photos_count', 0)
    text += f"📸 <b>Фото:</b> {photos_count} шт.\n\n"
    text += "Выберите параметр для настройки:"
    
    await message.answer(
        text,
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
    dp.message.register(process_new_service_max_clients, AdminStates.waiting_for_new_service_max_clients)
    dp.message.register(process_new_service_duration, AdminStates.waiting_for_new_service_duration)
    dp.message.register(process_new_service_photos, AdminStates.waiting_for_new_service_photos)
