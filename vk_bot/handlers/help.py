from __future__ import annotations

from enum import Enum

from vkbottle import BaseStateGroup, Keyboard, KeyboardButtonColor, Text
from vkbottle.bot import Bot, Message

from database import admin_repo, faq_repo, support_repo
from vk_bot.keyboards import get_main_menu_keyboard


class VkSupportState(BaseStateGroup, Enum):
    user_chat = "user_chat"


def _faq_keyboard(page: int, total_pages: int, items: list[tuple[int, str]]) -> str:
    kb = Keyboard(one_time=False, inline=False)
    for faq_id, question in items:
        kb.add(
            Text(
                f"❓ {question[:64]}",
                payload={"a": "faq_open", "id": faq_id, "p": page},
            ),
            color=KeyboardButtonColor.PRIMARY,
        ).row()

    if total_pages > 1:
        if page > 0:
            kb.add(Text("⬅️", payload={"a": "faq_page", "p": page - 1}), color=KeyboardButtonColor.SECONDARY)
        if page < total_pages - 1:
            kb.add(Text("➡️", payload={"a": "faq_page", "p": page + 1}), color=KeyboardButtonColor.SECONDARY)
        kb.row()

    kb.add(Text("💬 Связаться с администратором", payload={"a": "faq_contact"}), color=KeyboardButtonColor.POSITIVE).row()
    kb.add(Text("🔙 Назад", payload={"a": "faq_back"}), color=KeyboardButtonColor.SECONDARY)
    return kb.get_json()


def _support_keyboard() -> str:
    kb = Keyboard(one_time=False, inline=False)
    kb.add(Text("✅ Закончить диалог", payload={"a": "faq_support_end"}), color=KeyboardButtonColor.NEGATIVE).row()
    kb.add(Text("🔙 Назад", payload={"a": "faq_back"}), color=KeyboardButtonColor.SECONDARY)
    return kb.get_json()


async def _send_faq_list(message: Message, page: int = 0):
    items, total_pages, page = await _get_faq_page_data(page)
    text = "ℹ️ Часто задаваемые вопросы\n\n"
    if not items:
        text += "Список FAQ пока пуст.\n\n"
        text += "Вы можете связаться с администратором."
    else:
        text += "Выберите вопрос кнопкой ниже:"

    await message.answer(text, keyboard=_faq_keyboard(page, total_pages, items))


async def _get_faq_page_data(page: int):
    faqs = await faq_repo.get_all_active()
    page_size = 6
    total = len(faqs)
    total_pages = max(1, (total + page_size - 1) // page_size)
    page = max(0, min(page, total_pages - 1))
    start = page * page_size
    end = min(start + page_size, total)
    items = [(x.id, x.question) for x in faqs[start:end]]
    return items, total_pages, page


async def _forward_user_to_vk_admins(message: Message):
    admins = await admin_repo.get_all()
    active_admins = [a for a in admins if a.is_active and a.vk_id]
    if not active_admins:
        await message.answer(
            "❌ Сейчас нет доступных администраторов. Попробуйте позже.",
            keyboard=_support_keyboard(),
        )
        return

    user = await message.get_user()
    user_label = f"{user.first_name} {user.last_name}".strip() or "Пользователь"
    text = (message.text or "").strip()
    if not text:
        await message.answer("Отправьте текст сообщения.", keyboard=_support_keyboard())
        return

    # сохраняем сообщение пользователя
    await support_repo.add_message(
        user_id=message.from_id,
        chat_id=message.peer_id,
        message_id=message.message_id,
        role="user",
        text=text,
    )

    header = (
        "🆘 Новый запрос поддержки\n\n"
        f"👤 Пользователь: {user_label}\n"
        f"🆔 VK ID: {message.from_id}\n\n"
        f"💬 Сообщение:\n{text}"
    )

    for admin in active_admins:
        try:
            sent = await message.ctx_api.messages.send(
                peer_id=admin.vk_id,
                random_id=0,
                message=header,
            )
            admin_msg_id = sent[0].conversation_message_id if isinstance(sent, list) else sent
            await support_repo.add_message(
                user_id=message.from_id,
                chat_id=admin.vk_id,
                message_id=int(admin_msg_id or 0),
                role="admin_alert",
                text=None,
            )
        except Exception as e:
            print(f"Не удалось отправить сообщение админу {admin.vk_id}: {e}")

    await message.answer(
        "✅ Сообщение отправлено администраторам. Мы скоро ответим.",
        keyboard=_support_keyboard(),
    )


def register_help_handlers(bot: Bot):
    @bot.on.message(text=["ℹ️ Помощь", "Помощь", "помощь"])
    async def help_entry(message: Message):
        await _send_faq_list(message, page=0)

    @bot.on.message(payload_contains={"a": "faq_page"})
    async def faq_page(message: Message):
        payload = message.get_payload_json() or {}
        await _send_faq_list(message, page=int(payload.get("p", 0)))

    @bot.on.message(payload_contains={"a": "faq_open"})
    async def faq_open(message: Message):
        payload = message.get_payload_json() or {}
        faq_id = int(payload.get("id"))
        page = int(payload.get("p", 0))
        entry = await faq_repo.get_by_id(faq_id)
        items, total_pages, page = await _get_faq_page_data(page)
        if not entry or not entry.is_active:
            await message.answer("Вопрос не найден.", keyboard=_faq_keyboard(page, total_pages, items))
            return
        text = f"❓ {entry.question}\n\n💡 {entry.answer}"
        await message.answer(text, keyboard=_faq_keyboard(page, total_pages, items))

    @bot.on.message(payload_contains={"a": "faq_contact"})
    async def faq_contact(message: Message):
        await bot.state_dispenser.set(message.peer_id, VkSupportState.user_chat)
        await message.answer(
            "🆘 Поддержка\n\nОпишите ваш вопрос одним сообщением.\n"
            "Чтобы выйти из режима поддержки, нажмите «✅ Закончить диалог».",
            keyboard=_support_keyboard(),
        )

    @bot.on.message(payload_contains={"a": "faq_support_end"}, state=VkSupportState.user_chat)
    async def faq_support_end(message: Message):
        await bot.state_dispenser.delete(message.peer_id)
        await message.answer(
            "🏠 Главное меню\n\nВыберите действие:",
            keyboard=get_main_menu_keyboard(),
        )

    @bot.on.message(payload_contains={"a": "faq_back"})
    async def faq_back(message: Message):
        await bot.state_dispenser.delete(message.peer_id)
        await message.answer(
            "🏠 Главное меню\n\nВыберите действие:",
            keyboard=get_main_menu_keyboard(),
        )

    @bot.on.message(state=VkSupportState.user_chat)
    async def faq_support_message(message: Message):
        # Позволяем текстовые команды выхода
        txt = (message.text or "").strip().lower()
        if txt in {"закончить диалог", "стоп", "/stop", "назад", "🔙 назад"}:
            await bot.state_dispenser.delete(message.peer_id)
            await message.answer(
                "🏠 Главное меню\n\nВыберите действие:",
                keyboard=get_main_menu_keyboard(),
            )
            return
        await _forward_user_to_vk_admins(message)
