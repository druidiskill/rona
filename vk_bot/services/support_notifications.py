from __future__ import annotations

from db import support_repo


async def send_support_request_to_vk_admins(
    *,
    message,
    admin_ids: list[int],
    admin_text: str,
) -> list[int]:
    if not admin_ids:
        return []

    for admin_vk_id in admin_ids:
        try:
            sent = await message.ctx_api.messages.send(
                peer_id=admin_vk_id,
                random_id=0,
                message=admin_text,
            )
            admin_msg_id = sent[0].conversation_message_id if isinstance(sent, list) else sent
            await support_repo.add_message(
                user_id=message.from_id,
                chat_id=admin_vk_id,
                message_id=int(admin_msg_id or 0),
                role="admin_alert",
                text=admin_text,
            )
        except Exception as exc:
            print(f"Не удалось отправить сообщение админу {admin_vk_id}: {exc}")

    return admin_ids
