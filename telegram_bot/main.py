import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from config import TELEGRAM_BOT_TOKEN
from db import db_manager
from telegram_bot.handlers import register_handlers
from telegram_bot.middlewares import register_middlewares
from telegram_bot.services.booking_reminders import run_booking_reminder_loop, send_telegram_booking_reminders

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
    reminder_task = asyncio.create_task(
        run_booking_reminder_loop(
            sender_name="telegram",
            send_callback=lambda: send_telegram_booking_reminders(bot),
        )
    )
    
    logger.info("Telegram бот запущен")
    
    try:
        # Запуск бота
        await dp.start_polling(bot)
    finally:
        reminder_task.cancel()
        try:
            await reminder_task
        except asyncio.CancelledError:
            pass
        await bot.session.close()

if __name__ == "__main__":
    asyncio.run(main())
