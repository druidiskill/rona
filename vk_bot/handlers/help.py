from __future__ import annotations

from enum import Enum

from vkbottle import BaseStateGroup, Keyboard, KeyboardButtonColor, Text
from vkbottle.bot import Bot, Message

from config import VK_GROUP_ID
from db import admin_repo, faq_repo, support_repo
from core.support.common import (
    build_faq_list_text,
    get_faq_page_data,
    truncate_question,
)
from core.support.use_case import prepare_vk_support_request
from vk_bot.services.support_notifications import send_support_request_to_vk_admins
from vk_bot.keyboards import get_main_menu_keyboard


class VkSupportState(BaseStateGroup, Enum):
    user_chat = "user_chat"


def _faq_keyboard(page: int, total_pages: int, items: list[tuple[int, str]]) -> str:
    kb = Keyboard(one_time=False, inline=False)
    for faq_id, question in items:
        short_question = truncate_question(question, max_length=37)
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
    return await get_faq_page_data(faq_repo=faq_repo, page=page)


async def send_faq_list(message: Message, page: int = 0) -> None:
    items, total_pages, page = await _get_faq_page_data(page)
    text = build_faq_list_text(has_items=bool(items), html_mode=False)
    await message.answer(text, keyboard=_faq_keyboard(page, total_pages, items))


async def forward_question_to_vk_admins(message: Message) -> bool:
    user = await message.get_user()
    user_label = f"{getattr(user, 'first_name', '')} {getattr(user, 'last_name', '')}".strip() or "Пользователь"
    dialog_link = f"https://vk.com/gim{VK_GROUP_ID}/convo/{message.from_id}?entrypoint=list_all"

    support_request = await prepare_vk_support_request(
        admin_repo=admin_repo,
        support_repo=support_repo,
        user_id=message.from_id,
        chat_id=message.peer_id,
        message_id=message.message_id,
        question_text=message.text or "",
        user_label=user_label,
        dialog_link=dialog_link,
    )
    sent_admin_ids = await send_support_request_to_vk_admins(
        message=message,
        admin_ids=support_request.active_admin_ids,
        admin_text=support_request.admin_text or "",
    )
    return bool(sent_admin_ids)


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
