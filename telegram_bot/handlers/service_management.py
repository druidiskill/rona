from aiogram import Dispatcher, F
from aiogram.types import CallbackQuery

from db import service_repo
from telegram_bot.keyboards import (
    get_service_edit_keyboard,
    get_services_list_keyboard,
    get_services_management_keyboard,
)


async def show_services_management(callback: CallbackQuery, is_admin: bool):
    """Показ управления услугами."""
    if not is_admin:
        await callback.answer("У вас нет прав администратора", show_alert=True)
        return

    services = await service_repo.get_all()
    services_text = "\U0001f4f8 <b>Управление услугами</b>\n\n"
    for service in services:
        services_text += f"\U0001f4f8 <b>{service.name}</b>\n"
        services_text += f"\U0001f4b0 {service.price_min}\u20bd - {service.price_min_weekend}\u20bd\n"
        services_text += f"\U0001f465 До {service.max_num_clients} чел.\n"
        services_text += f"\u23f0 {service.min_duration_minutes} мин.\n"
        services_text += (
            f"\U0001f4ca Статус: {'\u2705 Активна' if service.is_active else '\u274c Неактивна'}\n\n"
        )

    await callback.message.edit_text(
        services_text,
        reply_markup=get_services_management_keyboard(),
        parse_mode="HTML",
    )


async def show_services_list(callback: CallbackQuery, is_admin: bool):
    """Показ списка услуг для редактирования."""
    if not is_admin:
        await callback.answer("У вас нет прав администратора", show_alert=True)
        return

    services = await service_repo.get_all()
    if not services:
        await callback.message.edit_text(
            "\U0001f4f8 <b>Услуги не найдены</b>\n\nДобавьте первую услугу.",
            reply_markup=get_services_management_keyboard(),
            parse_mode="HTML",
        )
        return

    await callback.message.edit_text(
        "\U0001f4f8 <b>Выберите услугу для редактирования:</b>",
        reply_markup=get_services_list_keyboard(services),
        parse_mode="HTML",
    )


async def show_service_edit(callback: CallbackQuery, is_admin: bool):
    """Показ карточки услуги перед редактированием."""
    if not is_admin:
        await callback.answer("У вас нет прав администратора", show_alert=True)
        return

    try:
        service_id = int(callback.data.split("_")[2])
    except (ValueError, IndexError):
        await callback.answer("Ошибка в данных", show_alert=True)
        return

    service = await service_repo.get_by_id(service_id)
    if not service:
        await callback.answer("Услуга не найдена", show_alert=True)
        return

    service_text = f"""\U0001f4f8 <b>Редактирование услуги</b>

<b>Название:</b> {service.name}
<b>Описание:</b> {service.description or 'Не указано'}
<b>Цена (будни):</b> {service.price_min}\u20bd
<b>Цена (выходные):</b> {service.price_min_weekend}\u20bd
<b>Макс. клиентов:</b> {service.max_num_clients}
<b>Доп. клиент (будни):</b> {service.price_for_extra_client}\u20bd
<b>Доп. клиент (выходные):</b> {service.price_for_extra_client_weekend}\u20bd
<b>Мин. длительность:</b> {service.min_duration_minutes} мин.
<b>Шаг длительности:</b> {service.duration_step_minutes} мин.
<b>Фиксированная цена:</b> {'Да' if service.fix_price else 'Нет'}
<b>Статус:</b> {'\u2705 Активна' if service.is_active else '\u274c Неактивна'}"""

    await callback.message.edit_text(
        service_text,
        reply_markup=get_service_edit_keyboard(service_id, service.is_active),
        parse_mode="HTML",
    )


async def delete_service(callback: CallbackQuery, is_admin: bool):
    """Деактивация услуги."""
    if not is_admin:
        await callback.answer("У вас нет прав администратора", show_alert=True)
        return

    service_id = int(callback.data.split("_")[2])
    service = await service_repo.get_by_id(service_id)
    if not service:
        await callback.answer("Услуга не найдена", show_alert=True)
        return

    service.is_active = False
    await service_repo.update(service)
    await callback.answer(f"\u2705 Услуга '{service.name}' деактивирована", show_alert=True)
    await show_services_management(callback, is_admin)


async def activate_service(callback: CallbackQuery, is_admin: bool):
    """Активация услуги."""
    if not is_admin:
        await callback.answer("У вас нет прав администратора", show_alert=True)
        return

    service_id = int(callback.data.split("_")[2])
    service = await service_repo.get_by_id(service_id)
    if not service:
        await callback.answer("Услуга не найдена", show_alert=True)
        return

    service.is_active = True
    await service_repo.update(service)
    await callback.answer(f"\u2705 Услуга '{service.name}' активирована", show_alert=True)
    await show_services_management(callback, is_admin)


def register_service_management_handlers(dp: Dispatcher):
    """Регистрация обработчиков управления услугами."""
    dp.callback_query.register(show_services_management, F.data == "admin_services")
    dp.callback_query.register(show_services_list, F.data == "edit_service")
    dp.callback_query.register(show_service_edit, F.data.regexp(r"^edit_service_\d+$"))
    dp.callback_query.register(delete_service, F.data.startswith("delete_service_"))
    dp.callback_query.register(activate_service, F.data.startswith("activate_service_"))
