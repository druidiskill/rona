from aiogram import BaseMiddleware
from aiogram.types import Message, CallbackQuery
from typing import Callable, Dict, Any, Awaitable

from database import admin_repo

class AdminMiddleware(BaseMiddleware):
    """Middleware для проверки прав администратора"""
    
    async def __call__(
        self,
        handler: Callable[[Message, Dict[str, Any]], Awaitable[Any]],
        event: Message | CallbackQuery,
        data: Dict[str, Any]
    ) -> Any:
        # Проверяем, является ли пользователь админом
        user_id = event.from_user.id if hasattr(event, 'from_user') else None
        
        if user_id:
            admin = await admin_repo.get_by_telegram_id(user_id)
            data["is_admin"] = admin is not None
            data["admin"] = admin
        else:
            data["is_admin"] = False
            data["admin"] = None
        
        return await handler(event, data)
