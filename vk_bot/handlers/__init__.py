from vkbottle.bot import Bot

from .booking import register_booking_handlers
from .start import register_start_handlers


def register_handlers(bot: Bot):
    register_booking_handlers(bot)
    register_start_handlers(bot)
