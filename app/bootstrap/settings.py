from __future__ import annotations

from dataclasses import dataclass

import config as legacy_config


@dataclass(frozen=True)
class AppSettings:
    telegram_bot_token: str | None
    vk_bot_token: str | None
    vk_group_id: str | None
    redis_url: str
    vk_redis_key_prefix: str
    vk_redis_state_ttl_seconds: int
    google_calendar_id: str | None
    google_credentials_file: str
    google_token_file: str
    database_url: str
    admin_username: str
    admin_password: str
    admin_ids_tg: str
    admin_ids_vk: str
    reminder_hour_msk: str | None


def load_settings() -> AppSettings:
    return AppSettings(
        telegram_bot_token=legacy_config.TELEGRAM_BOT_TOKEN,
        vk_bot_token=legacy_config.VK_BOT_TOKEN,
        vk_group_id=legacy_config.VK_GROUP_ID,
        redis_url=legacy_config.REDIS_URL,
        vk_redis_key_prefix=legacy_config.VK_REDIS_KEY_PREFIX,
        vk_redis_state_ttl_seconds=legacy_config.VK_REDIS_STATE_TTL_SECONDS,
        google_calendar_id=legacy_config.GOOGLE_CALENDAR_ID,
        google_credentials_file=legacy_config.GOOGLE_CREDENTIALS_FILE,
        google_token_file=legacy_config.GOOGLE_TOKEN_FILE,
        database_url=legacy_config.DATABASE_URL,
        admin_username=legacy_config.ADMIN_USERNAME,
        admin_password=legacy_config.ADMIN_PASSWORD,
        admin_ids_tg=legacy_config.ADMIN_IDS_TG,
        admin_ids_vk=legacy_config.ADMIN_IDS_VK,
        reminder_hour_msk=legacy_config.REMINDER_HOUR_MSK,
    )
