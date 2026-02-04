import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.enums import ParseMode

from config import TELEGRAM_BOT_TOKEN
from database import db_manager
from telegram_bot.handlers import register_handlers
from telegram_bot.middlewares import register_middlewares

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def main():
    """Главная функция запуска бота"""
    # Инициализация базы данных
    await db_manager.init_database()
    logger.info("База данных инициализирована")
    
    # Создание бота и диспетчера
    bot = Bot(token=TELEGRAM_BOT_TOKEN)
    
    storage = MemoryStorage()
    dp = Dispatcher(storage=storage)
    
    # Регистрация middleware и обработчиков
    register_middlewares(dp)
    register_handlers(dp)
    
    logger.info("Telegram бот запущен")
    
    try:
        # Запуск бота
        await dp.start_polling(bot)
    finally:
        await bot.session.close()

if __name__ == "__main__":
    asyncio.run(main())
