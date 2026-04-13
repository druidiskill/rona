import asyncio
import logging
import ssl

import certifi
from aiohttp import TCPConnector
from vkbottle import API, AiohttpClient, Bot

from config import REDIS_URL, VK_BOT_TOKEN, VK_REDIS_KEY_PREFIX, VK_REDIS_STATE_TTL_SECONDS
from app.bootstrap import install_asyncio_exception_handler
from app.integrations.local.calendar.cache_sync import run_calendar_cache_sync_loop, sync_calendar_cache
from app.integrations.local.db import db_manager
from app.interfaces.messenger.tg.services.booking_reminders import run_booking_reminder_loop, send_vk_booking_reminders
from app.interfaces.messenger.vk.handlers import register_handlers
from app.interfaces.messenger.vk.state_dispenser import MemoryStateDispenser, RedisStateDispenser

logger = logging.getLogger(__name__)


def _build_vk_api() -> API:
    # Reuse the same CA bundle that works for requests in this environment.
    ssl_context = ssl.create_default_context(cafile=certifi.where())
    http_client = AiohttpClient(connector=TCPConnector(ssl=ssl_context))
    return API(token=VK_BOT_TOKEN, http_client=http_client)


async def build_bot() -> Bot:
    install_asyncio_exception_handler(asyncio.get_running_loop())
    if not VK_BOT_TOKEN:
        raise RuntimeError("VK_BOT_TOKEN/VK_GROUP_TOKEN не задан в .env")

    await db_manager.init_database()
    logger.info("База данных инициализирована")
    try:
        synced_count = await sync_calendar_cache(force=True)
        logger.info("Календарный кэш инициализирован: %s событий", synced_count)
    except Exception:
        logger.exception("Не удалось выполнить первичную синхронизацию календарного кэша")

    state_dispenser = RedisStateDispenser(
        redis_url=REDIS_URL,
        key_prefix=VK_REDIS_KEY_PREFIX,
        ttl_seconds=VK_REDIS_STATE_TTL_SECONDS,
    )
    try:
        await state_dispenser.healthcheck()
    except Exception as e:
        logger.warning(
            "Redis недоступен по REDIS_URL=%s. VK бот будет запущен с in-memory state dispenser. "
            "Состояния VK не переживут перезапуск процесса. Ошибка: %s",
            REDIS_URL,
            e,
        )
        state_dispenser = MemoryStateDispenser(ttl_seconds=VK_REDIS_STATE_TTL_SECONDS)

    bot = Bot(api=_build_vk_api(), state_dispenser=state_dispenser)
    register_handlers(bot)

    async def _vk_reminder_task():
        await run_booking_reminder_loop(
            sender_name="vk",
            send_callback=lambda: send_vk_booking_reminders(bot),
        )

    async def _vk_calendar_cache_task():
        await run_calendar_cache_sync_loop("vk")

    bot.loop_wrapper.add_task(_vk_reminder_task)
    bot.loop_wrapper.add_task(_vk_calendar_cache_task)
    return bot


def run_forever(bot: Bot):
    logger.info("VK bot запущен (Long Poll)")
    bot.run_forever()
