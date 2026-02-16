from aiogram import Dispatcher, F
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext

from telegram_bot.keyboards import (
    get_services_management_keyboard, get_service_edit_keyboard, 
    get_services_list_keyboard, get_admin_keyboard
)
from telegram_bot.states import AdminStates
from database import service_repo
from database.models import Service

async def show_services_management(callback: CallbackQuery, is_admin: bool):
    """Показ управления услугами"""
    if not is_admin:
        await callback.answer("У вас нет прав администратора", show_alert=True)
        return
    
    services = await service_repo.get_all_active()
    
    services_text = "📸 <b>Управление услугами</b>\n\n"
    for service in services:
        services_text += f"📸 <b>{service.name}</b>\n"
        services_text += f"💰 {service.price_min}₽ - {service.price_min_weekend}₽\n"
        services_text += f"👥 До {service.max_num_clients} чел.\n"
        services_text += f"⏰ {service.min_duration_minutes} мин.\n"
        services_text += f"📊 Статус: {'✅ Активна' if service.is_active else '❌ Неактивна'}\n\n"
    
    await callback.message.edit_text(
        services_text,
        reply_markup=get_services_management_keyboard(),
        parse_mode="HTML"
    )

async def show_services_list(callback: CallbackQuery, is_admin: bool):
    """Показ списка услуг для редактирования"""
    if not is_admin:
        await callback.answer("У вас нет прав администратора", show_alert=True)
        return
    
    services = await service_repo.get_all_active()
    
    if not services:
        await callback.message.edit_text(
            "📸 <b>Услуги не найдены</b>\n\n"
            "Добавьте первую услугу.",
            reply_markup=get_services_management_keyboard(),
            parse_mode="HTML"
        )
        return
    
    await callback.message.edit_text(
        "📸 <b>Выберите услугу для редактирования:</b>",
        reply_markup=get_services_list_keyboard(services),
        parse_mode="HTML"
    )

async def show_service_edit(callback: CallbackQuery, is_admin: bool):
    """Показ редактирования конкретной услуги"""
    if not is_admin:
        await callback.answer("У вас нет прав администратора", show_alert=True)
        return
    
    # Парсим callback data более безопасно
    try:
        parts = callback.data.split("_")
        if len(parts) < 3:
            await callback.answer("Неверный формат данных", show_alert=True)
            return
        
        service_id = int(parts[2])
    except (ValueError, IndexError):
        await callback.answer("Ошибка в данных", show_alert=True)
        return
    
    service = await service_repo.get_by_id(service_id)
    
    if not service:
        await callback.answer("Услуга не найдена", show_alert=True)
        return
    
    service_text = f"""📸 <b>Редактирование услуги</b>

<b>Название:</b> {service.name}
<b>Описание:</b> {service.description or 'Не указано'}
<b>Цена (будни):</b> {service.price_min}₽
<b>Цена (выходные):</b> {service.price_min_weekend}₽
<b>Макс. клиентов:</b> {service.max_num_clients}
<b>Доп. клиент (будни):</b> {service.price_for_extra_client}₽
<b>Доп. клиент (выходные):</b> {service.price_for_extra_client_weekend}₽
<b>Мин. длительность:</b> {service.min_duration_minutes} мин.
<b>Шаг длительности:</b> {service.duration_step_minutes} мин.
<b>Фиксированная цена:</b> {'Да' if service.fix_price else 'Нет'}
<b>Статус:</b> {'✅ Активна' if service.is_active else '❌ Неактивна'}"""
    
    await callback.message.edit_text(
        service_text,
        reply_markup=get_service_edit_keyboard(service_id),
        parse_mode="HTML"
    )

async def edit_service_name(callback: CallbackQuery, state: FSMContext, is_admin: bool):
    """Начало редактирования названия услуги"""
    if not is_admin:
        await callback.answer("У вас нет прав администратора", show_alert=True)
        return
    
    service_id = int(callback.data.split("_")[3])
    await state.update_data(service_id=service_id, edit_field="name")
    await state.set_state(AdminStates.waiting_for_service_name)
    
    await callback.message.edit_text(
        "✏️ <b>Редактирование названия услуги</b>\n\n"
        "Введите новое название:",
        parse_mode="HTML"
    )

async def edit_service_description(callback: CallbackQuery, state: FSMContext, is_admin: bool):
    """Начало редактирования описания услуги"""
    if not is_admin:
        await callback.answer("У вас нет прав администратора", show_alert=True)
        return
    
    service_id = int(callback.data.split("_")[3])
    await state.update_data(service_id=service_id, edit_field="description")
    await state.set_state(AdminStates.waiting_for_service_description)
    
    await callback.message.edit_text(
        "📝 <b>Редактирование описания услуги</b>\n\n"
        "Введите новое описание:",
        parse_mode="HTML"
    )

async def edit_service_price(callback: CallbackQuery, state: FSMContext, is_admin: bool):
    """Начало редактирования цены услуги"""
    if not is_admin:
        await callback.answer("У вас нет прав администратора", show_alert=True)
        return
    
    try:
        service_id = int(callback.data.split("_")[3])
    except (ValueError, IndexError):
        await callback.answer("Некорректные данные для редактирования цены", show_alert=True)
        return
    await state.update_data(service_id=service_id, edit_field="price")
    await state.set_state(AdminStates.waiting_for_service_price)
    
    await callback.message.edit_text(
        "💰 <b>Редактирование цены услуги</b>\n\n"
        "Введите цены в формате:\n"
        "<b>цена_будни цена_выходные</b>\n\n"
        "Например: <code>5000 6000</code>",
        parse_mode="HTML"
    )

async def edit_service_duration(callback: CallbackQuery, state: FSMContext, is_admin: bool):
    """Начало редактирования длительности услуги"""
    if not is_admin:
        await callback.answer("У вас нет прав администратора", show_alert=True)
        return
    
    service_id = int(callback.data.split("_")[3])
    await state.update_data(service_id=service_id, edit_field="duration")
    await state.set_state(AdminStates.waiting_for_service_duration)
    
    await callback.message.edit_text(
        "⏰ <b>Редактирование длительности услуги</b>\n\n"
        "Введите длительность в формате:\n"
        "<b>мин_длительность шаг_длительности</b>\n\n"
        "Например: <code>60 30</code> (мин. 60, шаг 30)",
        parse_mode="HTML"
    )

async def delete_service(callback: CallbackQuery, is_admin: bool):
    """Удаление услуги"""
    if not is_admin:
        await callback.answer("У вас нет прав администратора", show_alert=True)
        return
    
    service_id = int(callback.data.split("_")[2])
    service = await service_repo.get_by_id(service_id)
    
    if not service:
        await callback.answer("Услуга не найдена", show_alert=True)
        return
    
    # Деактивируем услугу вместо удаления
    service.is_active = False
    await service_repo.update(service)
    
    await callback.answer(f"✅ Услуга '{service.name}' деактивирована", show_alert=True)
    await show_services_management(callback, is_admin)

async def process_service_name(message: Message, state: FSMContext, is_admin: bool):
    """Обработка нового названия услуги"""
    if not is_admin:
        await message.answer("У вас нет прав администратора")
        return
    
    data = await state.get_data()
    
    # Проверяем, это новая услуга или редактирование
    if data.get("edit_field") == "new_service":
        # Это новая услуга - переходим к следующему шагу
        await state.update_data(service_name=message.text.strip())
        await state.set_state(AdminStates.waiting_for_service_description)
        
        await message.answer(
            "📝 <b>Описание услуги</b>\n\n"
            "Введите описание услуги:",
            parse_mode="HTML"
        )
        return
    
    # Это редактирование существующей услуги
    service_id = data.get("service_id")
    if not service_id:
        await message.answer("Ошибка: ID услуги не найден")
        await state.clear()
        return
    
    service = await service_repo.get_by_id(service_id)
    if not service:
        await message.answer("Услуга не найдена")
        await state.clear()
        return
    
    # Обновляем название
    service.name = message.text.strip()
    await service_repo.update(service)
    
    # Показываем обновленную информацию с кнопкой "Назад"
    service_text = f"""📸 <b>Редактирование услуги</b>

<b>Название:</b> {service.name}
<b>Описание:</b> {service.description or 'Не указано'}
<b>Цена (будни):</b> {service.price_min}₽
<b>Цена (выходные):</b> {service.price_min_weekend}₽
<b>Мин. длительность:</b> {service.min_duration_minutes} мин
<b>Шаг длительности:</b> {service.duration_step_minutes} мин
<b>Макс. клиентов:</b> {service.max_num_clients}
<b>Статус:</b> {'Активна' if service.is_active else 'Неактивна'}

Выберите что редактировать:"""
    
    await message.answer(
        service_text,
        reply_markup=get_service_edit_keyboard(service_id),
        parse_mode="HTML"
    )
    await state.clear()

async def process_service_description(message: Message, state: FSMContext, is_admin: bool):
    """Обработка нового описания услуги"""
    if not is_admin:
        await message.answer("У вас нет прав администратора")
        return
    
    data = await state.get_data()
    
    # Проверяем, это новая услуга или редактирование
    if data.get("edit_field") == "new_service":
        # Это новая услуга - переходим к следующему шагу
        await state.update_data(service_description=message.text.strip())
        await state.set_state(AdminStates.waiting_for_service_price)
        
        await message.answer(
            "💰 <b>Цены услуги</b>\n\n"
            "Введите цены в формате:\n"
            "<b>цена_будни цена_выходные</b>\n\n"
            "Например: <code>5000 6000</code>",
            parse_mode="HTML"
        )
        return
    
    # Это редактирование существующей услуги
    service_id = data.get("service_id")
    if not service_id:
        await message.answer("Ошибка: ID услуги не найден")
        await state.clear()
        return
    
    service = await service_repo.get_by_id(service_id)
    if not service:
        await message.answer("Услуга не найдена")
        await state.clear()
        return
    
    # Обновляем описание
    service.description = message.text.strip()
    await service_repo.update(service)
    
    # Показываем обновленную информацию с кнопкой "Назад"
    service_text = f"""📸 <b>Редактирование услуги</b>

<b>Название:</b> {service.name}
<b>Описание:</b> {service.description or 'Не указано'}
<b>Цена (будни):</b> {service.price_min}₽
<b>Цена (выходные):</b> {service.price_min_weekend}₽
<b>Мин. длительность:</b> {service.min_duration_minutes} мин
<b>Шаг длительности:</b> {service.duration_step_minutes} мин
<b>Макс. клиентов:</b> {service.max_num_clients}
<b>Статус:</b> {'Активна' if service.is_active else 'Неактивна'}

Выберите что редактировать:"""
    
    await message.answer(
        service_text,
        reply_markup=get_service_edit_keyboard(service_id),
        parse_mode="HTML"
    )
    await state.clear()

async def process_service_price(message: Message, state: FSMContext, is_admin: bool):
    """Обработка новых цен услуги"""
    if not is_admin:
        await message.answer("У вас нет прав администратора")
        return
    
    try:
        prices = message.text.strip().split()
        if len(prices) != 2:
            raise ValueError("Неверный формат")
        
        price_min = float(prices[0])
        price_weekend = float(prices[1])
        
        if price_min <= 0 or price_weekend <= 0:
            raise ValueError("Цены должны быть положительными")
        
    except ValueError as e:
        await message.answer(f"❌ Ошибка в формате цен: {e}\n\nПопробуйте снова в формате: <code>5000 6000</code>", parse_mode="HTML")
        return
    
    data = await state.get_data()
    
    # Проверяем, это новая услуга или редактирование
    if data.get("edit_field") == "new_service":
        # Это новая услуга - переходим к следующему шагу
        await state.update_data(service_price_min=price_min, service_price_weekend=price_weekend)
        await state.set_state(AdminStates.waiting_for_service_duration)
        
        await message.answer(
            "⏰ <b>Длительность услуги</b>\n\n"
            "Введите длительность в формате:\n"
            "<b>мин_длительность шаг_длительности</b>\n\n"
            "Например: <code>60 30</code> (мин. 60, шаг 30)",
            parse_mode="HTML"
        )
        return
    
    # Это редактирование существующей услуги
    service_id = data.get("service_id")
    if not service_id:
        await message.answer("Ошибка: ID услуги не найден")
        await state.clear()
        return
    
    service = await service_repo.get_by_id(service_id)
    if not service:
        await message.answer("Услуга не найдена")
        await state.clear()
        return
    
    # Обновляем цены
    service.price_min = price_min
    service.price_min_weekend = price_weekend
    await service_repo.update(service)
    
    # Показываем обновленную информацию с кнопкой "Назад"
    service_text = f"""📸 <b>Редактирование услуги</b>

<b>Название:</b> {service.name}
<b>Описание:</b> {service.description or 'Не указано'}
<b>Цена (будни):</b> {service.price_min}₽
<b>Цена (выходные):</b> {service.price_min_weekend}₽
<b>Мин. длительность:</b> {service.min_duration_minutes} мин
<b>Шаг длительности:</b> {service.duration_step_minutes} мин
<b>Макс. клиентов:</b> {service.max_num_clients}
<b>Статус:</b> {'Активна' if service.is_active else 'Неактивна'}

Выберите что редактировать:"""
    
    await message.answer(
        service_text,
        reply_markup=get_service_edit_keyboard(service_id),
        parse_mode="HTML"
    )
    await state.clear()

async def process_service_duration(message: Message, state: FSMContext, is_admin: bool):
    """Обработка новой длительности услуги"""
    if not is_admin:
        await message.answer("У вас нет прав администратора")
        return
    
    data = await state.get_data()
    
    try:
        durations = message.text.strip().split()
        if len(durations) != 2:
            raise ValueError("Неверный формат")
        
        min_duration = int(durations[0])
        step_duration = int(durations[1])
        
        if min_duration <= 0 or step_duration <= 0:
            raise ValueError("Длительность должна быть положительной")
        
    except ValueError as e:
        await message.answer(f"❌ Ошибка в формате длительности: {e}\n\nПопробуйте снова в формате: <code>60 30</code>", parse_mode="HTML")
        return
    
    # Проверяем, это новая услуга или редактирование
    if data.get("edit_field") == "new_service":
        # Это новая услуга - создаем её
        service = Service(
            name=data.get("service_name"),
            description=data.get("service_description"),
            base_num_clients=4,  # По умолчанию
            max_num_clients=4,  # По умолчанию
            price_min=data.get("service_price_min"),
            price_min_weekend=data.get("service_price_weekend"),
            fix_price=False,  # По умолчанию
            price_for_extra_client=1000.0,  # По умолчанию
            price_for_extra_client_weekend=1500.0,  # По умолчанию
            min_duration_minutes=min_duration,
            duration_step_minutes=step_duration,
            is_active=True
        )
        
        try:
            service_id = await service_repo.create(service)
            await message.answer(
                f"✅ <b>Услуга создана!</b>\n\n"
                f"📸 <b>Название:</b> {service.name}\n"
                f"📝 <b>Описание:</b> {service.description}\n"
                f"💰 <b>Цены:</b> {service.price_min}₽ - {service.price_min_weekend}₽\n"
                f"⏰ <b>Длительность:</b> {service.min_duration_minutes} мин. (шаг {service.duration_step_minutes})\n\n"
                f"ID услуги: {service_id}",
                reply_markup=get_services_management_keyboard(),
                parse_mode="HTML"
            )
        except Exception as e:
            await message.answer(f"❌ Ошибка при создании услуги: {e}")
        
        await state.clear()
        return
    
    # Это редактирование существующей услуги
    service_id = data.get("service_id")
    if not service_id:
        await message.answer("Ошибка: ID услуги не найден")
        await state.clear()
        return
    
    service = await service_repo.get_by_id(service_id)
    if not service:
        await message.answer("Услуга не найдена")
        await state.clear()
        return
    
    # Обновляем длительность
    service.min_duration_minutes = min_duration
    service.duration_step_minutes = step_duration
    await service_repo.update(service)
    
    # Показываем обновленную информацию с кнопкой "Назад"
    service_text = f"""📸 <b>Редактирование услуги</b>

<b>Название:</b> {service.name}
<b>Описание:</b> {service.description or 'Не указано'}
<b>Цена (будни):</b> {service.price_min}₽
<b>Цена (выходные):</b> {service.price_min_weekend}₽
<b>Мин. длительность:</b> {service.min_duration_minutes} мин
<b>Шаг длительности:</b> {service.duration_step_minutes} мин
<b>Макс. клиентов:</b> {service.max_num_clients}
<b>Статус:</b> {'Активна' if service.is_active else 'Неактивна'}

Выберите что редактировать:"""
    
    await message.answer(
        service_text,
        reply_markup=get_service_edit_keyboard(service_id),
        parse_mode="HTML"
    )
    await state.clear()

def register_service_management_handlers(dp: Dispatcher):
    """Регистрация обработчиков управления услугами"""
    # Управление услугами
    dp.callback_query.register(show_services_management, F.data == "admin_services")
    dp.callback_query.register(show_services_list, F.data == "edit_service")
    dp.callback_query.register(show_service_edit, F.data.regexp(r"^edit_service_\d+$"))
    
    # Редактирование полей
    dp.callback_query.register(edit_service_name, F.data.startswith("edit_service_name_"))
    dp.callback_query.register(edit_service_description, F.data.startswith("edit_service_desc_"))
    dp.callback_query.register(edit_service_price, F.data.regexp(r"^edit_service_price_\d+$"))
    dp.callback_query.register(edit_service_duration, F.data.startswith("edit_service_duration_"))
    dp.callback_query.register(delete_service, F.data.startswith("delete_service_"))
    
    # Обработка текстовых сообщений
    dp.message.register(process_service_name, AdminStates.waiting_for_service_name)
    dp.message.register(process_service_description, AdminStates.waiting_for_service_description)
    dp.message.register(process_service_price, AdminStates.waiting_for_service_price)
    dp.message.register(process_service_duration, AdminStates.waiting_for_service_duration)
