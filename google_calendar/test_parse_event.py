#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Тестовый файл для проверки методов парсинга событий календаря
"""

import asyncio
import sys
from datetime import datetime
from google_calendar.calendar_service import GoogleCalendarService

# Устанавливаем кодировку UTF-8 для Windows консоли
if sys.platform == 'win32':
    import os
    import io
    os.environ['PYTHONIOENCODING'] = 'utf-8'
    try:
        if hasattr(sys.stdout, 'buffer') and not isinstance(sys.stdout, io.TextIOWrapper):
            sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
        if hasattr(sys.stderr, 'buffer') and not isinstance(sys.stderr, io.TextIOWrapper):
            sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')
    except (AttributeError, ValueError, TypeError):
        pass


def test_parse_event_description():
    """Тест парсинга описания события"""
    print("=" * 80)
    print("ТЕСТ: parse_event_description")
    print("=" * 80)
    
    service = GoogleCalendarService()
    
    # Пример описания события с HTML-разметкой
    test_description = """
<b>Кто забронировал</b>
Иван Иванов
email: ivan@example.com
+7 (999) 123-45-67

<b>Какой зал вы хотите забронировать?</b>
Большой зал

<b>Какое количество гостейпланируется, включая фотографа?</b>
5

<b>Нужна ли гримерная за час до съемки?</b>
Да

<b>Нужен ли фотограф?</b> 
Нет

<b><u>ВНИМАНИЕ</u></b> Автоматически на вашу электронную почту приходит подтверждение о <b><u>предварительном бронировании времени</u></b><u>.</u> Вам нужно:

<ul><li>дождаться информации о предоплате</li><li>отправить нам скриншот оплаты в течение 24-х часов</li><li>получить от нас подтверждение, что желаемая дата и время забронировано.</li></ul>

Бронируя фотостудию, Вы соглашаетесь с <a href="https://example.com">Правилами аренды фотостудии</a>
    """.strip()
    
    print("\n[INFO] Исходное описание:")
    print(test_description[:200] + "...")
    
    # Парсим описание
    result = service.parse_event_description(test_description)
    
    print("\n[OK] Результат парсинга:")
    for key, value in result.items():
        print(f"  {key}: {value}")
    
    # Проверяем результаты
    assert result.get('name') == 'Иван Иванов', f"Ожидалось 'Иван Иванов', получено '{result.get('name')}'"
    assert result.get('email') == 'ivan@example.com', f"Ожидалось 'ivan@example.com', получено '{result.get('email')}'"
    assert result.get('phone') == '+7 (999) 123-45-67', f"Ожидалось '+7 (999) 123-45-67', получено '{result.get('phone')}'"
    assert result.get('service_name') == 'Большой зал', f"Ожидалось 'Большой зал', получено '{result.get('service_name')}'"
    assert result.get('guests_count') == '5', f"Ожидалось '5', получено '{result.get('guests_count')}'"
    assert result.get('makeuproom') == 'Да', f"Ожидалось 'Да', получено '{result.get('makeuproom')}'"
    assert result.get('need_photographer') == 'Нет', f"Ожидалось 'Нет', получено '{result.get('need_photographer')}'"
    
    print("\n[OK] Все проверки пройдены!")
    
    # Тест с пустым описанием
    print("\n" + "-" * 80)
    print("ТЕСТ: Пустое описание")
    print("-" * 80)
    empty_result = service.parse_event_description("")
    assert empty_result == {}, f"Ожидался пустой словарь, получено: {empty_result}"
    print("[OK] Пустое описание обработано корректно")
    
    # Тест с частичными данными
    print("\n" + "-" * 80)
    print("ТЕСТ: Частичные данные")
    print("-" * 80)
    partial_description = """
<b>Кто забронировал</b>
Мария Петрова
email: не указан

<b>Какой зал вы хотите забронировать?</b>
Малый зал
    """.strip()
    
    partial_result = service.parse_event_description(partial_description)
    print("[OK] Результат парсинга частичных данных:")
    for key, value in partial_result.items():
        print(f"  {key}: {value}")
    
    assert partial_result.get('name') == 'Мария Петрова'
    assert partial_result.get('email') == 'не указан'
    assert partial_result.get('service_name') == 'Малый зал'
    print("[OK] Частичные данные обработаны корректно")


def test_parse_event():
    """Тест парсинга полного события"""
    print("\n" + "=" * 80)
    print("ТЕСТ: parse_event")
    print("=" * 80)
    
    service = GoogleCalendarService()
    
    # Пример события из Google Calendar API
    test_event = {
        'id': 'test_event_123',
        'summary': 'Фотосессия: Большой зал',
        'start': {
            'dateTime': '2024-12-25T14:00:00+03:00',
            'timeZone': 'Europe/Moscow'
        },
        'end': {
            'dateTime': '2024-12-25T15:00:00+03:00',
            'timeZone': 'Europe/Moscow'
        },
        'description': """
<b>Кто забронировал</b>
Анна Сидорова
email: anna@example.com
+7 (999) 987-65-43

<b>Какой зал вы хотите забронировать?</b>
Большой зал

<b>Какое количество гостейпланируется, включая фотографа?</b>
3

<b>Нужна ли гримерная за час до съемки?</b>
Нет

<b>Нужен ли фотограф?</b> 
Да
        """.strip(),
        'location': 'Фотостудия RONA',
        'status': 'confirmed'
    }
    
    print("\n[INFO] Исходное событие:")
    print(f"  ID: {test_event['id']}")
    print(f"  Название: {test_event['summary']}")
    print(f"  Начало: {test_event['start']['dateTime']}")
    print(f"  Конец: {test_event['end']['dateTime']}")
    
    # Парсим событие
    result = service.parse_event(test_event)
    
    print("\n[OK] Результат парсинга:")
    print(f"  id: {result['id']}")
    print(f"  title: {result['title']}")
    print(f"  start: {result['start']}")
    print(f"  end: {result['end']}")
    print(f"  location: {result['location']}")
    print(f"  status: {result['status']}")
    print("\n  Данные бронирования:")
    for key, value in result['booking_data'].items():
        print(f"    {key}: {value}")
    
    # Проверяем результаты
    assert result['id'] == 'test_event_123'
    assert result['title'] == 'Фотосессия: Большой зал'
    assert result['start'] == '2024-12-25T14:00:00+03:00'
    assert result['end'] == '2024-12-25T15:00:00+03:00'
    assert result['location'] == 'Фотостудия RONA'
    assert result['status'] == 'confirmed'
    assert result['booking_data']['name'] == 'Анна Сидорова'
    assert result['booking_data']['email'] == 'anna@example.com'
    assert result['booking_data']['phone'] == '+7 (999) 987-65-43'
    
    print("\n[OK] Все проверки пройдены!")
    
    # Тест с пустым событием
    print("\n" + "-" * 80)
    print("ТЕСТ: Пустое событие")
    print("-" * 80)
    empty_result = service.parse_event({})
    assert empty_result['id'] is None
    assert empty_result['title'] == ''
    assert empty_result['booking_data'] == {}
    print("[OK] Пустое событие обработано корректно")
    
    # Тест с событием без времени (только дата)
    print("\n" + "-" * 80)
    print("ТЕСТ: Событие с датой без времени")
    print("-" * 80)
    date_only_event = {
        'id': 'date_event_123',
        'summary': 'Событие на весь день',
        'start': {
            'date': '2024-12-25'
        },
        'end': {
            'date': '2024-12-26'
        },
        'description': 'Описание события'
    }
    
    date_result = service.parse_event(date_only_event)
    assert date_result['start'] == '2024-12-25'
    assert date_result['end'] == '2024-12-26'
    print(f"[OK] Событие с датой обработано: {date_result['start']} - {date_result['end']}")


def test_edge_cases():
    """Тест граничных случаев"""
    print("\n" + "=" * 80)
    print("ТЕСТ: Граничные случаи")
    print("=" * 80)
    
    service = GoogleCalendarService()
    
    # Тест с None
    print("\n1. Тест с None:")
    none_result = service.parse_event(None)
    assert none_result['id'] is None
    print("   [OK] None обработан корректно")
    
    # Тест с минимальным описанием
    print("\n2. Тест с минимальным описанием:")
    minimal_desc = "Кто забронировал\nТест Тестов"
    minimal_result = service.parse_event_description(minimal_desc)
    assert minimal_result.get('name') == 'Тест Тестов'
    print(f"   [OK] Извлечено имя: {minimal_result.get('name')}")
    
    # Тест с HTML без данных
    print("\n3. Тест с HTML без данных:")
    html_only = "<b>Тест</b><br><p>Текст</p>"
    html_result = service.parse_event_description(html_only)
    print(f"   [OK] HTML обработан, результат: {len(html_result)} полей")
    
    print("\n[OK] Все граничные случаи обработаны корректно!")


def main():
    """Запуск всех тестов"""
    print("\n" + "=" * 80)
    print("ЗАПУСК ТЕСТОВ ПАРСИНГА СОБЫТИЙ КАЛЕНДАРЯ")
    print("=" * 80 + "\n")
    
    try:
        test_parse_event_description()
        test_parse_event()
        test_edge_cases()
        
        print("\n" + "=" * 80)
        print("[OK] ВСЕ ТЕСТЫ УСПЕШНО ПРОЙДЕНЫ!")
        print("=" * 80 + "\n")
        
    except AssertionError as e:
        print(f"\n[ERROR] ОШИБКА ТЕСТА: {e}\n")
        raise
    except Exception as e:
        print(f"\n[ERROR] НЕОЖИДАННАЯ ОШИБКА: {e}\n")
        raise


if __name__ == "__main__":
    main()

