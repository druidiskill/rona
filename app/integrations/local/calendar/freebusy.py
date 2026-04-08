# -*- coding: utf-8 -*-
"""
Unified module for working with Google Calendar free/busy slots.
"""

from __future__ import annotations

import json
import os
from datetime import datetime, time, timedelta
from typing import Dict, List, Tuple
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from dotenv import load_dotenv
from google.auth.transport.requests import Request
from google.oauth2 import service_account
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

load_dotenv()

SCOPES = ["https://www.googleapis.com/auth/calendar"]
CREDENTIALS_FILE = os.getenv(
    "GOOGLE_CREDENTIALS_FILE", "calendar_properties_primary.json"
)
TOKEN_FILE = os.getenv(
    "GOOGLE_TOKEN_FILE", "calendar_properties_primary.json"
)


def _load_json_objects(path: str) -> List[dict]:
    with open(path, "r", encoding="utf-8-sig") as f:
        raw = f.read().strip()

    if not raw:
        return []

    try:
        parsed = json.loads(raw)
        return [parsed] if isinstance(parsed, dict) else []
    except Exception:
        pass

    decoder = json.JSONDecoder()
    idx = 0
    objs: List[dict] = []
    length = len(raw)

    while idx < length:
        while idx < length and raw[idx].isspace():
            idx += 1
        if idx >= length:
            break
        obj, end = decoder.raw_decode(raw, idx)
        if isinstance(obj, dict):
            objs.append(obj)
        idx = end

    return objs


def _extract_oauth_client_config(objs: List[dict]) -> dict | None:
    for obj in objs:
        if "installed" in obj or "web" in obj:
            return obj
    return None


def _extract_token_payload(objs: List[dict]) -> dict | None:
    for obj in objs:
        if "token" in obj and "refresh_token" in obj and "client_id" in obj:
            return obj
    return None


def _extract_service_account_payload(objs: List[dict]) -> dict | None:
    for obj in objs:
        if obj.get("type") == "service_account":
            return obj
    return None


def _resolve_token_file() -> str:
    if os.path.abspath(TOKEN_FILE) == os.path.abspath(CREDENTIALS_FILE):
        return f"{TOKEN_FILE}.token.json"
    return TOKEN_FILE


def _get_tz(time_zone: str) -> ZoneInfo:
    try:
        return ZoneInfo(time_zone)
    except ZoneInfoNotFoundError:
        return ZoneInfo("UTC")


def build_calendar_service():
    token_file = _resolve_token_file()
    creds = None

    if os.path.exists(token_file):
        try:
            creds = Credentials.from_authorized_user_file(token_file, SCOPES)
        except Exception:
            token_objs = _load_json_objects(token_file)
            token_payload = _extract_token_payload(token_objs)
            if token_payload:
                creds = Credentials.from_authorized_user_info(token_payload, SCOPES)

    if (not creds) and os.path.exists(CREDENTIALS_FILE):
        creds_objs = _load_json_objects(CREDENTIALS_FILE)
        token_payload = _extract_token_payload(creds_objs)
        if token_payload:
            creds = Credentials.from_authorized_user_info(token_payload, SCOPES)

    if creds and not creds.valid:
        if creds.expired and creds.refresh_token:
            creds.refresh(Request())
            with open(token_file, "w", encoding="utf-8") as token:
                token.write(creds.to_json())
        else:
            creds = None

    if not creds and os.path.exists(CREDENTIALS_FILE):
        creds_objs = _load_json_objects(CREDENTIALS_FILE)
        oauth_client_config = _extract_oauth_client_config(creds_objs)
        if oauth_client_config:
            flow = InstalledAppFlow.from_client_config(oauth_client_config, SCOPES)
            creds = flow.run_local_server(port=0)
            with open(token_file, "w", encoding="utf-8") as token:
                token.write(creds.to_json())

    if not creds and os.path.exists(CREDENTIALS_FILE):
        creds_objs = _load_json_objects(CREDENTIALS_FILE)
        service_account_payload = _extract_service_account_payload(creds_objs)
        if service_account_payload:
            creds = service_account.Credentials.from_service_account_info(
                service_account_payload,
                scopes=SCOPES,
            )
            creds.refresh(Request())

    if not creds:
        raise FileNotFoundError(
            f"Не удалось получить Google credentials. Проверьте {CREDENTIALS_FILE} и {token_file}"
        )

    return build("calendar", "v3", credentials=creds)


def get_freebusy(
    service,
    calendar_ids: List[str],
    time_min: datetime,
    time_max: datetime,
    time_zone: str = "Europe/Moscow",
) -> Dict[str, List[Tuple[datetime, datetime]]]:
    if time_min.tzinfo is None or time_max.tzinfo is None:
        tz = _get_tz(time_zone)
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
    tz = _get_tz(time_zone)
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
    if start.tzinfo is None or end.tzinfo is None:
        tz = _get_tz(time_zone)
        start = start.replace(tzinfo=tz)
        end = end.replace(tzinfo=tz)

    body = {
        "summary": title,
        "description": description,
        "start": {"dateTime": start.isoformat(), "timeZone": time_zone},
        "end": {"dateTime": end.isoformat(), "timeZone": time_zone},
    }

    return service.events().insert(calendarId=calendar_id, body=body).execute()


__all__ = [
    "book_slot",
    "build_calendar_service",
    "compute_free_slots",
    "get_busy_slots_for_period",
    "get_free_slots_for_date",
    "get_freebusy",
    "merge_busy",
]
