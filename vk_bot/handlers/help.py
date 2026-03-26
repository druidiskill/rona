from __future__ import annotations

from enum import Enum

from vkbottle import BaseStateGroup, Keyboard, KeyboardButtonColor, Text
from vkbottle.bot import Bot, Message

from config import VK_GROUP_ID
from database import admin_repo, faq_repo, support_repo
from vk_bot.keyboards import get_main_menu_keyboard


class VkSupportState(BaseStateGroup, Enum):
    user_chat = "user_chat"


def _faq_keyboard(page: int, total_pages: int, items: list[tuple[int, str]]) -> str:
    kb = Keyboard(one_time=False, inline=False)
    for faq_id, question in items:
        short_question = question if len(question) <= 37 else f"{question[:34]}..."
        kb.add(
            Text(
                f"❓ {short_question}",
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

    kb.add(
        Text("💬 Связь с админом", payload={"a": "faq_contact"}),
        color=KeyboardButtonColor.POSITIVE,
    ).row()
    kb.add(Text("🔙 Назад", payload={"a": "faq_back"}), color=KeyboardButtonColor.SECONDARY)
    return kb.get_json()


def _support_keyboard() -> str:
    kb = Keyboard(one_time=False, inline=False)
    kb.add(Text("🔙 Назад", payload={"a": "faq_back"}), color=KeyboardButtonColor.SECONDARY)
    return kb.get_json()


async def _get_faq_page_data(page: int) -> tuple[list[tuple[int, str]], int, int]:
    faqs = await faq_repo.get_all_active()
    page_size = 6
    total = len(faqs)
    total_pages = max(1, (total + page_size - 1) // page_size)
    page = max(0, min(page, total_pages - 1))
    start = page * page_size
    end = min(start + page_size, total)
    items = [(entry.id, entry.question) for entry in faqs[start:end] if entry.id is not None]
    return items, total_pages, page


async def send_faq_list(message: Message, page: int = 0) -> None:
    items, total_pages, page = await _get_faq_page_data(page)
    text = "ℹ️ Часто задаваемые вопросы\n\n"
    if not items:
        text += "Список FAQ пока пуст.\n\nВы можете связаться с администратором."
    else:
        text += "Выберите вопрос кнопкой ниже или напишите администратору."
    await message.answer(text, keyboard=_faq_keyboard(page, total_pages, items))


async def forward_question_to_vk_admins(message: Message) -> bool:
    admins = await admin_repo.get_all()
    active_admins = [admin for admin in admins if admin.is_active and admin.vk_id]
    if not active_admins:
        return False

    text = (message.text or "").strip()
    if not text:
        return False

    user = await message.get_user()
    user_label = f"{getattr(user, 'first_name', '')} {getattr(user, 'last_name', '')}".strip() or "Пользователь"
    dialog_link = f"https://vk.com/gim{VK_GROUP_ID}/convo/{message.from_id}?entrypoint=list_all"

    await support_repo.add_message(
        user_id=message.from_id,
        chat_id=message.peer_id,
        message_id=message.message_id,
        role="user",
        text=text,
    )

    admin_text = f"{text}\n{dialog_link}"

    for admin in active_admins:
        try:
            sent = await message.ctx_api.messages.send(
                peer_id=admin.vk_id,
                random_id=0,
                message=admin_text,
            )
            admin_msg_id = sent[0].conversation_message_id if isinstance(sent, list) else sent
            await support_repo.add_message(
                user_id=message.from_id,
                chat_id=admin.vk_id,
                message_id=int(admin_msg_id or 0),
                role="admin_alert",
                text=f"{user_label}\n{admin_text}",
            )
        except Exception as exc:
            print(f"Не удалось отправить сообщение админу {admin.vk_id}: {exc}")

    return True


async def _forward_user_to_vk_admins(message: Message) -> None:
    if not (message.text or "").strip():
        await message.answer(
            "Введите текст вопроса или нажмите «Назад».",
            keyboard=_support_keyboard(),
        )
        return

    forwarded = await forward_question_to_vk_admins(message)
    if not forwarded:
        await message.answer(
            "Сейчас нет доступных администраторов. Попробуйте позже.",
            keyboard=_support_keyboard(),
        )


def register_help_handlers(bot: Bot) -> None:
    @bot.on.message(text=["ℹ️ Помощь", "Помощь", "помощь"])
    async def help_entry(message: Message):
        await send_faq_list(message, page=0)

    @bot.on.message(payload_contains={"a": "faq_page"})
    async def faq_page(message: Message):
        payload = message.get_payload_json() or {}
        await send_faq_list(message, page=int(payload.get("p", 0)))

    @bot.on.message(payload_contains={"a": "faq_open"})
    async def faq_open(message: Message):
        payload = message.get_payload_json() or {}
        faq_id = int(payload.get("id"))
        page = int(payload.get("p", 0))
        entry = await faq_repo.get_by_id(faq_id)
        items, total_pages, current_page = await _get_faq_page_data(page)
        if not entry or not entry.is_active:
            await message.answer("Вопрос не найден.", keyboard=_faq_keyboard(current_page, total_pages, items))
            return

        text = f"❓ {entry.question}\n\n💡 {entry.answer}"
        await message.answer(text, keyboard=_faq_keyboard(current_page, total_pages, items))

    @bot.on.message(payload_contains={"a": "faq_contact"})
    async def faq_contact(message: Message):
        await bot.state_dispenser.set(message.peer_id, VkSupportState.user_chat)
        await message.answer(
            "💬 Связь с администратором\n\nВведите ваш вопрос одним сообщением.",
            keyboard=_support_keyboard(),
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
        payload = message.get_payload_json() or {}
        if payload.get("a") == "faq_back":
            await bot.state_dispenser.delete(message.peer_id)
            await message.answer(
                "🏠 Главное меню\n\nВыберите действие:",
                keyboard=get_main_menu_keyboard(),
            )
            return
        await bot.state_dispenser.delete(message.peer_id)
        await _forward_user_to_vk_admins(message)
