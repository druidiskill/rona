#!/usr/bin/env python3
"""
Скрипт для получения списка календарей из Google Calendar API
"""

import asyncio
import os
import sys
from datetime import datetime

# Добавляем путь к корневой директории проекта
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from google_calendar.calendar_service import GoogleCalendarService

async def list_calendars():
    """Получение и отображение списка календарей"""
    try:
        # Создаем экземпляр сервиса
        calendar_service = GoogleCalendarService()
        
        # Аутентифицируемся
        print("🔐 Подключение к Google Calendar API...")
        auth_success = await calendar_service.authenticate()
        
        if not auth_success:
            print("❌ Ошибка аутентификации!")
            print("📝 Убедитесь, что файл google_calendar/credentials.json существует")
            return False
        
        print("✅ Успешная аутентификация!")
        
        # Получаем сервис
        service = await calendar_service.get_service()
        
        if not service:
            print("❌ Не удалось получить сервис Google Calendar")
            return False
        
        print("\n📅 Получение списка календарей...")
        
        # Получаем список календарей
        calendar_list = service.calendarList().list().execute()
        calendars = calendar_list.get('items', [])
        
        if not calendars:
            print("📭 Календари не найдены")
            return True
        
        print(f"\n📋 Найдено календарей: {len(calendars)}")
        print("=" * 80)
        
        for i, calendar in enumerate(calendars, 1):
            calendar_id = calendar.get('id', 'N/A')
            summary = calendar.get('summary', 'Без названия')
            description = calendar.get('description', '')
            timezone = calendar.get('timeZone', 'N/A')
            access_role = calendar.get('accessRole', 'N/A')
            primary = calendar.get('primary', False)
            selected = calendar.get('selected', False)
            
            print(f"\n{i}. 📅 {summary}")
            print(f"   🆔 ID: {calendar_id}")
            print(f"   🌍 Часовой пояс: {timezone}")
            print(f"   🔐 Роль доступа: {access_role}")
            
            if description:
                print(f"   📝 Описание: {description}")
            
            if primary:
                print(f"   ⭐ Основной календарь")
            
            if selected:
                print(f"   ✅ Выбран для отображения")
            
            # Информация о цвете
            color_id = calendar.get('colorId')
            if color_id:
                print(f"   🎨 Цвет: {color_id}")
            
            # Информация о синхронизации
            hidden = calendar.get('hidden', False)
            if hidden:
                print(f"   👁️ Скрыт")
            
            print("-" * 40)
        
        # Показываем основную информацию
        primary_calendar = next((cal for cal in calendars if cal.get('primary')), None)
        if primary_calendar:
            print(f"\n⭐ Основной календарь: {primary_calendar.get('summary')}")
            print(f"🆔 ID основного календаря: {primary_calendar.get('id')}")
        
        return True
        
    except Exception as e:
        print(f"❌ Ошибка при получении календарей: {e}")
        return False

async def get_calendar_details(calendar_id: str):
    """Получение детальной информации о конкретном календаре"""
    try:
        calendar_service = GoogleCalendarService()
        await calendar_service.authenticate()
        service = await calendar_service.get_service()
        
        if not service:
            print("❌ Не удалось получить сервис Google Calendar")
            return False
        
        print(f"\n🔍 Получение информации о календаре: {calendar_id}")
        
        # Получаем информацию о календаре
        calendar_info = service.calendars().get(calendarId=calendar_id).execute()
        
        print("\n📋 Детальная информация о календаре:")
        print("=" * 50)
        print(f"📅 Название: {calendar_info.get('summary', 'N/A')}")
        print(f"🆔 ID: {calendar_info.get('id', 'N/A')}")
        print(f"📝 Описание: {calendar_info.get('description', 'N/A')}")
        print(f"🌍 Часовой пояс: {calendar_info.get('timeZone', 'N/A')}")
        print(f"📍 Местоположение: {calendar_info.get('location', 'N/A')}")
        
        # Информация о доступе
        access_role = calendar_info.get('accessRole', 'N/A')
        print(f"🔐 Роль доступа: {access_role}")
        
        # Информация о правах
        conference_properties = calendar_info.get('conferenceProperties', {})
        if conference_properties:
            print(f"📞 Поддержка конференций: {conference_properties.get('allowedConferenceSolutionTypes', [])}")
        
        return True
        
    except Exception as e:
        print(f"❌ Ошибка при получении информации о календаре: {e}")
        return False

def print_usage():
    """Вывод справки по использованию"""
    print("""
📅 Google Calendar List - Получение списка календарей

Использование:
    python list_calendars.py                    # Показать все календари
    python list_calendars.py <calendar_id>     # Показать детали календаря
    python list_calendars.py --help            # Показать эту справку

Примеры:
    python list_calendars.py
    python list_calendars.py primary
    python list_calendars.py your-email@gmail.com

Требования:
    - Файл google_calendar/credentials.json должен существовать
    - Необходима аутентификация через Google OAuth2
    """)

async def main():
    """Главная функция"""
    if len(sys.argv) > 1:
        if sys.argv[1] in ['--help', '-h', 'help']:
            print_usage()
            return
        
        # Получаем детали конкретного календаря
        calendar_id = sys.argv[1]
        await get_calendar_details(calendar_id)
    else:
        # Получаем список всех календарей
        await list_calendars()

if __name__ == "__main__":
    print("🚀 Запуск скрипта получения календарей Google Calendar")
    print(f"⏰ Время запуска: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n⏹️ Скрипт прерван пользователем")
    except Exception as e:
        print(f"\n❌ Неожиданная ошибка: {e}")
    
    print("\n✅ Скрипт завершен")
