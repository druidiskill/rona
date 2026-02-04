from aiogram import Dispatcher
from .database import DatabaseMiddleware
from .admin import AdminMiddleware
from .parse_mode import ParseModeMiddleware

def register_middlewares(dp: Dispatcher):
    """Регистрация всех middleware"""
    dp.message.middleware(DatabaseMiddleware())
    dp.callback_query.middleware(DatabaseMiddleware())
    dp.message.middleware(AdminMiddleware())
    dp.callback_query.middleware(AdminMiddleware())
    dp.message.middleware(ParseModeMiddleware())
    dp.callback_query.middleware(ParseModeMiddleware())
