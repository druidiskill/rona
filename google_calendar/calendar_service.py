from __future__ import annotations

import os
from dotenv import load_dotenv
from datetime import date, datetime, time
from typing import List, Optional, Dict, Any
from zoneinfo import ZoneInfo

load_dotenv()

from google_calendar.calendar_freebusy import (
    build_calendar_service,
    get_free_slots_for_date,
    book_slot,
)


class GoogleCalendarService:
    def __init__(self, calendar_id: Optional[str] = None, time_zone: str = "Europe/Moscow"):
        self.calendar_id = calendar_id or os.getenv("GOOGLE_CALENDAR_ID")
        if not self.calendar_id:
            raise ValueError("GOOGLE_CALENDAR_ID is not set")
        self.time_zone = time_zone
        self._service = build_calendar_service()

    def _ensure_tz(self, dt: datetime) -> datetime:
        if dt.tzinfo is None:
            return dt.replace(tzinfo=ZoneInfo(self.time_zone))
        return dt

    def _parse_event_time(self, event: Dict[str, Any], key: str) -> Optional[datetime]:
        raw = event.get(key, {})
        if "dateTime" in raw:
            return datetime.fromisoformat(raw["dateTime"])
        if "date" in raw:
            return datetime.fromisoformat(f"{raw['date']}T00:00:00")
        return None

    async def get_free_slots(
        self,
        date: date,
        duration_minutes: int = 60,
        step_minutes: int = 60,
        work_start: time = time(hour=9, minute=0),
        work_end: time = time(hour=21, minute=0),
    ) -> List[Dict[str, datetime]]:
        slots = get_free_slots_for_date(
            self._service,
            self.calendar_id,
            date,
            slot_minutes=duration_minutes,
            step_minutes=step_minutes,
            work_start=work_start,
            work_end=work_end,
            time_zone=self.time_zone,
        )
        return [{"start": s, "end": e} for s, e in slots]

    async def create_event(
        self,
        title: str,
        description: str,
        start_time: datetime,
        end_time: datetime,
    ) -> Dict[str, Any]:
        start_time = self._ensure_tz(start_time)
        end_time = self._ensure_tz(end_time)
        return book_slot(
            self._service,
            self.calendar_id,
            title=title,
            start=start_time,
            end=end_time,
            time_zone=self.time_zone,
            description=description,
        )

    async def list_events(
        self,
        start: datetime,
        end: datetime,
        query: Optional[str] = None,
        max_results: int = 250,
    ) -> List[Dict[str, Any]]:
        start = self._ensure_tz(start)
        end = self._ensure_tz(end)
        response = (
            self._service.events()
            .list(
                calendarId=self.calendar_id,
                timeMin=start.isoformat(),
                timeMax=end.isoformat(),
                singleEvents=True,
                orderBy="startTime",
                q=query,
                maxResults=max_results,
            )
            .execute()
        )

        events = []
        for event in response.get("items", []):
            events.append(
                {
                    "id": event.get("id"),
                    "summary": event.get("summary", ""),
                    "description": event.get("description", ""),
                    "start": self._parse_event_time(event, "start"),
                    "end": self._parse_event_time(event, "end"),
                }
            )
        return events
