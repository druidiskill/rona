from aiogram.fsm.state import State, StatesGroup

class BookingStates(StatesGroup):
    """РЎРѕСЃС‚РѕСЏРЅРёСЏ РїСЂРѕС†РµСЃСЃР° Р±СЂРѕРЅРёСЂРѕРІР°РЅРёСЏ"""
    filling_form = State()
    entering_name = State()
    entering_last_name = State()
    entering_phone = State()
    entering_discount_code = State()
    entering_comment = State()
    entering_guests_count = State()
    entering_duration = State()
    entering_email = State()
    selecting_extras = State()
    selecting_date = State()

class AdminStates(StatesGroup):
    """РЎРѕСЃС‚РѕСЏРЅРёСЏ Р°РґРјРёРЅ-РїР°РЅРµР»Рё"""
    waiting_for_service_name = State()
    waiting_for_service_description = State()
    waiting_for_service_price = State()
    waiting_for_service_duration = State()
    
    # РќРѕРІС‹Рµ СЃРѕСЃС‚РѕСЏРЅРёСЏ РґР»СЏ РґРѕР±Р°РІР»РµРЅРёСЏ СѓСЃР»СѓРі
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
    
    # РЎРѕСЃС‚РѕСЏРЅРёСЏ РґР»СЏ СЂРµРґР°РєС‚РёСЂРѕРІР°РЅРёСЏ СѓСЃР»СѓРіРё
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
    waiting_for_faq_question = State()
    waiting_for_faq_answer = State()
    waiting_for_faq_edit_question = State()
    waiting_for_faq_edit_answer = State()


class SupportStates(StatesGroup):
    """РЎРѕСЃС‚РѕСЏРЅРёСЏ РїРѕРґРґРµСЂР¶РєРё"""
    user_chat = State()
    admin_reply = State()

