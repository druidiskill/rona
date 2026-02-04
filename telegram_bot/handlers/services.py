from aiogram import Dispatcher, F
from aiogram.types import CallbackQuery
from aiogram.fsm.context import FSMContext

from telegram_bot.keyboards import get_service_details_keyboard, get_back_to_service_keyboard
from database import service_repo

async def show_service_details(callback: CallbackQuery, state: FSMContext):
    """Показ деталей услуги"""
    service_id = int(callback.data.split("_")[1])
    service = await service_repo.get_by_id(service_id)
    
    if not service:
        await callback.answer("Услуга не найдена", show_alert=True)
        return
    
    # Формируем описание услуги
    description = f"""
📸 <b>{service.name}</b>

{service.description}

💰 <b>Цены:</b>
• Будни: {service.price_min}₽
• Выходные: {service.price_min_weekend}₽

👥 <b>Количество людей:</b>
• До {service.max_num_clients} чел. - базовая цена
• Дополнительно: {service.price_for_extra_client}₽/чел.

⏰ <b>Длительность:</b>
• Минимум: {service.min_duration_minutes} мин.
• Шаг: {service.duration_step_minutes} мин.

📅 <b>Дополнительные услуги:</b>
• Фотограф: +2000₽
• Гримерка: 1000₽/час
    """
    
    await callback.message.edit_text(
        description,
        reply_markup=get_service_details_keyboard(service_id),
        parse_mode="HTML"
    )

# Функция start_booking перенесена в booking.py для единой логики бронирования
# Удалено во избежание дублирования обработчиков

async def show_photos(callback: CallbackQuery):
    """Показ фотографий услуги"""
    service_id = int(callback.data.split("_")[1])
    service = await service_repo.get_by_id(service_id)
    
    if not service:
        await callback.answer("Услуга не найдена", show_alert=True)
        return
    
    if not service.photo_ids:
        await callback.answer("Фотографии для этой услуги пока не добавлены", show_alert=True)
        return
    
    # Получаем список file_id фотографий
    photo_ids = [photo_id.strip() for photo_id in service.photo_ids.split(',') if photo_id.strip()]
    
    if not photo_ids:
        await callback.answer("Фотографии для этой услуги пока не добавлены", show_alert=True)
        return
    
    # Подготавливаем медиа-группу
    from aiogram.types import InputMediaPhoto
    
    # Создаем список медиа-объектов
    media_group = []
    
    # Первая фотография с подписью
    caption = f"📸 <b>{service.name}</b>\n\n{service.description}"
    media_group.append(InputMediaPhoto(
        media=photo_ids[0],
        caption=caption,
        parse_mode="HTML"
    ))
    
    # Остальные фотографии без подписи
    for photo_id in photo_ids[1:]:
        media_group.append(InputMediaPhoto(media=photo_id))
    
    # Отправляем медиа-группу
    sent_messages = await callback.message.answer_media_group(media=media_group)
    
    # Собираем ID всех сообщений медиа-группы
    media_message_ids = [str(msg.message_id) for msg in sent_messages]
    message_ids_str = ",".join(media_message_ids)
    
    # Отправляем кнопку "Назад" отдельным сообщением
    control_message = await callback.message.answer(
        "📸 <b>Фотографии услуги</b>",
        reply_markup=get_back_to_service_keyboard(service_id, message_ids_str),
        parse_mode="HTML"
    )
    
    await callback.answer("Фотографии отправлены!")

async def back_to_service_from_photos(callback: CallbackQuery):
    """Возврат к услуге и удаление постов с фотографиями"""
    # Извлекаем данные из callback_data "back_to_service_123_456,789"
    # Формат: back_to_service_{service_id}_{message_ids}
    parts = callback.data.split("_", 3)  # Разделяем максимум на 3 части
    if len(parts) < 4:
        await callback.answer("Ошибка в данных", show_alert=True)
        return
    
    # parts[0] = "back", parts[1] = "to", parts[2] = "service", parts[3] = "123_456,789"
    # Нужно извлечь service_id из parts[3]
    service_and_messages = parts[3].split("_", 1)  # Разделяем "123_456,789" на "123" и "456,789"
    service_id = int(service_and_messages[0])
    message_ids_str = service_and_messages[1] if len(service_and_messages) > 1 else ""
    
    # Удаляем текущее сообщение с кнопкой
    await callback.message.delete()
    
    # Удаляем все сообщения медиа-группы
    if message_ids_str:
        message_ids = message_ids_str.split(",")
        for msg_id in message_ids:
            try:
                await callback.bot.delete_message(
                    chat_id=callback.message.chat.id,
                    message_id=int(msg_id)
                )
            except Exception as e:
                print(f"Ошибка удаления сообщения {msg_id}: {e}")
    
    # Просто подтверждаем действие
    await callback.answer("Возврат к услуге")

def register_services_handlers(dp: Dispatcher):
    """Регистрация обработчиков услуг"""
    dp.callback_query.register(show_service_details, F.data.startswith("service_"))
    # start_booking теперь в booking.py - убрано отсюда чтобы избежать дублирования
    # dp.callback_query.register(start_booking, F.data.startswith("book_service_"))
    dp.callback_query.register(show_photos, F.data.startswith("photos_"))
    dp.callback_query.register(back_to_service_from_photos, F.data.startswith("back_to_service_"))
