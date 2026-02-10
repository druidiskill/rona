from aiogram import Dispatcher, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
import html

from telegram_bot.keyboards import (
    get_main_menu_keyboard, get_support_menu_keyboard, get_admin_keyboard, get_services_management_keyboard, 
    get_bookings_management_keyboard, get_contacts_keyboard, get_my_bookings_keyboard,
    get_clients_management_keyboard, get_admins_management_keyboard
)
from telegram_bot.states import SupportStates
from database import admin_repo, support_repo

async def help_callback(callback: CallbackQuery, state: FSMContext):
    """Обработчик кнопки помощи"""
    await state.set_state(SupportStates.user_chat)
    await callback.message.edit_text(
        "🆘 <b>Поддержка</b>\n\n"
        "Опишите ваш вопрос одним сообщением. Мы передадим его администраторам.\n"
        "Чтобы выйти из режима поддержки, нажмите /start.",
        reply_markup=get_support_menu_keyboard(),
        parse_mode="HTML"
    )
    # Сохраняем сообщение поддержки для последующего удаления
    try:
        await support_repo.add_message(
            user_id=callback.from_user.id,
            chat_id=callback.message.chat.id,
            message_id=callback.message.message_id,
            role="bot",
            text="Поддержка",
        )
    except Exception:
        pass


async def support_user_message(message: Message, state: FSMContext):
    """Сообщение пользователя в поддержку"""
    admins = await admin_repo.get_all()
    active_admins = [a for a in admins if a.is_active and a.telegram_id]
    if not active_admins:
        sent = await message.answer(
            "❌ Сейчас нет доступных администраторов. Попробуйте позже.",
            reply_markup=get_support_menu_keyboard(),
            parse_mode="HTML"
        )
        try:
            await support_repo.add_message(
                user_id=message.from_user.id,
                chat_id=message.chat.id,
                message_id=sent.message_id,
                role="bot",
                text="Нет доступных администраторов",
            )
        except Exception:
            pass
        return

    user = message.from_user

    # Сохраняем сообщение пользователя и строим историю из БД
    if message.text:
        history_item = message.text
    elif message.caption:
        history_item = message.caption
    else:
        history_item = f"[{message.content_type}]"

    await support_repo.add_message(
        user_id=user.id,
        chat_id=message.chat.id,
        message_id=message.message_id,
        role="user",
        text=history_item,
    )

    history_rows = await support_repo.get_last_messages(user.id, limit=6)
    history_text = ""
    if history_rows:
        lines = []
        for role, text in history_rows:
            label = "Пользователь" if role == "user" else "Админ"
            lines.append(f"• {label}: {html.escape(text or '')}")
        history_text = "\n\n<b>История (последние 6 сообщений):</b>\n" + "\n".join(lines)
    header = (
        "🆘 <b>Новый запрос поддержки</b>\n\n"
        f"👤 Пользователь: {user.full_name}\n"
        f"🆔 ID: {user.id}\n"
    )
    if user.username:
        header += f"🔗 https://t.me/{user.username}\n"
    header += history_text

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Ответить", callback_data=f"support_reply_{user.id}")]
    ])

    for admin in active_admins:
        try:
            sent = await message.bot.send_message(
                admin.telegram_id,
                header,
                reply_markup=keyboard,
                parse_mode="HTML"
            )
            await support_repo.add_message(
                user_id=user.id,
                chat_id=admin.telegram_id,
                message_id=sent.message_id,
                role="admin_alert",
                text=None,
            )
            copied = await message.bot.copy_message(
                chat_id=admin.telegram_id,
                from_chat_id=message.chat.id,
                message_id=message.message_id
            )
            await support_repo.add_message(
                user_id=user.id,
                chat_id=admin.telegram_id,
                message_id=copied.message_id,
                role="bot",
                text=None,
            )
        except Exception as e:
            print(f"Не удалось отправить сообщение админу {admin.telegram_id}: {e}")

    sent_to_user = await message.answer(
        "✅ Сообщение отправлено администраторам. Мы скоро ответим.",
        reply_markup=get_support_menu_keyboard(),
        parse_mode="HTML"
    )
    await support_repo.add_message(
        user_id=user.id,
        chat_id=message.chat.id,
        message_id=sent_to_user.message_id,
        role="bot",
        text="Сообщение отправлено администраторам",
    )


async def support_end_callback(callback: CallbackQuery, state: FSMContext):
    """Завершение диалога поддержки пользователем"""
    await state.clear()
    user = callback.from_user

    # Удаляем все сообщения поддержки у пользователя и админов
    try:
        msg_ids = await support_repo.get_message_ids(user.id)
        for chat_id, msg_id in msg_ids:
            # Не удаляем текущее сообщение, чтобы обновить его в главное меню
            if chat_id == callback.message.chat.id and msg_id == callback.message.message_id:
                continue
            try:
                await callback.bot.delete_message(chat_id, msg_id)
            except Exception:
                pass
        await support_repo.delete_by_user(user.id)
    except Exception as e:
        print(f"Ошибка удаления сообщений поддержки: {e}")

    # Уведомляем администраторов о завершении диалога
    try:
        admins = await admin_repo.get_all()
        active_admins = [a for a in admins if a.is_active and a.telegram_id]
        if active_admins:
            end_text = (
                "✅ <b>Диалог завершен пользователем</b>\n\n"
                f"👤 Пользователь: {user.full_name}\n"
                f"🆔 ID: {user.id}\n"
            )
            if user.username:
                end_text += f"🔗 https://t.me/{user.username}\n"

            for admin in active_admins:
                try:
                    await callback.bot.send_message(
                        admin.telegram_id,
                        end_text,
                        parse_mode="HTML"
                    )
                except Exception as e:
                    print(f"Не удалось отправить уведомление админу {admin.telegram_id}: {e}")
    except Exception as e:
        print(f"Ошибка уведомления администраторов о завершении диалога: {e}")

    await callback.message.edit_text(
        "🏠 <b>Главное меню</b>\n\nВыберите действие:",
        reply_markup=get_main_menu_keyboard(),
        parse_mode="HTML"
    )


async def support_reply_callback(callback: CallbackQuery, state: FSMContext):
    """Админ нажал Ответить"""
    parts = callback.data.split("_")
    if len(parts) < 3:
        await callback.answer("Ошибка в данных", show_alert=True)
        return
    user_id = int(parts[2])
    await state.set_state(SupportStates.admin_reply)
    await state.update_data(support_reply_user_id=user_id)
    sent = await callback.message.answer(
        "✍️ Напишите ответ пользователю. Чтобы выйти из режима ответа, отправьте /stop.",
        parse_mode="HTML"
    )
    try:
        await support_repo.add_message(
            user_id=user_id,
            chat_id=callback.message.chat.id,
            message_id=sent.message_id,
            role="bot",
            text="Ответ админа: ввод",
        )
    except Exception:
        pass
    await callback.answer()

async def support_reply_username_callback(callback: CallbackQuery, state: FSMContext):
    """Админ нажал Ответить по username."""
    username = callback.data.replace("support_reply_username_", "", 1).strip()
    if not username:
        await callback.answer("Ошибка в данных", show_alert=True)
        return

    try:
        chat = await callback.bot.get_chat(f"@{username}")
        user_id = chat.id
    except Exception as e:
        await callback.answer("Не удалось найти чат пользователя", show_alert=True)
        print(f"Ошибка resolve username @{username}: {e}")
        return

    await state.set_state(SupportStates.admin_reply)
    await state.update_data(support_reply_user_id=user_id)
    sent = await callback.message.answer(
        "✍️ Напишите ответ пользователю. Чтобы выйти из режима ответа, отправьте /stop.",
        parse_mode="HTML"
    )
    try:
        await support_repo.add_message(
            user_id=user_id,
            chat_id=callback.message.chat.id,
            message_id=sent.message_id,
            role="bot",
            text="Ответ админа: ввод",
        )
    except Exception:
        pass
    await callback.answer()


async def support_admin_message(message: Message, state: FSMContext):
    """Сообщение администратора в ответ пользователю"""
    if message.text and message.text.strip().lower() == "/stop":
        data = await state.get_data()
        user_id = data.get("support_reply_user_id")
        await state.clear()

        # Завершаем диалог от администратора
        if user_id:
            try:
                msg_ids = await support_repo.get_message_ids(user_id)
                for chat_id, msg_id in msg_ids:
                    try:
                        await message.bot.delete_message(chat_id, msg_id)
                    except Exception:
                        pass
                await support_repo.delete_by_user(user_id)
            except Exception as e:
                print(f"Ошибка удаления сообщений поддержки: {e}")

            try:
                await message.bot.send_message(
                    user_id,
                    "✅ <b>Диалог завершен администратором</b>",
                    parse_mode="HTML"
                )
            except Exception:
                pass

        await message.answer("✅ Режим ответа завершен.", parse_mode="HTML")
        return

    data = await state.get_data()
    user_id = data.get("support_reply_user_id")
    if not user_id:
        await message.answer("❌ Не выбран пользователь для ответа.", parse_mode="HTML")
        return

    # Удаляем уведомления о новом запросе у всех админов
    try:
        alerts = await support_repo.get_admin_alerts(user_id)
        for admin_id, msg_id in alerts:
            try:
                await message.bot.delete_message(admin_id, msg_id)
            except Exception:
                pass
        await support_repo.delete_admin_alerts(user_id)
    except Exception:
        pass

    # Добавляем ответ администратора в историю пользователя
    if message.text:
        history_item = message.text
    elif message.caption:
        history_item = message.caption
    else:
        history_item = "[сообщение]"

    await support_repo.add_message(
        user_id=user_id,
        chat_id=message.chat.id,
        message_id=message.message_id,
        role="admin",
        text=history_item,
    )

    try:
        sent_header = await message.bot.send_message(
            user_id,
            "💬 <b>Ответ администратора:</b>",
            parse_mode="HTML"
        )
        await support_repo.add_message(
            user_id=user_id,
            chat_id=user_id,
            message_id=sent_header.message_id,
            role="bot",
            text="Ответ администратора",
        )

        sent_copy = await message.bot.copy_message(
            chat_id=user_id,
            from_chat_id=message.chat.id,
            message_id=message.message_id
        )
        await support_repo.add_message(
            user_id=user_id,
            chat_id=user_id,
            message_id=sent_copy.message_id,
            role="bot",
            text=None,
        )
        sent_confirm = await message.answer("✅ Ответ отправлен.", parse_mode="HTML")
        try:
            await support_repo.add_message(
                user_id=user_id,
                chat_id=message.chat.id,
                message_id=sent_confirm.message_id,
                role="bot",
                text="Ответ отправлен",
            )
        except Exception:
            pass
    except Exception as e:
        await message.answer(f"❌ Не удалось отправить ответ: {e}")

async def unknown_message(message: Message):
    """Обработчик неизвестных сообщений"""
    await message.answer(
        "🤔 <b>Не понимаю команду</b>\n\n"
        "Используйте кнопки меню или команду /start для начала работы.",
        reply_markup=get_main_menu_keyboard(),
        parse_mode="HTML"
    )

async def back_to_main_callback(callback: CallbackQuery, is_admin: bool = False):
    """Обработчик кнопки 'Назад в главное меню'"""
    await callback.message.edit_text(
        "🏠 <b>Главное меню</b>\n\nВыберите действие:",
        reply_markup=get_main_menu_keyboard(is_admin)
    )

async def back_to_admin_callback(callback: CallbackQuery):
    """Обработчик кнопки 'Назад в админ-панель'"""
    await callback.message.edit_text(
        "🔧 <b>Админ-панель</b>\n\nВыберите действие:",
        reply_markup=get_admin_keyboard()
    )

async def back_to_services_management_callback(callback: CallbackQuery):
    """Обработчик кнопки 'Назад к управлению услугами'"""
    await callback.message.edit_text(
        "📸 <b>Управление услугами</b>\n\nВыберите действие:",
        reply_markup=get_services_management_keyboard()
    )

async def back_to_bookings_management_callback(callback: CallbackQuery):
    """Обработчик кнопки 'Назад к управлению бронированиями'"""
    await callback.message.edit_text(
        "📅 <b>Управление бронированиями</b>\n\nВыберите действие:",
        reply_markup=get_bookings_management_keyboard()
    )

async def contacts_callback(callback: CallbackQuery):
    """Обработчик кнопки контактов"""
    contacts_text = """
📞 <b>Контакты фотостудии</b>

<b>Телефон:</b> +7 (900) 123-45-67
<b>WhatsApp:</b> +7 (900) 123-45-67
<b>Email:</b> info@studio.ru
<b>Сайт:</b> https://studio.ru

<b>Адрес:</b> г. Москва, ул. Примерная, д. 1
<b>Время работы:</b> 9:00 - 21:00 (ежедневно)

<b>Как добраться:</b>
🚇 Метро "Примерная" (5 мин пешком)
🚌 Автобусы: 123, 456 (остановка "Студия")
🚗 Парковка: бесплатная
    """
    
    await callback.message.edit_text(
        contacts_text,
        reply_markup=get_contacts_keyboard()
    )

async def my_bookings_callback(callback: CallbackQuery):
    """Обработчик кнопки моих бронирований"""
    await callback.message.edit_text(
        "📅 <b>Мои бронирования</b>\n\nВыберите действие:",
        reply_markup=get_my_bookings_keyboard()
    )

async def admin_clients_callback(callback: CallbackQuery):
    """Обработчик кнопки управления клиентами"""
    await callback.message.edit_text(
        "👥 <b>Управление клиентами</b>\n\nВыберите действие:",
        reply_markup=get_clients_management_keyboard()
    )

async def admin_admins_callback(callback: CallbackQuery):
    """Обработчик кнопки управления администраторами"""
    await callback.message.edit_text(
        "👨‍💼 <b>Управление администраторами</b>\n\nВыберите действие:",
        reply_markup=get_admins_management_keyboard()
    )

async def unknown_callback(callback: CallbackQuery):
    """Обработчик неизвестных callback'ов"""
    await callback.answer("Неизвестная команда", show_alert=True)

def register_common_handlers(dp: Dispatcher):
    """Регистрация общих обработчиков"""
    dp.callback_query.register(help_callback, F.data == "help")
    dp.callback_query.register(contacts_callback, F.data == "contacts")
    dp.callback_query.register(my_bookings_callback, F.data == "my_bookings")
    dp.callback_query.register(admin_clients_callback, F.data == "admin_clients")
    dp.callback_query.register(admin_admins_callback, F.data == "admin_admins")
    dp.callback_query.register(back_to_main_callback, F.data == "back_to_main")
    dp.callback_query.register(back_to_admin_callback, F.data == "admin_panel")
    dp.callback_query.register(back_to_services_management_callback, F.data == "admin_services")
    dp.callback_query.register(back_to_bookings_management_callback, F.data == "admin_bookings")
    dp.callback_query.register(support_end_callback, F.data == "support_end")
    dp.callback_query.register(support_reply_username_callback, F.data.startswith("support_reply_username_"))
    dp.callback_query.register(support_reply_callback, F.data.startswith("support_reply_"))

    dp.message.register(support_user_message, SupportStates.user_chat)
    dp.message.register(support_admin_message, SupportStates.admin_reply)

    dp.message.register(unknown_message)
    dp.callback_query.register(unknown_callback)
