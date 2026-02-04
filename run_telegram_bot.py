#!/usr/bin/env python3
"""
Запуск Telegram бота для фотостудии
"""

import asyncio
import logging
import sys
import os

# Добавляем корневую папку в путь
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from telegram_bot.main import main

admins_ids = [447392189]

if __name__ == "__main__":
    try:
        print("🚀 Запуск Telegram бота...")
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n⏹️ Бот остановлен пользователем")
    except Exception as e:
        print(f"❌ Ошибка при запуске бота: {e}")
        sys.exit(1)
