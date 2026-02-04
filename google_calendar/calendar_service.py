# -*- coding: utf-8 -*-
import os
import asyncio
import re
import sys
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import json

# Устанавливаем кодировку UTF-8 для Windows консоли
if sys.platform == 'win32':
    import io
    try:
        # Устанавливаем кодировку через переменную окружения
        os.environ['PYTHONIOENCODING'] = 'utf-8'
        # Пытаемся установить кодировку для stdout/stderr если они еще не установлены
        if hasattr(sys.stdout, 'buffer') and not isinstance(sys.stdout, io.TextIOWrapper):
            sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
        if hasattr(sys.stderr, 'buffer') and not isinstance(sys.stderr, io.TextIOWrapper):
            sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')
    except (AttributeError, ValueError, TypeError):
        # Если не удалось установить, используем переменную окружения
        os.environ['PYTHONIOENCODING'] = 'utf-8'

class GoogleCalendarService:
    """Сервис для работы с Google Calendar API"""
    
    SCOPES = ['https://www.googleapis.com/auth/calendar']
    CREDENTIALS_FILE = 'google_calendar/credentials.json'
    TOKEN_FILE = 'google_calendar/token.json'
    
    def __init__(self):
        self.service = None
        self.credentials = None
    
    async def get_service(self):
        """Получение сервиса Google Calendar"""
        if not self.service:
            await self.authenticate()
        return self.service

    async def authenticate(self) -> bool:
        """Аутентификация в Google Calendar API"""
        try:
            # Загружаем сохраненные учетные данные
            if os.path.exists(self.TOKEN_FILE):
                self.credentials = Credentials.from_authorized_user_file(
                    self.TOKEN_FILE, self.SCOPES
                )
            
            # Если нет действительных учетных данных, запрашиваем авторизацию
            if not self.credentials or not self.credentials.valid:
                if self.credentials and self.credentials.expired and self.credentials.refresh_token:
                    self.credentials.refresh(Request())
                else:
                    if not os.path.exists(self.CREDENTIALS_FILE):
                        print(f"[ERROR] Файл {self.CREDENTIALS_FILE} не найден!")
                        print("[INFO] Создайте файл credentials.json в папке google_calendar/")
                        return False
                    
                    flow = InstalledAppFlow.from_client_secrets_file(
                        self.CREDENTIALS_FILE, self.SCOPES
                    )
                    self.credentials = flow.run_local_server(port=0)
                
                # Сохраняем учетные данные для следующего запуска
                with open(self.TOKEN_FILE, 'w') as token:
                    token.write(self.credentials.to_json())
            
            # Создаем сервис
            self.service = build('calendar', 'v3', credentials=self.credentials)
            print("[OK] Google Calendar API подключен успешно!")
            return True
            
        except Exception as e:
            print(f"[ERROR] Ошибка аутентификации Google Calendar: {e}")
            return False
    
    async def get_calendar_events(self, calendar_id: str = 'primary', 
                                 start_date: datetime = None, 
                                 end_date: datetime = None) -> List[Dict[str, Any]]:
        """Получение событий из календаря"""
        if not self.service:
            await self.authenticate()
        
        if not self.service:
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
            
            # Получаем события
            events_result = self.service.events().list(
                calendarId=calendar_id,
                timeMin=time_min,
                timeMax=time_max,
                singleEvents=True,
                orderBy='startTime'
            ).execute()
            
            events = events_result.get('items', [])
            
            # Форматируем события
            formatted_events = []
            for event in events:
                start = event['start'].get('dateTime', event['start'].get('date'))
                end = event['end'].get('dateTime', event['end'].get('date'))
                
                formatted_events.append({
                    'id': event.get('id'),
                    'summary': event.get('summary', 'Без названия'),
                    'start': start,
                    'end': end,
                    'description': event.get('description', ''),
                    'location': event.get('location', ''),
                    'status': event.get('status', 'confirmed')
                })
            
            return formatted_events
            
        except HttpError as e:
            print(f"[ERROR] Ошибка Google Calendar API: {e}")
            return []
        except Exception as e:
            print(f"[ERROR] Ошибка получения событий: {e}")
            return []
    
    async def check_time_availability(self, start_time: datetime, 
                                    end_time: datetime, 
                                    calendar_id: str = 'primary') -> bool:
        """Проверка доступности времени"""
        events = await self.get_calendar_events(
            calendar_id=calendar_id,
            start_date=start_time,
            end_date=end_time
        )
        
        # Проверяем пересечения
        for event in events:
            event_start = datetime.fromisoformat(event['start'].replace('Z', '+00:00'))
            event_end = datetime.fromisoformat(event['end'].replace('Z', '+00:00'))
            
            # Проверяем пересечение временных интервалов
            if (start_time < event_end and end_time > event_start):
                return False
        
        return True
    
    async def get_free_slots(self, date: datetime, 
                           duration_minutes: int = 60,
                           calendar_id: str = 'primary') -> List[Dict[str, datetime]]:
        """Получение свободных слотов на день"""
        # Преобразуем date в datetime если нужно
        if hasattr(date, 'date'):  # Если это datetime объект
            date_obj = date.date()
        else:  # Если это date объект
            date_obj = date
            
        start_of_day = datetime.combine(date_obj, datetime.min.time().replace(hour=9, minute=0, second=0, microsecond=0))
        end_of_day = datetime.combine(date_obj, datetime.min.time().replace(hour=21, minute=0, second=0, microsecond=0))
        
        events = await self.get_calendar_events(
            calendar_id=calendar_id,
            start_date=start_of_day,
            end_date=end_of_day
        )
        
        # Создаем список занятых интервалов
        busy_slots = []
        for event in events:
            event_start = datetime.fromisoformat(event['start'].replace('Z', '+00:00'))
            event_end = datetime.fromisoformat(event['end'].replace('Z', '+00:00'))
            busy_slots.append((event_start, event_end))
        
        # Сортируем по времени начала
        busy_slots.sort(key=lambda x: x[0])
        
        # Находим свободные слоты и разбиваем их на часовые интервалы
        free_slots = []
        current_time = start_of_day
        
        for busy_start, busy_end in busy_slots:
            # Приводим к naive datetime для сравнения
            busy_start_naive = busy_start.replace(tzinfo=None) if busy_start.tzinfo else busy_start
            busy_end_naive = busy_end.replace(tzinfo=None) if busy_end.tzinfo else busy_end
            
            # Если есть свободное время до занятого слота
            if current_time + timedelta(minutes=duration_minutes) <= busy_start_naive:
                # Разбиваем свободный интервал на часовые слоты
                slot_start = current_time
                while slot_start + timedelta(minutes=duration_minutes) <= busy_start_naive:
                    free_slots.append({
                        'start': slot_start,
                        'end': slot_start + timedelta(minutes=duration_minutes)
                    })
                    slot_start += timedelta(minutes=duration_minutes)
            
            # Обновляем текущее время
            current_time = max(current_time, busy_end_naive)
        
        # Проверяем время после последнего события
        if current_time + timedelta(minutes=duration_minutes) <= end_of_day:
            # Разбиваем оставшийся интервал на часовые слоты
            slot_start = current_time
            while slot_start + timedelta(minutes=duration_minutes) <= end_of_day:
                free_slots.append({
                    'start': slot_start,
                    'end': slot_start + timedelta(minutes=duration_minutes)
                })
                slot_start += timedelta(minutes=duration_minutes)
        
        return free_slots

    async def create_event(self, title: str, description: str, start_time: datetime, 
                          end_time: datetime, calendar_id: str = 'primary') -> dict:
        """Создание события в календаре"""
        try:
            service = await self.get_service()
            
            if not service:
                raise Exception("Google Calendar сервис не доступен")
            
            event = {
                'summary': title,
                'description': description,
                'start': {
                    'dateTime': start_time.isoformat(),
                    'timeZone': 'Europe/Moscow',
                },
                'end': {
                    'dateTime': end_time.isoformat(),
                    'timeZone': 'Europe/Moscow',
                },
            }
            
            # Обертываем синхронный execute() в asyncio.to_thread для избежания блокировки
            import asyncio
            loop = asyncio.get_event_loop()
            created_event = await loop.run_in_executor(
                None,
                lambda: service.events().insert(
                calendarId=calendar_id,
                body=event
            ).execute()
            )
            
            print(f"[OK] Событие создано: {created_event.get('htmlLink')}")
            return created_event
            
        except Exception as e:
            import traceback
            print(f"[ERROR] Ошибка создания события: {e}")
            print(f"[INFO] Детали:\n{traceback.format_exc()}")
            raise e

    def parse_event_description(self, description: str) -> Dict[str, Any]:
        """
        Парсинг описания события для извлечения информации о бронировании
        
        Args:
            description: Описание события из календаря (может содержать HTML)
            
        Returns:
            Словарь с распарсенными данными:
            {
                'name': str - имя клиента,
                'email': str - email клиента,
                'phone': str - телефон клиента,
                'service_name': str - название зала/услуги,
                'guests_count': str - количество гостей,
                'makeuproom': str - нужна ли гримерная,
                'need_photographer': str - нужен ли фотограф
            }
        """
        if not description:
            return {}
        
        # Удаляем HTML-теги для упрощения парсинга
        # Заменяем <br> и </br> на переносы строк
        text = re.sub(r'<br\s*/?>', '\n', description, flags=re.IGNORECASE)
        # Удаляем остальные HTML-теги
        text = re.sub(r'<[^>]+>', '', text)
        # Удаляем множественные пробелы и переносы
        text = re.sub(r'\n\s*\n', '\n', text)
        text = text.strip()
        
        parsed_data = {}
        
        try:
            # Парсим имя (идет после "Кто забронировал" на следующей строке)
            name_match = re.search(r'Кто забронировал\s*\n([^\n]+)', text, re.IGNORECASE)
            if name_match:
                parsed_data['name'] = name_match.group(1).strip()
            
            # Парсим email
            email_match = re.search(r'email:\s*([^\n]+)', text, re.IGNORECASE)
            if email_match:
                parsed_data['email'] = email_match.group(1).strip()
            
            # Парсим телефон (идет после email на следующей строке, до следующего заголовка)
            # Ищем строку после email, которая не является заголовком
            phone_match = re.search(r'email:[^\n]+\n([^\n]+)', text, re.IGNORECASE)
            if phone_match:
                phone = phone_match.group(1).strip()
                # Проверяем, что это не следующий заголовок и не пустая строка
                if phone and not phone.startswith('Какой зал') and not phone.startswith('Какое количество'):
                    parsed_data['phone'] = phone
            
            # Парсим название зала
            service_match = re.search(r'Какой зал вы хотите забронировать\?\s*\n([^\n]+)', text, re.IGNORECASE)
            if service_match:
                parsed_data['service_name'] = service_match.group(1).strip()
            
            # Парсим количество гостей
            guests_match = re.search(r'Какое количество гостей[^\n]*\s*\n([^\n]+)', text, re.IGNORECASE)
            if guests_match:
                parsed_data['guests_count'] = guests_match.group(1).strip()
            
            # Парсим гримерную
            makeuproom_match = re.search(r'Нужна ли гримерная за час до съемки\?\s*\n([^\n]+)', text, re.IGNORECASE)
            if makeuproom_match:
                parsed_data['makeuproom'] = makeuproom_match.group(1).strip()
            
            # Парсим фотографа
            photographer_match = re.search(r'Нужен ли фотограф\?\s*\n([^\n]+)', text, re.IGNORECASE)
            if photographer_match:
                parsed_data['need_photographer'] = photographer_match.group(1).strip()
                
        except Exception as e:
            print(f"[WARNING] Ошибка парсинга описания события: {e}")
        
        return parsed_data

    def parse_event(self, event: Dict[str, Any]) -> Dict[str, Any]:
        """
        Парсинг полного события календаря с извлечением информации о бронировании
        
        Args:
            event: Словарь события из Google Calendar API
            
        Returns:
            Словарь с полной информацией о событии:
            {
                'id': str - ID события,
                'title': str - название события,
                'start': str - время начала,
                'end': str - время окончания,
                'description': str - полное описание,
                'location': str - местоположение,
                'status': str - статус события,
                'booking_data': dict - распарсенные данные бронирования
            }
        """
        if not event:
            return {
                'id': None,
                'title': '',
                'start': '',
                'end': '',
                'description': '',
                'location': '',
                'status': 'confirmed',
                'booking_data': {}
            }
        
        # Извлекаем время начала и окончания
        start_data = event.get('start', {})
        start_time = start_data.get('dateTime') or start_data.get('date', '')
        
        end_data = event.get('end', {})
        end_time = end_data.get('dateTime') or end_data.get('date', '')
        
        parsed_event = {
            'id': event.get('id'),
            'title': event.get('summary', ''),
            'start': start_time,
            'end': end_time,
            'description': event.get('description', ''),
            'location': event.get('location', ''),
            'status': event.get('status', 'confirmed'),
            'booking_data': {}
        }
        
        # Парсим описание для извлечения данных бронирования
        description = event.get('description', '')
        if description:
            parsed_event['booking_data'] = self.parse_event_description(description)
        
        return parsed_event

# Глобальный экземпляр сервиса
calendar_service = GoogleCalendarService()

async def get_calendar_service() -> GoogleCalendarService:
    """Получение экземпляра сервиса календаря"""
    if not calendar_service.service:
        await calendar_service.authenticate()
    return calendar_service