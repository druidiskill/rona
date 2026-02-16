from aiogram.fsm.state import State, StatesGroup

class BookingStates(StatesGroup):
    """Состояния процесса бронирования"""
    filling_form = State()
    entering_name = State()
    entering_phone = State()
    entering_guests_count = State()
    entering_duration = State()
    entering_email = State()
    selecting_extras = State()
    selecting_date = State()

class AdminStates(StatesGroup):
    """Состояния админ-панели"""
    waiting_for_service_name = State()
    waiting_for_service_description = State()
    waiting_for_service_price = State()
    waiting_for_service_duration = State()
    
    # Новые состояния для добавления услуг
    waiting_for_new_service_name = State()
    waiting_for_new_service_description = State()
    waiting_for_new_service_price_weekday = State()
    waiting_for_new_service_price_weekend = State()
    waiting_for_new_service_price_extra_weekday = State()
    waiting_for_new_service_price_extra_weekend = State()
    waiting_for_new_service_price_group = State()
    waiting_for_new_service_max_clients = State()
    waiting_for_new_service_duration = State()
    waiting_for_new_service_photos = State()
    
    # Состояния для редактирования услуги
    waiting_for_edit_service_name = State()
    waiting_for_edit_service_description = State()
    waiting_for_edit_service_price_weekday = State()
    waiting_for_edit_service_price_weekend = State()
    waiting_for_edit_service_price_extra_weekday = State()
    waiting_for_edit_service_price_extra_weekend = State()
    waiting_for_edit_service_price_group = State()
    waiting_for_edit_service_max_clients = State()
    waiting_for_edit_service_duration = State()
    waiting_for_edit_service_photos = State()
    waiting_for_booking_search_query = State()


class SupportStates(StatesGroup):
    """Состояния поддержки"""
    user_chat = State()
    admin_reply = State()
