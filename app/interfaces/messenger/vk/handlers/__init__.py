from vkbottle.bot import Bot

from .admin import register_admin_handlers
from .admin_extra_services import register_admin_extra_service_handlers
from .admin_services import register_admin_service_handlers
from .booking import register_booking_handlers
from .help import register_help_handlers
from .start import register_start_handlers


def register_handlers(bot: Bot):
    register_booking_handlers(bot)
    register_help_handlers(bot)
    register_admin_handlers(bot)
    register_admin_service_handlers(bot)
    register_admin_extra_service_handlers(bot)
    register_start_handlers(bot)
