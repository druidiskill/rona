from __future__ import annotations

from dataclasses import dataclass

from config import VK_GROUP_ID
from app.core.modules.booking.presentation import (
    build_telegram_admin_text,
    build_vk_admin_text,
    build_vk_to_telegram_admin_text,
)


@dataclass
class TelegramBookingAdminNotification:
    text: str
    contact_url: str
    support_callback_data: str


@dataclass
class TelegramAdminNotificationFromVk:
    text: str


@dataclass
class VkAdminNotification:
    text: str


def build_telegram_booking_admin_notification(
    *,
    summary: dict,
    phone_html: str,
    telegram_id: int,
    username: str | None,
) -> TelegramBookingAdminNotification:
    contact_url = f"https://t.me/{username}" if username else f"tg://user?id={telegram_id}"
    return TelegramBookingAdminNotification(
        text=build_telegram_admin_text(summary, phone_html=phone_html),
        contact_url=contact_url,
        support_callback_data=f"support_reply_{telegram_id}",
    )


def build_vk_booking_admin_notification_for_telegram(
    *,
    summary: dict,
    vk_id: int,
) -> TelegramAdminNotificationFromVk:
    return TelegramAdminNotificationFromVk(
        text=build_vk_to_telegram_admin_text(summary, vk_id=vk_id),
    )


def build_telegram_booking_admin_notification_for_vk(
    *,
    summary: dict,
    telegram_id: int,
    username: str | None,
) -> VkAdminNotification:
    if username:
        contact_line = f"Telegram: https://t.me/{username}"
    else:
        contact_line = f"Telegram ID: {telegram_id}"
    return VkAdminNotification(
        text=build_vk_admin_text(
            summary,
            source_label="Telegram",
            contact_line=contact_line,
        ),
    )


def build_vk_booking_admin_notification(
    *,
    summary: dict,
    vk_id: int,
) -> VkAdminNotification:
    dialog_link = (
        f"https://vk.com/gim{VK_GROUP_ID}/convo/{vk_id}?entrypoint=list_all"
        if VK_GROUP_ID
        else None
    )
    contact_line = dialog_link or f"VK ID: {vk_id}"
    return VkAdminNotification(
        text=build_vk_admin_text(
            summary,
            source_label="VK",
            contact_line=contact_line,
        ),
    )
