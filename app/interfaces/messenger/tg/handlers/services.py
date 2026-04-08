import logging

from aiogram import Dispatcher, F
from aiogram.types import CallbackQuery
from aiogram.fsm.context import FSMContext

from app.interfaces.messenger.tg.keyboards import (
    get_back_to_service_keyboard,
    get_service_details_keyboard,
)
from app.core.modules.services.details import build_service_details_text
from app.integrations.local.db import service_repo
from app.interfaces.messenger.tg.services.service_media import (
    send_service_cover,
    send_service_gallery,
)
from app.interfaces.messenger.tg.utils.photos import list_service_photos


logger = logging.getLogger(__name__)


async def show_service_details(callback: CallbackQuery, state: FSMContext):
    """Показ деталей услуги."""
    service_id = int(callback.data.split("_")[1])
    service = await service_repo.get_by_id(service_id)

    if not service:
        await callback.answer("Услуга не найдена", show_alert=True)
        return

    description = build_service_details_text(service, html=True)
    photo_files = list_service_photos(service_id)
    if photo_files:
        try:
            await callback.message.delete()
        except Exception:
            logger.warning(
                "Не удалось удалить сообщение перед отправкой карточки услуги %s",
                service_id,
                exc_info=True,
            )

        await send_service_cover(
            callback.message,
            service,
            caption=description.strip(),
            reply_markup=get_service_details_keyboard(service_id),
        )
        return

    await callback.message.edit_text(
        description,
        reply_markup=get_service_details_keyboard(service_id),
        parse_mode="HTML",
    )


async def show_photos(callback: CallbackQuery):
    """Показ фотографий услуги."""
    service_id = int(callback.data.split("_")[1])
    service = await service_repo.get_by_id(service_id)

    if not service:
        await callback.answer("Услуга не найдена", show_alert=True)
        return

    photo_files = list_service_photos(service_id)
    if not photo_files:
        await callback.answer("Фотографии для этой услуги пока не добавлены", show_alert=True)
        return

    photo_files = photo_files[1:]
    if not photo_files:
        await callback.answer("Других фотографий нет", show_alert=True)
        return

    caption = f"📸 <b>{service.name}</b>\n\n{service.description}"
    try:
        sent_messages = await send_service_gallery(
            callback.message,
            service,
            caption=caption,
        )
    except Exception:
        logger.exception("Не удалось отправить фотографии услуги %s", service_id)
        await callback.answer("Не удалось отправить фотографии", show_alert=True)
        return

    message_ids_str = ",".join(str(msg.message_id) for msg in sent_messages)
    await callback.message.answer(
        "📸 <b>Фотографии услуги</b>",
        reply_markup=get_back_to_service_keyboard(service_id, message_ids_str),
        parse_mode="HTML",
    )
    await callback.answer("Фотографии отправлены!")


async def back_to_service_from_photos(callback: CallbackQuery):
    """Возврат к услуге и удаление постов с фотографиями."""
    parts = callback.data.split("_", 3)
    if len(parts) < 4:
        await callback.answer("Ошибка в данных", show_alert=True)
        return

    service_and_messages = parts[3].split("_", 1)
    service_id = int(service_and_messages[0])
    message_ids_str = service_and_messages[1] if len(service_and_messages) > 1 else ""

    try:
        await callback.message.delete()
    except Exception:
        logger.warning(
            "Не удалось удалить сообщение с кнопкой возврата к услуге %s",
            service_id,
            exc_info=True,
        )

    if message_ids_str:
        message_ids = message_ids_str.split(",")
        for msg_id in message_ids:
            try:
                await callback.bot.delete_message(
                    chat_id=callback.message.chat.id,
                    message_id=int(msg_id),
                )
            except Exception:
                logger.warning(
                    "Не удалось удалить сообщение %s при возврате к услуге %s",
                    msg_id,
                    service_id,
                    exc_info=True,
                )

    await callback.answer("Возврат к услуге")


def register_services_handlers(dp: Dispatcher):
    """Регистрация обработчиков услуг."""
    dp.callback_query.register(show_service_details, F.data.startswith("service_"))
    dp.callback_query.register(show_photos, F.data.startswith("photos_"))
    dp.callback_query.register(back_to_service_from_photos, F.data.startswith("back_to_service_"))
