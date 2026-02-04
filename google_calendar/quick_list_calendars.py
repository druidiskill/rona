#!/usr/bin/env python3
"""
Простой скрипт для быстрого получения списка календарей Google Calendar
"""

import asyncio
from google_calendar.calendar_service import GoogleCalendarService

async def quick_list_calendars():
    """Быстрое получение списка календарей"""
    try:
        calendar_service = GoogleCalendarService()
        await calendar_service.authenticate()
        service = await calendar_service.get_service()
        
        if not service:
            print("❌ Ошибка подключения к Google Calendar")
            return
        
        # Получаем список календарей
        calendar_list = service.calendarList().list().execute()
        calendars = calendar_list.get('items', [])
        
        print(f"📅 Найдено календарей: {len(calendars)}")
        print("-" * 50)
        
        for calendar in calendars:
            calendar_id = calendar.get('id', 'N/A')
            summary = calendar.get('summary', 'Без названия')
            primary = "⭐" if calendar.get('primary') else "  "
            selected = "✅" if calendar.get('selected') else "  "
            
            print(f"{primary} {selected} {summary}")
            print(f"    ID: {calendar_id}")
        
        # Показываем основной календарь
        primary_calendar = next((cal for cal in calendars if cal.get('primary')), None)
        if primary_calendar:
            print(f"\n⭐ Основной календарь: {primary_calendar.get('summary')}")
            print(f"🆔 ID: {primary_calendar.get('id')}")
        
    except Exception as e:
        print(f"❌ Ошибка: {e}")

if __name__ == "__main__":
    asyncio.run(quick_list_calendars())

