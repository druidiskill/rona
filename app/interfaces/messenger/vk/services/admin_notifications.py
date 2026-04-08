from __future__ import annotations

import ssl

import certifi
from aiohttp import TCPConnector
from vkbottle import API, AiohttpClient

from config import VK_BOT_TOKEN
from app.core.modules.support.common import get_active_admin_targets
from app.integrations.local.db import admin_repo


def _build_vk_api() -> API:
    ssl_context = ssl.create_default_context(cafile=certifi.where())
    http_client = AiohttpClient(connector=TCPConnector(ssl=ssl_context))
    return API(token=VK_BOT_TOKEN, http_client=http_client)


async def _get_active_admin_vk_ids() -> list[int]:
    admins = await admin_repo.get_all()
    return get_active_admin_targets(admins, channel="vk")


async def send_vk_admin_notification(
    *,
    notification,
    api: API | None = None,
) -> None:
    text = getattr(notification, "text", None)
    if not text or not VK_BOT_TOKEN:
        return

    admin_ids = await _get_active_admin_vk_ids()
    if not admin_ids:
        return

    own_api = api is None
    vk_api = api or _build_vk_api()
    try:
        for admin_id in admin_ids:
            try:
                await vk_api.messages.send(
                    peer_id=admin_id,
                    random_id=0,
                    message=text,
                )
            except Exception as exc:
                print(f"Не удалось отправить VK-уведомление админу {admin_id}: {exc}")
    finally:
        if own_api:
            await vk_api.http_client.close()
