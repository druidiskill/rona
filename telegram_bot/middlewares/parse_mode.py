from aiogram import BaseMiddleware
from aiogram.types import Message, CallbackQuery
from typing import Callable, Dict, Any, Awaitable

class ParseModeMiddleware(BaseMiddleware):
    """Middleware для автоматического добавления parse_mode"""
    
    async def __call__(
        self,
        handler: Callable[[Message, Dict[str, Any]], Awaitable[Any]],
        event: Message | CallbackQuery,
        data: Dict[str, Any]
    ) -> Any:
        # Добавляем parse_mode в данные
        data["parse_mode"] = "HTML"
        
        return await handler(event, data)
