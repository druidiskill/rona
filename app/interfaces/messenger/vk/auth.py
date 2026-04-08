from __future__ import annotations

from config import ADMIN_IDS_VK
from app.integrations.local.db import admin_repo


def _parse_admin_ids(value: str) -> set[int]:
    return {int(x.strip()) for x in value.split(",") if x.strip().isdigit()}


ENV_ADMIN_IDS = _parse_admin_ids(ADMIN_IDS_VK)


async def is_vk_admin_id(vk_id: int | None) -> bool:
    if not vk_id:
        return False

    normalized_vk_id = int(vk_id)
    if normalized_vk_id in ENV_ADMIN_IDS:
        return True

    admin = await admin_repo.get_by_vk_id(normalized_vk_id)
    return bool(admin)
