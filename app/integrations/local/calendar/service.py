from __future__ import annotations

import json
import logging
import os
from datetime import date, datetime, time
from typing import Any, Dict, List, Optional
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from dotenv import load_dotenv

from .cache_repo import calendar_cache_repo
from .freebusy import book_slot, build_calendar_service, get_free_slots_for_date

load_dotenv()
logger = logging.getLogger(__name__)


class GoogleCalendarService:
    def __init__(self, calendar_id: Optional[str] = None, time_zone: str = "Europe/Moscow"):
        self.calendar_id = calendar_id or os.getenv("GOOGLE_CALENDAR_ID") or "primary"
        self.time_zone = time_zone
        self._service = None

    def _get_service(self):
        if self._service is None:
            self._service = build_calendar_service()
        return self._service

    def _ensure_tz(self, dt: datetime) -> datetime:
        if dt.tzinfo is None:
            try:
                tz = ZoneInfo(self.time_zone)
            except ZoneInfoNotFoundError:
                tz = ZoneInfo("UTC")
            return dt.replace(tzinfo=tz)
        return dt

    def _get_tzinfo(self) -> ZoneInfo:
        try:
            return ZoneInfo(self.time_zone)
        except ZoneInfoNotFoundError:
            return ZoneInfo("UTC")

    def _parse_event_time(self, event: Dict[str, Any], key: str) -> Optional[datetime]:
        raw = event.get(key, {})
        try:
            tz = ZoneInfo(self.time_zone)
        except ZoneInfoNotFoundError:
            tz = ZoneInfo("UTC")
        if "dateTime" in raw:
            value = datetime.fromisoformat(raw["dateTime"])
            if value.tzinfo is None:
                return value.replace(tzinfo=tz)
            return value.astimezone(tz)
        if "date" in raw:
            return datetime.fromisoformat(f"{raw['date']}T00:00:00").replace(tzinfo=tz)
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
            self._get_service(),
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
        payload = book_slot(
            self._get_service(),
            self.calendar_id,
            title=title,
            start=start_time,
            end=end_time,
            time_zone=self.time_zone,
            description=description,
        )
        try:
            await calendar_cache_repo.upsert_event(
                event_id=str(payload.get("id") or ""),
                calendar_id=self.calendar_id,
                summary=payload.get("summary", ""),
                description=payload.get("description", ""),
                start_time=self._parse_event_time(payload, "start"),
                end_time=self._parse_event_time(payload, "end"),
                raw_event=payload,
            )
        except Exception:
            logger.exception("Не удалось записать новое событие в локальный кэш календаря")
        return payload

    def _fetch_raw_events(
        self,
        *,
        start: datetime,
        end: datetime,
        query: Optional[str] = None,
        max_results: int | None = None,
    ) -> list[dict]:
        service = self._get_service()
        page_token = None
        items: list[dict] = []

        while True:
            response = (
                service.events()
                .list(
                    calendarId=self.calendar_id,
                    timeMin=start.isoformat(),
                    timeMax=end.isoformat(),
                    timeZone=self.time_zone,
                    singleEvents=True,
                    orderBy="startTime",
                    q=query,
                    maxResults=min(max_results or 250, 250) if max_results else 250,
                    pageToken=page_token,
                )
                .execute()
            )
            batch = response.get("items", [])
            items.extend(batch)

            if max_results and len(items) >= max_results:
                return items[:max_results]

            page_token = response.get("nextPageToken")
            if not page_token:
                return items

    def _normalize_event(self, event: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "id": event.get("id"),
            "summary": event.get("summary", ""),
            "description": event.get("description", ""),
            "start": self._parse_event_time(event, "start"),
            "end": self._parse_event_time(event, "end"),
        }

    def _build_cache_row(self, event: Dict[str, Any]) -> dict:
        start_time = self._parse_event_time(event, "start")
        end_time = self._parse_event_time(event, "end")
        return {
            "event_id": str(event.get("id") or ""),
            "summary": event.get("summary", ""),
            "description": event.get("description", ""),
            "start_time": start_time.isoformat() if start_time else None,
            "end_time": end_time.isoformat() if end_time else None,
            "raw_event": json.dumps(event, ensure_ascii=False),
        }

    async def sync_cache(
        self,
        *,
        period_start: datetime,
        period_end: datetime,
    ) -> int:
        period_start = self._ensure_tz(period_start)
        period_end = self._ensure_tz(period_end)
        raw_events = self._fetch_raw_events(
            start=period_start,
            end=period_end,
            max_results=None,
        )
        rows = [self._build_cache_row(event) for event in raw_events]

        await calendar_cache_repo.replace_period(
            calendar_id=self.calendar_id,
            period_start=period_start,
            period_end=period_end,
            rows=rows,
        )
        await calendar_cache_repo.set_last_sync(
            calendar_id=self.calendar_id,
            synced_at=datetime.now(self._get_tzinfo()),
        )
        return len(rows)

    async def list_events(
        self,
        start: datetime,
        end: datetime,
        query: Optional[str] = None,
        max_results: int = 250,
    ) -> List[Dict[str, Any]]:
        start = self._ensure_tz(start)
        end = self._ensure_tz(end)
        cached_events = await calendar_cache_repo.list_events(
            calendar_id=self.calendar_id,
            period_start=start,
            period_end=end,
            max_results=max_results,
            query=query,
        )
        if cached_events or await calendar_cache_repo.has_events(self.calendar_id):
            return cached_events

        raw_events = self._fetch_raw_events(
            start=start,
            end=end,
            query=query,
            max_results=max_results,
        )
        for event in raw_events:
            await calendar_cache_repo.upsert_event(
                event_id=str(event.get("id") or ""),
                calendar_id=self.calendar_id,
                summary=event.get("summary", ""),
                description=event.get("description", ""),
                start_time=self._parse_event_time(event, "start"),
                end_time=self._parse_event_time(event, "end"),
                raw_event=event,
            )
        return [self._normalize_event(event) for event in raw_events]

    async def get_event(self, event_id: str) -> dict | None:
        cached_event = await calendar_cache_repo.get_event(event_id)
        if cached_event:
            return cached_event

        event = (
            self._get_service().events().get(
                calendarId=self.calendar_id,
                eventId=event_id,
            ).execute()
        )
        if event:
            await calendar_cache_repo.upsert_event(
                event_id=str(event.get("id") or ""),
                calendar_id=self.calendar_id,
                summary=event.get("summary", ""),
                description=event.get("description", ""),
                start_time=self._parse_event_time(event, "start"),
                end_time=self._parse_event_time(event, "end"),
                raw_event=event,
            )
        return event

    async def delete_event(self, event_id: str) -> bool:
        self._get_service().events().delete(
            calendarId=self.calendar_id,
            eventId=event_id,
        ).execute()
        await calendar_cache_repo.delete_event(event_id)
        return True


__all__ = ["GoogleCalendarService"]
