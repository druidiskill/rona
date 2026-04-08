from __future__ import annotations

from aiogram import Bot as TelegramBot
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from app.integrations.local.db import admin_repo


def _build_reply_markup(notification) -> InlineKeyboardMarkup | None:
    contact_url = getattr(notification, "contact_url", None)
    support_callback_data = getattr(notification, "support_callback_data", None)
    if not contact_url and not support_callback_data:
        return None

    rows: list[list[InlineKeyboardButton]] = []
    if contact_url:
        rows.append([InlineKeyboardButton(text="Связаться в Telegram", url=contact_url)])
    if support_callback_data:
        rows.append([InlineKeyboardButton(text="Связаться во внутреннем чате", callback_data=support_callback_data)])
    return InlineKeyboardMarkup(inline_keyboard=rows)


async def _get_active_admin_telegram_ids() -> list[int]:
    admins = await admin_repo.get_all()
    return [admin.telegram_id for admin in admins if admin.is_active and admin.telegram_id]


async def send_telegram_admin_notification(
    *,
    notification,
    bot: TelegramBot | None = None,
    bot_token: str | None = None,
) -> None:
    if not notification:
        return

    admin_ids = await _get_active_admin_telegram_ids()
    if not admin_ids:
        return

    own_bot = bot is None
    telegram_bot = bot or TelegramBot(token=bot_token)
    reply_markup = _build_reply_markup(notification)

    try:
        for admin_id in admin_ids:
            try:
                await telegram_bot.send_message(
                    admin_id,
                    notification.text,
                    reply_markup=reply_markup,
                    parse_mode="HTML",
                )
            except Exception as exc:
                print(f"Не удалось отправить уведомление админу {admin_id}: {exc}")
    finally:
        if own_bot:
            await telegram_bot.session.close()
