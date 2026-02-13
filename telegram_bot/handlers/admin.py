from aiogram import Dispatcher, F
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext

from telegram_bot.keyboards import (
    get_admin_keyboard,
    get_main_menu_keyboard,
    get_services_management_keyboard,
    get_bookings_management_keyboard,
    get_admin_future_bookings_keyboard,
    get_admin_booking_detail_keyboard,
)
from telegram_bot.states import AdminStates
from database import admin_repo, service_repo, client_repo
from datetime import datetime, timedelta
from telegram_bot.services.calendar_queries import (
    is_calendar_available,
    list_events as svc_list_events,
    get_event as svc_get_event,
)
from telegram_bot.services.contact_utils import (
    extract_booking_contact_details as svc_extract_booking_contact_details,
    normalize_phone as svc_normalize_phone,
    format_phone_plus7 as svc_format_phone_plus7,
)


def _extract_booking_contact_details(description: str) -> dict:
    return svc_extract_booking_contact_details(description)


def _normalize_phone(phone: str | None) -> str | None:
    return svc_normalize_phone(phone)


def _format_phone_plus7(phone: str | None) -> str | None:
    return svc_format_phone_plus7(phone)

async def admin_panel(callback: CallbackQuery, is_admin: bool, parse_mode: str = "HTML"):
    """РђРґРјРёРЅ-РїР°РЅРµР»СЊ"""
    if not is_admin:
        await callback.answer("РЈ РІР°СЃ РЅРµС‚ РїСЂР°РІ Р°РґРјРёРЅРёСЃС‚СЂР°С‚РѕСЂР°", show_alert=True)
        return
    
    await callback.message.edit_text(
        "рџ”§ <b>РђРґРјРёРЅ-РїР°РЅРµР»СЊ</b>\n\n"
        "Р’С‹Р±РµСЂРёС‚Рµ РґРµР№СЃС‚РІРёРµ:",
        reply_markup=get_admin_keyboard(),
        parse_mode=parse_mode
    )

async def admin_stats(callback: CallbackQuery, is_admin: bool):
    """РЎС‚Р°С‚РёСЃС‚РёРєР° РґР»СЏ Р°РґРјРёРЅР°"""
    if not is_admin:
        await callback.answer("РЈ РІР°СЃ РЅРµС‚ РїСЂР°РІ Р°РґРјРёРЅРёСЃС‚СЂР°С‚РѕСЂР°", show_alert=True)
        return
    
    # РџРѕР»СѓС‡Р°РµРј СЃС‚Р°С‚РёСЃС‚РёРєСѓ
    services = await service_repo.get_all_active()
    # Р—РґРµСЃСЊ РјРѕР¶РЅРѕ РґРѕР±Р°РІРёС‚СЊ РїРѕР»СѓС‡РµРЅРёРµ СЃС‚Р°С‚РёСЃС‚РёРєРё Р±СЂРѕРЅРёСЂРѕРІР°РЅРёР№
    
    stats_text = f"""рџ“Љ <b>РЎС‚Р°С‚РёСЃС‚РёРєР° СЃС‚СѓРґРёРё</b>

рџ“ё <b>РЈСЃР»СѓРіРё:</b> {len(services)} Р°РєС‚РёРІРЅС‹С…
рџ“… <b>Р‘СЂРѕРЅРёСЂРѕРІР°РЅРёСЏ СЃРµРіРѕРґРЅСЏ:</b> [Р±СѓРґРµС‚ РґРѕР±Р°РІР»РµРЅРѕ]
рџ’° <b>Р’С‹СЂСѓС‡РєР° Р·Р° РјРµСЃСЏС†:</b> [Р±СѓРґРµС‚ РґРѕР±Р°РІР»РµРЅРѕ]
рџ‘Ґ <b>РќРѕРІС‹С… РєР»РёРµРЅС‚РѕРІ:</b> [Р±СѓРґРµС‚ РґРѕР±Р°РІР»РµРЅРѕ]"""
    
    await callback.message.edit_text(
        stats_text,
        reply_markup=get_admin_keyboard(),
        parse_mode="HTML"
    )

async def admin_bookings(callback: CallbackQuery, is_admin: bool):
    """РЈРїСЂР°РІР»РµРЅРёРµ Р±СЂРѕРЅРёСЂРѕРІР°РЅРёСЏРјРё"""
    if not is_admin:
        await callback.answer("РЈ РІР°СЃ РЅРµС‚ РїСЂР°РІ Р°РґРјРёРЅРёСЃС‚СЂР°С‚РѕСЂР°", show_alert=True)
        return

    if not is_calendar_available():
        await callback.message.edit_text(
            "рџ“… <b>Р‘СЂРѕРЅРёСЂРѕРІР°РЅРёСЏ</b>\n\n"
            "Google Calendar РЅРµРґРѕСЃС‚СѓРїРµРЅ. РџСЂРѕРІРµСЂСЊС‚Рµ РЅР°СЃС‚СЂРѕР№РєРё Рё С‚РѕРєРµРЅС‹.",
            reply_markup=get_admin_keyboard(),
            parse_mode="HTML"
        )
        return

    period_start = datetime.now()
    period_end = period_start + timedelta(days=365)
    try:
        events = await svc_list_events(period_start, period_end, max_results=250)
    except Exception as e:
        print(f"РћС€РёР±РєР° РїРѕР»СѓС‡РµРЅРёСЏ СЃРѕР±С‹С‚РёР№ РєР°Р»РµРЅРґР°СЂСЏ: {e}")
        await callback.message.edit_text(
            "рџ“… <b>Р‘СЂРѕРЅРёСЂРѕРІР°РЅРёСЏ</b>\n\n"
            "РќРµ СѓРґР°Р»РѕСЃСЊ РїРѕР»СѓС‡РёС‚СЊ РґР°РЅРЅС‹Рµ РёР· РєР°Р»РµРЅРґР°СЂСЏ.",
            reply_markup=get_admin_keyboard(),
            parse_mode="HTML"
        )
        return

    future_events = [event for event in events if event.get("start")]
    if not future_events:
        await callback.message.edit_text(
            "рџ“… <b>Р‘СЂРѕРЅРёСЂРѕРІР°РЅРёСЏ</b>\n\n"
            "Р‘СѓРґСѓС‰РёС… Р±СЂРѕРЅРёСЂРѕРІР°РЅРёР№ РЅРµС‚.",
            reply_markup=get_admin_keyboard(),
            parse_mode="HTML"
        )
        return

    await callback.message.edit_text(
        "рџ“… <b>Р‘СѓРґСѓС‰РёРµ Р±СЂРѕРЅРёСЂРѕРІР°РЅРёСЏ</b>\n\n"
        "Р’С‹Р±РµСЂРёС‚Рµ Р±СЂРѕРЅРёСЂРѕРІР°РЅРёРµ РґР»СЏ РїСЂРѕСЃРјРѕС‚СЂР° РґРµС‚Р°Р»РµР№:",
        reply_markup=get_admin_future_bookings_keyboard(future_events),
        parse_mode="HTML"
    )


async def admin_booking_open(callback: CallbackQuery, is_admin: bool):
    """РљР°СЂС‚РѕС‡РєР° РІС‹Р±СЂР°РЅРЅРѕРіРѕ Р±СЂРѕРЅРёСЂРѕРІР°РЅРёСЏ РґР»СЏ Р°РґРјРёРЅР°."""
    if not is_admin:
        await callback.answer("РЈ РІР°СЃ РЅРµС‚ РїСЂР°РІ Р°РґРјРёРЅРёСЃС‚СЂР°С‚РѕСЂР°", show_alert=True)
        return

    event_id = callback.data.replace("admin_booking_open_", "", 1)
    if not is_calendar_available():
        await callback.answer("Google Calendar РЅРµРґРѕСЃС‚СѓРїРµРЅ", show_alert=True)
        return

    try:
        raw_event = await svc_get_event(event_id)
    except Exception as e:
        print(f"РћС€РёР±РєР° РїРѕР»СѓС‡РµРЅРёСЏ СЃРѕР±С‹С‚РёСЏ {event_id}: {e}")
        await callback.answer("РќРµ СѓРґР°Р»РѕСЃСЊ РїРѕР»СѓС‡РёС‚СЊ Р±СЂРѕРЅРёСЂРѕРІР°РЅРёРµ", show_alert=True)
        return
    if not raw_event:
        await callback.answer("РќРµ СѓРґР°Р»РѕСЃСЊ РїРѕР»СѓС‡РёС‚СЊ Р±СЂРѕРЅРёСЂРѕРІР°РЅРёРµ", show_alert=True)
        return

    summary = raw_event.get("summary", "Р‘РµР· РЅР°Р·РІР°РЅРёСЏ")
    description = raw_event.get("description", "")
    start_raw = raw_event.get("start", {})
    end_raw = raw_event.get("end", {})
    start = start_raw.get("dateTime") or start_raw.get("date")
    end = end_raw.get("dateTime") or end_raw.get("date")

    start_dt = None
    end_dt = None
    try:
        if start and "T" in start:
            start_dt = datetime.fromisoformat(start)
        if end and "T" in end:
            end_dt = datetime.fromisoformat(end)
    except Exception:
        pass

    contact = _extract_booking_contact_details(description)

    text = "рџ“‹ <b>РРЅС„РѕСЂРјР°С†РёСЏ Рѕ Р±СЂРѕРЅРёСЂРѕРІР°РЅРёРё</b>\n\n"
    text += f"рџЋЇ <b>РЈСЃР»СѓРіР°:</b> {summary}\n"
    if start_dt:
        text += f"рџ“… <b>Р”Р°С‚Р°:</b> {start_dt.strftime('%d.%m.%Y')}\n"
        text += f"рџ•’ <b>Р’СЂРµРјСЏ:</b> {start_dt.strftime('%H:%M')}"
        if end_dt:
            text += f" - {end_dt.strftime('%H:%M')}"
        text += "\n"

    # Р”Р»СЏ СЂРµР¶РёРјР° С‡Р°С‚Р° РЅСѓР¶РµРЅ numeric user_id.
    chat_target_user_id = contact.get("telegram_id")
    if not chat_target_user_id:
        # Р¤РѕР»Р±РµРє: РёС‰РµРј РєР»РёРµРЅС‚Р° РІ Р‘Р” РїРѕ С‚РµР»РµС„РѕРЅСѓ/email Рё Р±РµСЂРµРј РµРіРѕ telegram_id.
        try:
            phone_norm = _normalize_phone(contact.get("phone"))
            db_client = None
            if phone_norm:
                db_client = await client_repo.get_by_phone(phone_norm)
            if (not db_client) and contact.get("email"):
                clients = await client_repo.get_all() if hasattr(client_repo, "get_all") else []
                email_lc = contact["email"].strip().lower()
                for c in clients:
                    if c.email and c.email.strip().lower() == email_lc:
                        db_client = c
                        break
            if db_client and db_client.telegram_id:
                chat_target_user_id = str(db_client.telegram_id)
        except Exception as e:
            print(f"РћС€РёР±РєР° РїРѕРёСЃРєР° РєР»РёРµРЅС‚Р° РІ Р‘Р” РґР»СЏ РІРЅСѓС‚СЂРµРЅРЅРµРіРѕ С‡Р°С‚Р°: {e}")

    text += "\nрџ“ћ <b>Р”Р°РЅРЅС‹Рµ РґР»СЏ СЃРІСЏР·Рё</b>\n"
    text += f"рџ‘¤ <b>РљР»РёРµРЅС‚:</b> {contact['name'] or 'РќРµ СѓРєР°Р·Р°РЅ'}\n"
    text += f"рџ“± <b>РўРµР»РµС„РѕРЅ:</b> {contact['phone'] or 'РќРµ СѓРєР°Р·Р°РЅ'}\n"
    text += f"рџ“§ <b>Email:</b> {contact['email'] or 'РќРµ СѓРєР°Р·Р°РЅ'}\n"
    if not chat_target_user_id:
        text += "вљ пёЏ <i>Р”Р»СЏ СЌС‚РѕРіРѕ Р±СЂРѕРЅРёСЂРѕРІР°РЅРёСЏ РІРЅСѓС‚СЂРµРЅРЅРёР№ С‡Р°С‚ РЅРµРґРѕСЃС‚СѓРїРµРЅ: РЅРµ РЅР°Р№РґРµРЅ Telegram ID РєР»РёРµРЅС‚Р°.</i>\n"

    await callback.message.edit_text(
        text,
        reply_markup=get_admin_booking_detail_keyboard(chat_target_user_id, None),
        parse_mode="HTML"
    )

async def admin_services(callback: CallbackQuery, is_admin: bool):
    """РЈРїСЂР°РІР»РµРЅРёРµ СѓСЃР»СѓРіР°РјРё"""
    if not is_admin:
        await callback.answer("РЈ РІР°СЃ РЅРµС‚ РїСЂР°РІ Р°РґРјРёРЅРёСЃС‚СЂР°С‚РѕСЂР°", show_alert=True)
        return
    
    services = await service_repo.get_all_active()
    
    services_text = "рџ“ё <b>РЈРїСЂР°РІР»РµРЅРёРµ СѓСЃР»СѓРіР°РјРё</b>\n\n"
    for service in services:
        services_text += f"рџ“ё <b>{service.name}</b>\n"
        services_text += f"рџ’° {service.price_min}в‚Ѕ - {service.price_min_weekend}в‚Ѕ\n"
        services_text += f"рџ‘Ґ Р”Рѕ {service.max_num_clients} С‡РµР».\n"
        services_text += f"вЏ° {service.min_duration_minutes} РјРёРЅ.\n"
        services_text += f"рџ“Љ {'вњ… РђРєС‚РёРІРЅР°' if service.is_active else 'вќЊ РќРµР°РєС‚РёРІРЅР°'}\n\n"
    
    await callback.message.edit_text(
        services_text,
        reply_markup=get_services_management_keyboard(),
        parse_mode="HTML"
    )

async def admin_clients(callback: CallbackQuery, is_admin: bool):
    """РЈРїСЂР°РІР»РµРЅРёРµ РєР»РёРµРЅС‚Р°РјРё"""
    if not is_admin:
        await callback.answer("РЈ РІР°СЃ РЅРµС‚ РїСЂР°РІ Р°РґРјРёРЅРёСЃС‚СЂР°С‚РѕСЂР°", show_alert=True)
        return
    
    # РџРѕР»СѓС‡Р°РµРј СЃС‚Р°С‚РёСЃС‚РёРєСѓ РєР»РёРµРЅС‚РѕРІ
    from database import client_repo
    clients = await client_repo.get_all() if hasattr(client_repo, 'get_all') else []
    
    clients_text = "рџ‘Ґ <b>РЈРїСЂР°РІР»РµРЅРёРµ РєР»РёРµРЅС‚Р°РјРё</b>\n\n"
    clients_text += f"рџ“Љ Р’СЃРµРіРѕ РєР»РёРµРЅС‚РѕРІ: {len(clients)}\n\n"
    
    if clients:
        clients_text += "рџ“‹ <b>РџРѕСЃР»РµРґРЅРёРµ РєР»РёРµРЅС‚С‹:</b>\n"
        for client in clients[:5]:  # РџРѕРєР°Р·С‹РІР°РµРј РїРѕСЃР»РµРґРЅРёС… 5
            clients_text += f"рџ‘¤ {client.name}\n"
            if client.telegram_id:
                telegram_label = "РќРµ СѓРєР°Р·Р°РЅ"
                try:
                    chat = await callback.bot.get_chat(client.telegram_id)
                    if chat.username:
                        telegram_label = f"@{chat.username}"
                except Exception as e:
                    print(f"РќРµ СѓРґР°Р»РѕСЃСЊ РїРѕР»СѓС‡РёС‚СЊ username РґР»СЏ client.telegram_id={client.telegram_id}: {e}")
                clients_text += f"   Telegram: {telegram_label}\n"
            if client.phone:
                phone_display = _format_phone_plus7(client.phone)
                clients_text += f"   рџ“ћ {phone_display}\n"
            clients_text += "\n"
    else:
        clients_text += "РљР»РёРµРЅС‚РѕРІ РїРѕРєР° РЅРµС‚."
    
    await callback.message.edit_text(
        clients_text,
        reply_markup=get_admin_keyboard(),
        parse_mode="HTML"
    )

async def admin_admins(callback: CallbackQuery, is_admin: bool):
    """РЈРїСЂР°РІР»РµРЅРёРµ Р°РґРјРёРЅРёСЃС‚СЂР°С‚РѕСЂР°РјРё"""
    if not is_admin:
        await callback.answer("РЈ РІР°СЃ РЅРµС‚ РїСЂР°РІ Р°РґРјРёРЅРёСЃС‚СЂР°С‚РѕСЂР°", show_alert=True)
        return
    
    admins = await admin_repo.get_all()
    
    admins_text = "рџ‘ЁвЂЌрџ’ј <b>РЈРїСЂР°РІР»РµРЅРёРµ Р°РґРјРёРЅРёСЃС‚СЂР°С‚РѕСЂР°РјРё</b>\n\n"
    for admin in admins:
        status = "вњ… РђРєС‚РёРІРµРЅ" if admin.is_active else "вќЊ РќРµР°РєС‚РёРІРµРЅ"
        telegram_label = "РќРµ СѓРєР°Р·Р°РЅ"
        if admin.telegram_id:
            try:
                chat = await callback.bot.get_chat(admin.telegram_id)
                if chat.username:
                    telegram_label = f"@{chat.username}"
            except Exception as e:
                print(f"РќРµ СѓРґР°Р»РѕСЃСЊ РїРѕР»СѓС‡РёС‚СЊ username РґР»СЏ admin.telegram_id={admin.telegram_id}: {e}")

        admins_text += f"рџ‘¤ ID: {admin.id}\n"
        admins_text += f"рџ“± Telegram: {telegram_label}\n"
        admins_text += f"рџ“§ VK: {admin.vk_id or 'РќРµ СѓРєР°Р·Р°РЅ'}\n"
        admins_text += f"рџ“Љ РЎС‚Р°С‚СѓСЃ: {status}\n\n"
    
    await callback.message.edit_text(
        admins_text,
        reply_markup=get_admin_keyboard(),
        parse_mode="HTML"
    )

async def bookings_today(callback: CallbackQuery, is_admin: bool):
    """Р‘СЂРѕРЅРёСЂРѕРІР°РЅРёСЏ РЅР° СЃРµРіРѕРґРЅСЏ"""
    if not is_admin:
        await callback.answer("РЈ РІР°СЃ РЅРµС‚ РїСЂР°РІ Р°РґРјРёРЅРёСЃС‚СЂР°С‚РѕСЂР°", show_alert=True)
        return
    
    today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    tomorrow = today + timedelta(days=1)
    
    if not is_calendar_available():
        await callback.message.edit_text(
            "рџ“… <b>Р‘СЂРѕРЅРёСЂРѕРІР°РЅРёСЏ РЅР° СЃРµРіРѕРґРЅСЏ</b>\n\n"
            "Google Calendar РЅРµРґРѕСЃС‚СѓРїРµРЅ. РџСЂРѕРІРµСЂСЊС‚Рµ РЅР°СЃС‚СЂРѕР№РєРё Рё С‚РѕРєРµРЅС‹.",
            reply_markup=get_bookings_management_keyboard(),
            parse_mode="HTML"
        )
        return

    try:
        events = await svc_list_events(today, tomorrow)
    except Exception as e:
        print(f"РћС€РёР±РєР° РїРѕР»СѓС‡РµРЅРёСЏ СЃРѕР±С‹С‚РёР№ РєР°Р»РµРЅРґР°СЂСЏ: {e}")
        await callback.message.edit_text(
            "рџ“… <b>Р‘СЂРѕРЅРёСЂРѕРІР°РЅРёСЏ РЅР° СЃРµРіРѕРґРЅСЏ</b>\n\n"
            "РќРµ СѓРґР°Р»РѕСЃСЊ РїРѕР»СѓС‡РёС‚СЊ РґР°РЅРЅС‹Рµ РёР· РєР°Р»РµРЅРґР°СЂСЏ.",
            reply_markup=get_bookings_management_keyboard(),
            parse_mode="HTML"
        )
        return

    if not events:
        await callback.message.edit_text(
            "рџ“… <b>Р‘СЂРѕРЅРёСЂРѕРІР°РЅРёСЏ РЅР° СЃРµРіРѕРґРЅСЏ</b>\n\n"
            "РќР° СЃРµРіРѕРґРЅСЏ Р±СЂРѕРЅРёСЂРѕРІР°РЅРёР№ РЅРµС‚.",
            reply_markup=get_bookings_management_keyboard(),
            parse_mode="HTML"
        )
        return

    bookings_text = f"рџ“… <b>Р‘СЂРѕРЅРёСЂРѕРІР°РЅРёСЏ РЅР° СЃРµРіРѕРґРЅСЏ ({today.strftime('%d.%m.%Y')})</b>\n\n"
    for event in events:
        start = event.get("start")
        if not start:
            continue
        summary = event.get("summary", "Р‘РµР· РЅР°Р·РІР°РЅРёСЏ")
        bookings_text += f"рџ•ђ {start.strftime('%H:%M')} вЂ” {summary}\n\n"

    await callback.message.edit_text(
        bookings_text,
        reply_markup=get_bookings_management_keyboard(),
        parse_mode="HTML"
    )

async def bookings_tomorrow(callback: CallbackQuery, is_admin: bool):
    """Р‘СЂРѕРЅРёСЂРѕРІР°РЅРёСЏ РЅР° Р·Р°РІС‚СЂР°"""
    if not is_admin:
        await callback.answer("РЈ РІР°СЃ РЅРµС‚ РїСЂР°РІ Р°РґРјРёРЅРёСЃС‚СЂР°С‚РѕСЂР°", show_alert=True)
        return
    
    tomorrow = (datetime.now() + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
    day_after = tomorrow + timedelta(days=1)
    
    if not is_calendar_available():
        await callback.message.edit_text(
            "рџ“… <b>Р‘СЂРѕРЅРёСЂРѕРІР°РЅРёСЏ РЅР° Р·Р°РІС‚СЂР°</b>\n\n"
            "Google Calendar РЅРµРґРѕСЃС‚СѓРїРµРЅ. РџСЂРѕРІРµСЂСЊС‚Рµ РЅР°СЃС‚СЂРѕР№РєРё Рё С‚РѕРєРµРЅС‹.",
            reply_markup=get_bookings_management_keyboard(),
            parse_mode="HTML"
        )
        return

    try:
        events = await svc_list_events(tomorrow, day_after)
    except Exception as e:
        print(f"РћС€РёР±РєР° РїРѕР»СѓС‡РµРЅРёСЏ СЃРѕР±С‹С‚РёР№ РєР°Р»РµРЅРґР°СЂСЏ: {e}")
        await callback.message.edit_text(
            "рџ“… <b>Р‘СЂРѕРЅРёСЂРѕРІР°РЅРёСЏ РЅР° Р·Р°РІС‚СЂР°</b>\n\n"
            "РќРµ СѓРґР°Р»РѕСЃСЊ РїРѕР»СѓС‡РёС‚СЊ РґР°РЅРЅС‹Рµ РёР· РєР°Р»РµРЅРґР°СЂСЏ.",
            reply_markup=get_bookings_management_keyboard(),
            parse_mode="HTML"
        )
        return

    if not events:
        await callback.message.edit_text(
            "рџ“… <b>Р‘СЂРѕРЅРёСЂРѕРІР°РЅРёСЏ РЅР° Р·Р°РІС‚СЂР°</b>\n\n"
            "РќР° Р·Р°РІС‚СЂР° Р±СЂРѕРЅРёСЂРѕРІР°РЅРёР№ РЅРµС‚.",
            reply_markup=get_bookings_management_keyboard(),
            parse_mode="HTML"
        )
        return

    bookings_text = f"рџ“… <b>Р‘СЂРѕРЅРёСЂРѕРІР°РЅРёСЏ РЅР° Р·Р°РІС‚СЂР° ({tomorrow.strftime('%d.%m.%Y')})</b>\n\n"
    for event in events:
        start = event.get("start")
        if not start:
            continue
        summary = event.get("summary", "Р‘РµР· РЅР°Р·РІР°РЅРёСЏ")
        bookings_text += f"рџ•ђ {start.strftime('%H:%M')} вЂ” {summary}\n\n"

    await callback.message.edit_text(
        bookings_text,
        reply_markup=get_bookings_management_keyboard(),
        parse_mode="HTML"
    )

async def bookings_week(callback: CallbackQuery, is_admin: bool):
    """Р‘СЂРѕРЅРёСЂРѕРІР°РЅРёСЏ РЅР° РЅРµРґРµР»СЋ"""
    if not is_admin:
        await callback.answer("РЈ РІР°СЃ РЅРµС‚ РїСЂР°РІ Р°РґРјРёРЅРёСЃС‚СЂР°С‚РѕСЂР°", show_alert=True)
        return

    today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    week_later = today + timedelta(days=7)

    if not is_calendar_available():
        await callback.message.edit_text(
            "рџ“… <b>Р‘СЂРѕРЅРёСЂРѕРІР°РЅРёСЏ РЅР° РЅРµРґРµР»СЋ</b>\n\n"
            "Google Calendar РЅРµРґРѕСЃС‚СѓРїРµРЅ. РџСЂРѕРІРµСЂСЊС‚Рµ РЅР°СЃС‚СЂРѕР№РєРё Рё С‚РѕРєРµРЅС‹.",
            reply_markup=get_bookings_management_keyboard(),
            parse_mode="HTML"
        )
        return

    try:
        events = await svc_list_events(today, week_later, max_results=100)
    except Exception as e:
        print(f"РћС€РёР±РєР° РїРѕР»СѓС‡РµРЅРёСЏ СЃРѕР±С‹С‚РёР№ РєР°Р»РµРЅРґР°СЂСЏ: {e}")
        await callback.message.edit_text(
            "рџ“… <b>Р‘СЂРѕРЅРёСЂРѕРІР°РЅРёСЏ РЅР° РЅРµРґРµР»СЋ</b>\n\n"
            "РќРµ СѓРґР°Р»РѕСЃСЊ РїРѕР»СѓС‡РёС‚СЊ РґР°РЅРЅС‹Рµ РёР· РєР°Р»РµРЅРґР°СЂСЏ.",
            reply_markup=get_bookings_management_keyboard(),
            parse_mode="HTML"
        )
        return

    if not events:
        await callback.message.edit_text(
            "рџ“… <b>Р‘СЂРѕРЅРёСЂРѕРІР°РЅРёСЏ РЅР° РЅРµРґРµР»СЋ</b>\n\n"
            "РќР° Р±Р»РёР¶Р°Р№С€РёРµ 7 РґРЅРµР№ Р±СЂРѕРЅРёСЂРѕРІР°РЅРёР№ РЅРµС‚.",
            reply_markup=get_bookings_management_keyboard(),
            parse_mode="HTML"
        )
        return

    bookings_text = "рџ“… <b>Р‘СЂРѕРЅРёСЂРѕРІР°РЅРёСЏ РЅР° РЅРµРґРµР»СЋ:</b>\n\n"
    for event in events:
        start = event.get("start")
        if not start:
            continue
        summary = event.get("summary", "Р‘РµР· РЅР°Р·РІР°РЅРёСЏ")
        bookings_text += f"рџ•ђ {start.strftime('%d.%m %H:%M')} вЂ” {summary}\n"

    await callback.message.edit_text(
        bookings_text,
        reply_markup=get_bookings_management_keyboard(),
        parse_mode="HTML"
    )

async def search_bookings(callback: CallbackQuery, state: FSMContext, is_admin: bool):
    """Р—Р°РїСѓСЃРє РїРѕРёСЃРєР° Р±СЂРѕРЅРёСЂРѕРІР°РЅРёР№ РїРѕ С‚РµРєСЃС‚Сѓ"""
    if not is_admin:
        await callback.answer("РЈ РІР°СЃ РЅРµС‚ РїСЂР°РІ Р°РґРјРёРЅРёСЃС‚СЂР°С‚РѕСЂР°", show_alert=True)
        return

    await state.set_state(AdminStates.waiting_for_booking_search_query)
    await callback.message.edit_text(
        "рџ”Ќ <b>РџРѕРёСЃРє Р±СЂРѕРЅРёСЂРѕРІР°РЅРёР№</b>\n\n"
        "Р’РІРµРґРёС‚Рµ С‚РµРєСЃС‚ РґР»СЏ РїРѕРёСЃРєР° (РёРјСЏ, С‚РµР»РµС„РѕРЅ, СѓСЃР»СѓРіР° РёР»Рё С‡Р°СЃС‚СЊ РѕРїРёСЃР°РЅРёСЏ).",
        reply_markup=get_bookings_management_keyboard(),
        parse_mode="HTML"
    )

async def process_search_bookings_query(message: Message, state: FSMContext, is_admin: bool):
    """РџРѕРёСЃРє Р±СЂРѕРЅРёСЂРѕРІР°РЅРёР№ РїРѕ РІРІРµРґРµРЅРЅРѕРјСѓ С‚РµРєСЃС‚Сѓ"""
    if not is_admin:
        await state.clear()
        await message.answer("РЈ РІР°СЃ РЅРµС‚ РїСЂР°РІ Р°РґРјРёРЅРёСЃС‚СЂР°С‚РѕСЂР°")
        return

    query = (message.text or "").strip()
    if len(query) < 2:
        await message.answer("вќЊ Р’РІРµРґРёС‚Рµ РјРёРЅРёРјСѓРј 2 СЃРёРјРІРѕР»Р° РґР»СЏ РїРѕРёСЃРєР°.")
        return

    if not is_calendar_available():
        await state.clear()
        await message.answer(
            "Google Calendar РЅРµРґРѕСЃС‚СѓРїРµРЅ. РџСЂРѕРІРµСЂСЊС‚Рµ РЅР°СЃС‚СЂРѕР№РєРё Рё С‚РѕРєРµРЅС‹.",
            reply_markup=get_bookings_management_keyboard()
        )
        return

    now = datetime.now()
    period_start = now - timedelta(days=30)
    period_end = now + timedelta(days=180)

    try:
        events = await svc_list_events(
            period_start,
            period_end,
            query=query,
            max_results=30
        )
    except Exception as e:
        print(f"РћС€РёР±РєР° РїРѕРёСЃРєР° СЃРѕР±С‹С‚РёР№ РєР°Р»РµРЅРґР°СЂСЏ: {e}")
        await state.clear()
        await message.answer(
            "вќЊ РћС€РёР±РєР° РїРѕРёСЃРєР° РІ РєР°Р»РµРЅРґР°СЂРµ. РџРѕРїСЂРѕР±СѓР№С‚Рµ РїРѕР·Р¶Рµ.",
            reply_markup=get_bookings_management_keyboard()
        )
        return

    if not events:
        await state.clear()
        await message.answer(
            f"рџ”Ќ РџРѕ Р·Р°РїСЂРѕСЃСѓ <b>{query}</b> РЅРёС‡РµРіРѕ РЅРµ РЅР°Р№РґРµРЅРѕ.",
            reply_markup=get_bookings_management_keyboard(),
            parse_mode="HTML"
        )
        return

    result_text = f"рџ”Ќ <b>Р РµР·СѓР»СЊС‚Р°С‚С‹ РїРѕРёСЃРєР°: {query}</b>\n\n"
    for event in events:
        start = event.get("start")
        if not start:
            continue
        summary = event.get("summary", "Р‘РµР· РЅР°Р·РІР°РЅРёСЏ")
        result_text += f"рџ•ђ {start.strftime('%d.%m %H:%M')} вЂ” {summary}\n"

    await state.clear()
    await message.answer(
        result_text,
        reply_markup=get_bookings_management_keyboard(),
        parse_mode="HTML"
    )

async def admin_access_denied(message: Message, is_admin: bool):
    """РћР±СЂР°Р±РѕС‚РєР° РґРѕСЃС‚СѓРїР° Рє Р°РґРјРёРЅ-С„СѓРЅРєС†РёСЏРј"""
    if not is_admin:
        await message.answer(
            "рџ”’ <b>Р”РѕСЃС‚СѓРї Р·Р°РїСЂРµС‰РµРЅ</b>\n\n"
            "РЈ РІР°СЃ РЅРµС‚ РїСЂР°РІ Р°РґРјРёРЅРёСЃС‚СЂР°С‚РѕСЂР°.\n"
            "РћР±СЂР°С‚РёС‚РµСЃСЊ Рє Р°РґРјРёРЅРёСЃС‚СЂР°С‚РѕСЂСѓ РґР»СЏ РїРѕР»СѓС‡РµРЅРёСЏ РґРѕСЃС‚СѓРїР°.",
            reply_markup=get_main_menu_keyboard()
        )

def register_admin_handlers(dp: Dispatcher):
    """Р РµРіРёСЃС‚СЂР°С†РёСЏ РѕР±СЂР°Р±РѕС‚С‡РёРєРѕРІ Р°РґРјРёРЅ-РїР°РЅРµР»Рё"""
    dp.callback_query.register(admin_panel, F.data == "admin_panel")
    dp.callback_query.register(admin_stats, F.data == "admin_stats")
    dp.callback_query.register(admin_bookings, F.data == "admin_bookings")
    dp.callback_query.register(admin_services, F.data == "admin_services")
    dp.callback_query.register(admin_clients, F.data == "admin_clients")
    dp.callback_query.register(admin_admins, F.data == "admin_admins")
    dp.callback_query.register(bookings_today, F.data == "bookings_today")
    dp.callback_query.register(bookings_tomorrow, F.data == "bookings_tomorrow")
    dp.callback_query.register(bookings_week, F.data == "bookings_week")
    dp.callback_query.register(search_bookings, F.data == "search_bookings")
    dp.callback_query.register(admin_booking_open, F.data.startswith("admin_booking_open_"))
    dp.message.register(process_search_bookings_query, AdminStates.waiting_for_booking_search_query)



