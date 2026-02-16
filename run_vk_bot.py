#!/usr/bin/env python3
"""Cross-platform launcher for VK bot (Windows/Ubuntu)."""

from __future__ import annotations

import asyncio
import platform
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from config import VK_BOT_TOKEN
from vk_bot.main import build_bot, run_forever


def _configure_event_loop_policy() -> None:
    # On Windows, SelectorEventLoop is more stable for networking libs.
    if platform.system().lower().startswith("win"):
        try:
            asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
        except Exception:
            pass


def _build_bot_in_loop():
    """Build VK bot inside an explicitly managed loop."""
    _configure_event_loop_policy()
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    bot = loop.run_until_complete(build_bot())
    return bot, loop


def run() -> int:
    if not VK_BOT_TOKEN:
        print("VK_BOT_TOKEN/VK_GROUP_TOKEN не задан в .env")
        return 1

    loop = None
    try:
        print("Запуск VK бота...")
        bot, loop = _build_bot_in_loop()
        run_forever(bot)
        return 0
    except KeyboardInterrupt:
        print("\nVK бот остановлен")
        return 0
    except Exception as e:
        print(f"Ошибка при запуске VK бота: {e}")
        return 1
    finally:
        try:
            if loop and loop.is_running():
                loop.stop()
            if loop and not loop.is_closed():
                loop.close()
        except Exception:
            pass


if __name__ == "__main__":
    raise SystemExit(run())
