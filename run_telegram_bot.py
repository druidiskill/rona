#!/usr/bin/env python3
"""Cross-platform launcher for Telegram bot (Windows/Ubuntu)."""

from __future__ import annotations

import asyncio
import platform
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from config import TELEGRAM_BOT_TOKEN
from telegram_bot.main import main as telegram_main


def _configure_event_loop_policy() -> None:
    # On Windows, SelectorEventLoop is more stable for networking libs.
    if platform.system().lower().startswith("win"):
        try:
            asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
        except Exception:
            pass


def _run_async(coro) -> None:
    _configure_event_loop_policy()
    asyncio.run(coro)


def run() -> int:
    if not TELEGRAM_BOT_TOKEN:
        print("TELEGRAM_BOT_TOKEN не задан в .env")
        return 1

    try:
        print("Запуск Telegram бота...")
        _run_async(telegram_main())
        return 0
    except KeyboardInterrupt:
        print("\nTelegram бот остановлен")
        return 0
    except Exception as e:
        print(f"Ошибка при запуске Telegram бота: {e}")
        return 1


if __name__ == "__main__":
    raise SystemExit(run())
