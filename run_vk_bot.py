#!/usr/bin/env python3

import asyncio
import os
import sys

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from vk_bot.main import build_bot, run_forever


if __name__ == "__main__":
    try:
        print("Запуск VK бота...")
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        bot = loop.run_until_complete(build_bot())
        run_forever(bot)
    except KeyboardInterrupt:
        print("\nVK бот остановлен")
    except Exception as e:
        print(f"Ошибка при запуске VK бота: {e}")
        sys.exit(1)
