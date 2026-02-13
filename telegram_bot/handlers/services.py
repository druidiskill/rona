from aiogram import Dispatcher, F
from aiogram.types import CallbackQuery, FSInputFile
from aiogram.fsm.context import FSMContext

from telegram_bot.keyboards import get_service_details_keyboard, get_back_to_service_keyboard
from database import service_repo
from telegram_bot.utils.photos import list_service_photos

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
"""

    if service.id != 9:
        description += f"""

👥 <b>Количество людей:</b>
• До {service.max_num_clients} чел. - базовая цена
• Дополнительно: {service.price_for_extra_client}₽/чел.
"""

    description += f"""

⏰ <b>Длительность:</b>
• Минимум: {service.min_duration_minutes} мин.
• Бронирование только полными часами.

📅 <b>Дополнительные услуги:</b>
• Фотограф: 11 500₽ (включает аренду зала, работу фотографа и обработанные фото)
• Гримерка: 200/250₽/час
• Розжиг камина: 400₽
• Прокат (белый махровый халат и полотенце): 200₽

<i>Важно: до 9:00 и после 21:00 действует двойная аренда зала и гримерной.</i>
    """
    
    photo_files = list_service_photos(service_id)
    if photo_files:
        await callback.message.delete()
        await callback.message.answer_photo(
            photo=FSInputFile(photo_files[0]),
            caption=description.strip(),
            parse_mode="HTML",
            reply_markup=get_service_details_keyboard(service_id)
        )
    else:
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
    
    photo_files = list_service_photos(service_id)
    if not photo_files:
        await callback.answer("Фотографии для этой услуги пока не добавлены", show_alert=True)
        return

    # Первая фотография уже показана в деталях услуги
    photo_files = photo_files[1:]
    if not photo_files:
        await callback.answer("Других фотографий нет", show_alert=True)
        return
    
    caption = f"📸 <b>{service.name}</b>\n\n{service.description}"

    # Если только одно фото — отправляем как обычную фотографию
    if len(photo_files) == 1:
        try:
            from aiogram.types import FSInputFile
            sent = await callback.message.answer_photo(
                photo=FSInputFile(photo_files[0]),
                caption=caption,
                parse_mode="HTML"
            )
            message_ids_str = str(sent.message_id)
        except Exception:
            await callback.answer("Не удалось отправить фотографию", show_alert=True)
            return
    else:
        # Медиа-группа требует минимум 2 элемента
        from aiogram.types import InputMediaPhoto, FSInputFile
        media_group = [InputMediaPhoto(
            media=FSInputFile(photo_files[0]),
            caption=caption,
            parse_mode="HTML"
        )]
        for photo_path in photo_files[1:]:
            media_group.append(InputMediaPhoto(media=FSInputFile(photo_path)))

        try:
            sent_messages = await callback.message.answer_media_group(media=media_group)
            message_ids_str = ",".join(str(msg.message_id) for msg in sent_messages)
        except Exception:
            await callback.answer("Не удалось отправить фотографии", show_alert=True)
            return

    # Отправляем кнопку "Назад" отдельным сообщением
    await callback.message.answer(
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



