# -*- coding: utf-8 -*-
"""
Единый модуль для работы со свободными слотами Google Calendar (FreeBusy).

Функции:
- build_calendar_service
- get_freebusy
- merge_busy
- compute_free_slots
- get_free_slots_for_date
- get_busy_slots_for_period
- book_slot
"""
import os
from dotenv import load_dotenv
from datetime import datetime, timedelta, time
from zoneinfo import ZoneInfo
from typing import List, Dict, Tuple

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

load_dotenv()

SCOPES = ["https://www.googleapis.com/auth/calendar"]
CREDENTIALS_FILE = os.getenv(
    "GOOGLE_CREDENTIALS_FILE", "google_calendar/calendar_properties_primary.json"
)
TOKEN_FILE = os.getenv(
    "GOOGLE_TOKEN_FILE", "google_calendar/calendar_properties_primary.json"
)


def build_calendar_service():
    """Создает Google Calendar API service с OAuth."""
    creds = None
    if os.path.exists(TOKEN_FILE):
        creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not os.path.exists(CREDENTIALS_FILE):
                raise FileNotFoundError(
                    f"Не найден {CREDENTIALS_FILE}. Создай OAuth credentials.json в google_calendar/"
                )
            flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_FILE, SCOPES)
            creds = flow.run_local_server(port=0)

        with open(TOKEN_FILE, "w", encoding="utf-8") as token:
            token.write(creds.to_json())

    return build("calendar", "v3", credentials=creds)


def get_freebusy(
    service,
    calendar_ids: List[str],
    time_min: datetime,
    time_max: datetime,
    time_zone: str = "Europe/Moscow",
) -> Dict[str, List[Tuple[datetime, datetime]]]:
    """Запрашивает занятость (FreeBusy) и возвращает интервалы по календарям."""
    if time_min.tzinfo is None or time_max.tzinfo is None:
        tz = ZoneInfo(time_zone)
        time_min = time_min.replace(tzinfo=tz)
        time_max = time_max.replace(tzinfo=tz)

    body = {
        "timeMin": time_min.isoformat(),
        "timeMax": time_max.isoformat(),
        "timeZone": time_zone,
        "items": [{"id": cid} for cid in calendar_ids],
    }

    resp = service.freebusy().query(body=body).execute()
    busy_by_cal = {}

    for cid, data in resp.get("calendars", {}).items():
        busy_intervals = []
        for slot in data.get("busy", []):
            start = datetime.fromisoformat(slot["start"])
            end = datetime.fromisoformat(slot["end"])
            busy_intervals.append((start, end))
        busy_by_cal[cid] = busy_intervals

    return busy_by_cal


def merge_busy(busy: List[Tuple[datetime, datetime]]) -> List[Tuple[datetime, datetime]]:
    """Сливает пересекающиеся интервалы занятости."""
    if not busy:
        return []
    busy_sorted = sorted(busy, key=lambda x: x[0])
    merged = [busy_sorted[0]]

    for start, end in busy_sorted[1:]:
        last_start, last_end = merged[-1]
        if start <= last_end:
            merged[-1] = (last_start, max(last_end, end))
        else:
            merged.append((start, end))

    return merged


def compute_free_slots(
    busy: List[Tuple[datetime, datetime]],
    day_start: datetime,
    day_end: datetime,
    slot_minutes: int = 45,
    step_minutes: int = 45,
) -> List[Tuple[datetime, datetime]]:
    """Возвращает свободные слоты заданной длительности внутри дня."""
    merged = merge_busy(busy)
    free_slots = []
    cursor = day_start

    for b_start, b_end in merged:
        if cursor < b_start:
            free_slots.extend(_split_into_slots(cursor, b_start, slot_minutes, step_minutes))
        cursor = max(cursor, b_end)

    if cursor < day_end:
        free_slots.extend(_split_into_slots(cursor, day_end, slot_minutes, step_minutes))

    return free_slots


def _split_into_slots(
    start: datetime,
    end: datetime,
    slot_minutes: int,
    step_minutes: int,
) -> List[Tuple[datetime, datetime]]:
    slots = []
    cursor = start
    while cursor + timedelta(minutes=slot_minutes) <= end:
        slots.append((cursor, cursor + timedelta(minutes=slot_minutes)))
        cursor += timedelta(minutes=step_minutes)
    return slots


def get_free_slots_for_date(
    service,
    calendar_id: str,
    date_obj,
    slot_minutes: int = 45,
    step_minutes: int = 45,
    work_start: time = time(hour=9, minute=0),
    work_end: time = time(hour=21, minute=0),
    time_zone: str = "Europe/Moscow",
) -> List[Tuple[datetime, datetime]]:
    """Свободные слоты на конкретную дату."""
    tz = ZoneInfo(time_zone)
    day_start = datetime.combine(date_obj, work_start, tzinfo=tz)
    day_end = datetime.combine(date_obj, work_end, tzinfo=tz)

    busy_by_cal = get_freebusy(service, [calendar_id], day_start, day_end, time_zone)
    all_busy = []
    for busy in busy_by_cal.values():
        all_busy.extend(busy)

    return compute_free_slots(
        all_busy,
        day_start,
        day_end,
        slot_minutes=slot_minutes,
        step_minutes=step_minutes,
    )


def get_busy_slots_for_period(
    service,
    calendar_ids: List[str],
    start: datetime,
    end: datetime,
    time_zone: str = "Europe/Moscow",
) -> Dict[str, List[Tuple[datetime, datetime]]]:
    """Занятые слоты за период для одного или нескольких календарей."""
    return get_freebusy(service, calendar_ids, start, end, time_zone)


def book_slot(
    service,
    calendar_id: str,
    title: str,
    start: datetime,
    end: datetime,
    time_zone: str = "Europe/Moscow",
    description: str = "",
) -> dict:
    """Записывает событие в календарь на указанный слот."""
    if start.tzinfo is None or end.tzinfo is None:
        tz = ZoneInfo(time_zone)
        start = start.replace(tzinfo=tz)
        end = end.replace(tzinfo=tz)

    body = {
        "summary": title,
        "description": description,
        "start": {"dateTime": start.isoformat(), "timeZone": time_zone},
        "end": {"dateTime": end.isoformat(), "timeZone": time_zone},
    }

    return service.events().insert(calendarId=calendar_id, body=body).execute()
