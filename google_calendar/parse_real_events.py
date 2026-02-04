#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Скрипт для получения и парсинга реальных событий из Google Calendar
"""

import asyncio
import os
import sys
from datetime import datetime, timedelta
import json

# Устанавливаем кодировку UTF-8 для Windows консоли
if sys.platform == 'win32':
    import io
    os.environ['PYTHONIOENCODING'] = 'utf-8'
    try:
        if hasattr(sys.stdout, 'buffer') and not isinstance(sys.stdout, io.TextIOWrapper):
            sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
        if hasattr(sys.stderr, 'buffer') and not isinstance(sys.stderr, io.TextIOWrapper):
            sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')
    except (AttributeError, ValueError, TypeError):
        pass

# Добавляем путь к корневой директории проекта
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from google_calendar.calendar_service import GoogleCalendarService


async def get_raw_events(calendar_service: GoogleCalendarService, 
                        calendar_id: str = 'primary',
                        start_date: datetime = None,
                        end_date: datetime = None):
    """Получение сырых событий из календаря (без форматирования)"""
    if not calendar_service.service:
        await calendar_service.authenticate()
    
    if not calendar_service.service:
        return []
    
    try:
        # Устанавливаем даты по умолчанию
        if not start_date:
            start_date = datetime.now()
        if not end_date:
            end_date = start_date + timedelta(days=30)
        
        # Форматируем даты для API
        time_min = start_date.isoformat() + 'Z'
        time_max = end_date.isoformat() + 'Z'
        
        # Получаем события (сырые, без форматирования)
        events_result = calendar_service.service.events().list(
            calendarId=calendar_id,
            timeMin=time_min,
            timeMax=time_max,
            singleEvents=True,
            orderBy='startTime'
        ).execute()
        
        return events_result.get('items', [])
        
    except Exception as e:
        print(f"[ERROR] Ошибка получения событий: {e}")
        return []


async def parse_real_events():
    """Получение и парсинг реальных событий из календаря"""
    print("=" * 80)
    print("ПАРСИНГ РЕАЛЬНЫХ СОБЫТИЙ ИЗ GOOGLE CALENDAR")
    print("=" * 80)
    
    # Создаем экземпляр сервиса
    calendar_service = GoogleCalendarService()
    
    # Аутентифицируемся
    print("\n[INFO] Подключение к Google Calendar API...")
    auth_success = await calendar_service.authenticate()
    
    if not auth_success:
        print("[ERROR] Ошибка аутентификации!")
        print("[INFO] Убедитесь, что файл google_calendar/credentials.json существует")
        return
    
    print("[OK] Успешная аутентификация!")
    
    # Получаем сырые события
    print("\n[INFO] Получение событий из календаря...")
    raw_events = await get_raw_events(calendar_service)
    
    if not raw_events:
        print("[INFO] События не найдены в календаре")
        return
    
    print(f"[OK] Найдено событий: {len(raw_events)}")
    print("=" * 80)
    
    # Парсим каждое событие
    parsed_events = []
    for i, raw_event in enumerate(raw_events, 1):
        print(f"\n--- Событие {i}/{len(raw_events)} ---")
        print(f"ID: {raw_event.get('id', 'N/A')}")
        print(f"Название: {raw_event.get('summary', 'Без названия')}")
        
        # Парсим событие
        parsed_event = calendar_service.parse_event(raw_event)
        
        # Выводим основную информацию
        print(f"Начало: {parsed_event['start']}")
        print(f"Конец: {parsed_event['end']}")
        print(f"Местоположение: {parsed_event.get('location', 'Не указано')}")
        print(f"Статус: {parsed_event['status']}")
        
        # Выводим распарсенные данные бронирования
        booking_data = parsed_event.get('booking_data', {})
        if booking_data:
            print("\n[OK] Данные бронирования найдены:")
            print("  " + "-" * 76)
            for key, value in booking_data.items():
                print(f"  {key:20s}: {value}")
        else:
            print("\n[INFO] Данные бронирования не найдены (возможно, это не событие бронирования)")
            # Показываем начало описания для отладки
            description = parsed_event.get('description', '')
            if description:
                desc_preview = description[:100].replace('\n', ' ')
                print(f"  Описание (начало): {desc_preview}...")
        
        parsed_events.append(parsed_event)
        print("-" * 80)
    
    # Сводная статистика
    print("\n" + "=" * 80)
    print("СВОДНАЯ СТАТИСТИКА")
    print("=" * 80)
    
    events_with_booking = sum(1 for e in parsed_events if e.get('booking_data'))
    events_without_booking = len(parsed_events) - events_with_booking
    
    print(f"Всего событий: {len(parsed_events)}")
    print(f"С событиями бронирования: {events_with_booking}")
    print(f"Без данных бронирования: {events_without_booking}")
    
    # Детальная статистика по полям бронирования
    if events_with_booking > 0:
        print("\n[INFO] Статистика по полям бронирования:")
        fields_stats = {}
        for event in parsed_events:
            booking_data = event.get('booking_data', {})
            for key in booking_data.keys():
                fields_stats[key] = fields_stats.get(key, 0) + 1
        
        for field, count in sorted(fields_stats.items()):
            print(f"  {field:20s}: найдено в {count} событиях")
    
    # Сохраняем результаты в JSON файл
    output_file = 'google_calendar/parsed_events.json'
    try:
        # Преобразуем datetime объекты в строки для JSON
        json_data = []
        for event in parsed_events:
            json_event = event.copy()
            json_data.append(json_event)
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(json_data, f, ensure_ascii=False, indent=2)
        
        print(f"\n[OK] Результаты сохранены в файл: {output_file}")
    except Exception as e:
        print(f"\n[ERROR] Ошибка сохранения в JSON: {e}")
    
    return parsed_events


async def main():
    """Главная функция"""
    try:
        await parse_real_events()
    except KeyboardInterrupt:
        print("\n[INFO] Прервано пользователем")
    except Exception as e:
        print(f"\n[ERROR] Неожиданная ошибка: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())

