from __future__ import annotations

import asyncio
import logging
import platform

from app.bootstrap import configure_logging, load_settings
from app.interfaces.messenger.vk import build_bot, run_forever

logger = logging.getLogger(__name__)


def _configure_event_loop_policy() -> None:
    if platform.system().lower().startswith("win"):
        try:
            asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
        except Exception:
            pass


def _build_bot_in_loop():
    _configure_event_loop_policy()
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    bot = loop.run_until_complete(build_bot())
    return bot, loop


def run() -> int:
    configure_logging()
    settings = load_settings()
    if not settings.vk_bot_token:
        logger.error("VK_BOT_TOKEN/VK_GROUP_TOKEN не задан в .env")
        return 1

    loop = None
    try:
        logger.info("Запуск VK бота...")
        bot, loop = _build_bot_in_loop()
        run_forever(bot)
        return 0
    except KeyboardInterrupt:
        logger.info("VK бот остановлен")
        return 0
    except Exception:
        logger.exception("Ошибка при запуске VK бота")
        return 1
    finally:
        try:
            if loop and loop.is_running():
                loop.stop()
            if loop and not loop.is_closed():
                loop.close()
        except Exception:
            logger.exception("Ошибка при закрытии event loop VK бота")


if __name__ == "__main__":
    raise SystemExit(run())
