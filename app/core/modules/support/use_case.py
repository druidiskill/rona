from __future__ import annotations

from dataclasses import dataclass

from app.core.modules.support.common import (
    build_telegram_support_alert_text,
    build_vk_support_alert_text,
    get_active_admin_targets,
)


def build_support_history_item(*, text: str | None, caption: str | None, content_type: str | None) -> str:
    if text:
        return text
    if caption:
        return caption
    return f"[{content_type or 'message'}]"


@dataclass
class TelegramSupportRequest:
    active_admin_ids: list[int]
    history_item: str
    header_html: str | None


@dataclass
class VkSupportRequest:
    active_admin_ids: list[int]
    question_text: str
    admin_text: str | None


async def prepare_telegram_support_request(
    *,
    admin_repo,
    support_repo,
    user_id: int,
    chat_id: int,
    message_id: int,
    user_full_name: str,
    username: str | None,
    text: str | None,
    caption: str | None,
    content_type: str | None,
) -> TelegramSupportRequest:
    admins = await admin_repo.get_all()
    active_admin_ids = get_active_admin_targets(admins, channel="telegram")
    history_item = build_support_history_item(text=text, caption=caption, content_type=content_type)
    if not active_admin_ids:
        return TelegramSupportRequest(active_admin_ids=[], history_item=history_item, header_html=None)

    await support_repo.add_message(
        user_id=user_id,
        chat_id=chat_id,
        message_id=message_id,
        role="user",
        text=history_item,
    )

    history_rows = await support_repo.get_last_messages(user_id, limit=6)
    header_html = build_telegram_support_alert_text(
        user_full_name=user_full_name,
        user_id=user_id,
        username=username,
        history_rows=history_rows,
    )
    return TelegramSupportRequest(
        active_admin_ids=active_admin_ids,
        history_item=history_item,
        header_html=header_html,
    )


async def prepare_vk_support_request(
    *,
    admin_repo,
    support_repo,
    user_id: int,
    chat_id: int,
    message_id: int,
    question_text: str,
    user_label: str,
    dialog_link: str,
) -> VkSupportRequest:
    admins = await admin_repo.get_all()
    active_admin_ids = get_active_admin_targets(admins, channel="vk")
    question_text = (question_text or "").strip()
    if not active_admin_ids or not question_text:
        return VkSupportRequest(active_admin_ids=[], question_text=question_text, admin_text=None)

    await support_repo.add_message(
        user_id=user_id,
        chat_id=chat_id,
        message_id=message_id,
        role="user",
        text=question_text,
    )

    admin_text = build_vk_support_alert_text(question=question_text, dialog_link=dialog_link)
    return VkSupportRequest(
        active_admin_ids=active_admin_ids,
        question_text=question_text,
        admin_text=f"{user_label}\n{admin_text}",
    )
