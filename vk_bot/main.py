import logging

from vkbottle import Bot

from config import REDIS_URL, VK_BOT_TOKEN, VK_REDIS_KEY_PREFIX, VK_REDIS_STATE_TTL_SECONDS
from database import db_manager
from vk_bot.handlers import register_handlers
from vk_bot.state_dispenser import RedisStateDispenser


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


async def build_bot() -> Bot:
    if not VK_BOT_TOKEN:
        raise RuntimeError("VK_BOT_TOKEN/VK_GROUP_TOKEN не задан в .env")

    await db_manager.init_database()
    logger.info("База данных инициализирована")

    state_dispenser = RedisStateDispenser(
        redis_url=REDIS_URL,
        key_prefix=VK_REDIS_KEY_PREFIX,
        ttl_seconds=VK_REDIS_STATE_TTL_SECONDS,
    )
    try:
        await state_dispenser.healthcheck()
    except Exception as e:
        raise RuntimeError(
            f"Redis недоступен по REDIS_URL={REDIS_URL}. "
            "Запустите Redis и проверьте .env"
        ) from e

    bot = Bot(token=VK_BOT_TOKEN, state_dispenser=state_dispenser)
    register_handlers(bot)
    return bot


def run_forever(bot: Bot):
    logger.info("VK bot запущен (Long Poll)")
    bot.run_forever()
