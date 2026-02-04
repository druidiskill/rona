from aiogram import Dispatcher
from .start import register_start_handlers
from .services import register_services_handlers
from .booking import register_booking_handlers
from .admin import register_admin_handlers
from .service_management import register_service_management_handlers
from .add_service_new import register_add_service_new_handlers
from .edit_service_new import register_edit_service_new_handlers
from .common import register_common_handlers

def register_handlers(dp: Dispatcher):
    """Регистрация всех обработчиков"""
    register_start_handlers(dp)
    register_services_handlers(dp)
    register_booking_handlers(dp)
    register_admin_handlers(dp)
    register_service_management_handlers(dp)
    register_add_service_new_handlers(dp)
    register_edit_service_new_handlers(dp)
    register_common_handlers(dp)
