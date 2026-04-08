import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from config import TELEGRAM_BOT_TOKEN
from app.bootstrap import install_asyncio_exception_handler
from app.integrations.local.db import db_manager
from app.integrations.local.calendar.cache_sync import run_calendar_cache_sync_loop, sync_calendar_cache
from app.interfaces.messenger.tg.handlers import register_handlers
from app.interfaces.messenger.tg.middlewares import register_middlewares
from app.interfaces.messenger.tg.services.booking_reminders import run_booking_reminder_loop, send_telegram_booking_reminders

logger = logging.getLogger(__name__)

async def main():
    """Главная функция запуска бота"""
    install_asyncio_exception_handler(asyncio.get_running_loop())
    # Инициализация базы данных
    await db_manager.init_database()
    logger.info("База данных инициализирована")
    try:
        synced_count = await sync_calendar_cache(force=True)
        logger.info("Календарный кэш инициализирован: %s событий", synced_count)
    except Exception:
        logger.exception("Не удалось выполнить первичную синхронизацию календарного кэша")
    
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
    calendar_cache_task = asyncio.create_task(run_calendar_cache_sync_loop("telegram"))
    
    logger.info("Telegram бот запущен")
    
    try:
        # Запуск бота
        await dp.start_polling(bot)
    finally:
        reminder_task.cancel()
        calendar_cache_task.cancel()
        try:
            await reminder_task
        except asyncio.CancelledError:
            pass
        try:
            await calendar_cache_task
        except asyncio.CancelledError:
            pass
        await bot.session.close()

if __name__ == "__main__":
    asyncio.run(main())
