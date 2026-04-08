from __future__ import annotations

from aiogram import Bot
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from app.integrations.local.db import support_repo


async def send_support_request_to_telegram_admins(
    *,
    bot: Bot,
    admin_ids: list[int],
    user_id: int,
    source_chat_id: int,
    source_message_id: int,
    header_html: str,
) -> list[int]:
    if not admin_ids:
        return []

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Ответить", callback_data=f"support_reply_{user_id}")]
        ]
    )

    for admin_id in admin_ids:
        try:
            sent = await bot.send_message(
                admin_id,
                header_html,
                reply_markup=keyboard,
                parse_mode="HTML",
            )
            await support_repo.add_message(
                user_id=user_id,
                chat_id=admin_id,
                message_id=sent.message_id,
                role="admin_alert",
                text=None,
            )
            copied = await bot.copy_message(
                chat_id=admin_id,
                from_chat_id=source_chat_id,
                message_id=source_message_id,
            )
            await support_repo.add_message(
                user_id=user_id,
                chat_id=admin_id,
                message_id=copied.message_id,
                role="bot",
                text=None,
            )
        except Exception as exc:
            print(f"Не удалось отправить сообщение админу {admin_id}: {exc}")

    return admin_ids
