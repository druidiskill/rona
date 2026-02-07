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
from config import ADMIN_IDS_TG

def _parse_admin_ids(value: str):
    return [int(x.strip()) for x in value.split(",") if x.strip().isdigit()]

admins_ids = _parse_admin_ids(ADMIN_IDS_TG)

if __name__ == "__main__":
    try:
        print("🚀 Запуск Telegram бота...")
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n⏹️ Бот остановлен пользователем")
    except Exception as e:
        print(f"❌ Ошибка при запуске бота: {e}")
        sys.exit(1)
