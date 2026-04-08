from __future__ import annotations

import asyncio
import logging
import platform

from app.bootstrap import configure_logging, load_settings
from app.interfaces.messenger.tg import main as telegram_main

logger = logging.getLogger(__name__)


def _configure_event_loop_policy() -> None:
    if platform.system().lower().startswith("win"):
        try:
            asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
        except Exception:
            pass


def run() -> int:
    configure_logging()
    settings = load_settings()
    if not settings.telegram_bot_token:
        logger.error("TELEGRAM_BOT_TOKEN не задан в .env")
        return 1

    try:
        logger.info("Запуск Telegram бота...")
        _configure_event_loop_policy()
        asyncio.run(telegram_main())
        return 0
    except KeyboardInterrupt:
        logger.info("Telegram бот остановлен")
        return 0
    except Exception:
        logger.exception("Ошибка при запуске Telegram бота")
        return 1


if __name__ == "__main__":
    raise SystemExit(run())
