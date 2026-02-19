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
from database import admin_repo, support_repo, faq_repo

FAQ_PAGE_SIZE = 6

def _build_faq_keyboard(items: list[tuple[int, str]], page: int, total_pages: int) -> InlineKeyboardMarkup:
    keyboard: list[list[InlineKeyboardButton]] = []

    for faq_id, question in items:
        short_question = question if len(question) <= 50 else f"{question[:47]}..."
        keyboard.append([
            InlineKeyboardButton(text=f"❓ {short_question}", callback_data=f"faq_open_{faq_id}_{page}")
        ])

    nav_row: list[InlineKeyboardButton] = []
    if total_pages > 1 and page > 0:
        nav_row.append(InlineKeyboardButton(text="⬅️", callback_data=f"faq_page_{page - 1}"))
    if total_pages > 1 and page < total_pages - 1:
        nav_row.append(InlineKeyboardButton(text="➡️", callback_data=f"faq_page_{page + 1}"))
    if nav_row:
        keyboard.append(nav_row)

    keyboard.append([InlineKeyboardButton(text="💬 Связаться с администратором", callback_data="faq_contact")])
    keyboard.append([InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_main")])
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


async def _get_faq_page_data(page: int) -> tuple[list[tuple[int, str]], int, int]:
    faqs = await faq_repo.get_all_active()
    total = len(faqs)
    total_pages = max(1, (total + FAQ_PAGE_SIZE - 1) // FAQ_PAGE_SIZE)
    page = max(0, min(page, total_pages - 1))
    start = page * FAQ_PAGE_SIZE
    end = min(start + FAQ_PAGE_SIZE, total)
    items = [(entry.id, entry.question) for entry in faqs[start:end]]
    return items, total_pages, page


async def send_faq_list_message(message: Message, page: int = 0):
    items, total_pages, page = await _get_faq_page_data(page)

    text = "ℹ️ <b>Часто задаваемые вопросы</b>\n\n"
    if not items:
        text += "Список FAQ пока пуст.\n\nВы можете связаться с администратором."
    else:
        text += "Выберите вопрос кнопкой ниже:"

    await message.answer(
        text,
        reply_markup=_build_faq_keyboard(items, page, total_pages),
        parse_mode="HTML",
    )


async def help_callback(callback: CallbackQuery, state: FSMContext):
    """Обработчик кнопки помощи: показывает FAQ из БД."""
    await state.clear()
    items, total_pages, page = await _get_faq_page_data(0)
    text = "ℹ️ <b>Часто задаваемые вопросы</b>\n\n"
    if not items:
        text += "Список FAQ пока пуст.\n\nВы можете связаться с администратором."
    else:
        text += "Выберите вопрос кнопкой ниже:"

    await callback.message.edit_text(
        text,
        reply_markup=_build_faq_keyboard(items, page, total_pages),
        parse_mode="HTML",
    )
    await callback.answer()


async def faq_page_callback(callback: CallbackQuery):
    """Переключение страницы FAQ."""
    try:
        page = int(callback.data.split("_")[-1])
    except (ValueError, IndexError):
        await callback.answer("Ошибка страницы FAQ", show_alert=True)
        return

    items, total_pages, page = await _get_faq_page_data(page)
    text = "ℹ️ <b>Часто задаваемые вопросы</b>\n\n"
    if not items:
        text += "Список FAQ пока пуст.\n\nВы можете связаться с администратором."
    else:
        text += "Выберите вопрос кнопкой ниже:"

    await callback.message.edit_text(
        text,
        reply_markup=_build_faq_keyboard(items, page, total_pages),
        parse_mode="HTML",
    )
    await callback.answer()


async def faq_open_callback(callback: CallbackQuery):
    """Открывает вопрос FAQ и сохраняет ту же клавиатуру."""
    parts = callback.data.split("_")
    if len(parts) < 4:
        await callback.answer("Ошибка данных FAQ", show_alert=True)
        return

    try:
        faq_id = int(parts[2])
        page = int(parts[3])
    except ValueError:
        await callback.answer("Ошибка данных FAQ", show_alert=True)
        return

    entry = await faq_repo.get_by_id(faq_id)
    items, total_pages, page = await _get_faq_page_data(page)
    keyboard = _build_faq_keyboard(items, page, total_pages)

    if not entry or not entry.is_active:
        await callback.message.edit_text(
            "❌ Вопрос не найден.",
            reply_markup=keyboard,
            parse_mode="HTML",
        )
        await callback.answer()
        return

    text = (
        f"❓ <b>{html.escape(entry.question)}</b>\n\n"
        f"💡 {html.escape(entry.answer)}"
    )
    await callback.message.edit_text(
        text,
        reply_markup=keyboard,
        parse_mode="HTML",
    )
    await callback.answer()


async def faq_contact_callback(callback: CallbackQuery, state: FSMContext):
    """Переход из FAQ в существующий внутренний чат."""
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
    await callback.answer()


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

<b>Email:</b> rona.photostudio.petergof@gmail.com
<b>Сайт:</b> https://innasuvorova.ru/rona_photostudio

<b>Адрес:</b> улица Володи Дубинина, 3, Санкт-Петербург
<b>Время работы:</b> с 9:00 до 21:00 по предварительному бронированию
    """

    await callback.message.edit_text(
        contacts_text,
        reply_markup=get_contacts_keyboard(),
        parse_mode="HTML"
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
    dp.callback_query.register(faq_page_callback, F.data.startswith("faq_page_"))
    dp.callback_query.register(faq_open_callback, F.data.startswith("faq_open_"))
    dp.callback_query.register(faq_contact_callback, F.data == "faq_contact")
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


