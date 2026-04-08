from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from config import (
    CALENDAR_CACHE_FUTURE_DAYS,
    CALENDAR_CACHE_PAST_DAYS,
    CALENDAR_CACHE_SYNC_INTERVAL_SECONDS,
    GOOGLE_CALENDAR_ID,
)
from .cache_repo import calendar_cache_repo
from .service import GoogleCalendarService


logger = logging.getLogger(__name__)

MOSCOW_TZ = ZoneInfo("Europe/Moscow")
async def sync_calendar_cache(*, force: bool = False) -> int | None:
    calendar_id = GOOGLE_CALENDAR_ID or "primary"
    now = datetime.now(MOSCOW_TZ)

    if not force:
        last_sync = await calendar_cache_repo.get_last_sync(calendar_id)
        if last_sync and (now - last_sync).total_seconds() < CALENDAR_CACHE_SYNC_INTERVAL_SECONDS:
            return None

    service = GoogleCalendarService(calendar_id=calendar_id)
    period_start = now - timedelta(days=CALENDAR_CACHE_PAST_DAYS)
    period_end = now + timedelta(days=CALENDAR_CACHE_FUTURE_DAYS)
    return await service.sync_cache(period_start=period_start, period_end=period_end)


async def run_calendar_cache_sync_loop(owner_name: str) -> None:
    while True:
        try:
            synced_count = await sync_calendar_cache(force=False)
            if synced_count is not None:
                logger.info("%s calendar cache synced: %s events", owner_name, synced_count)
        except Exception:
            logger.exception("Ошибка синхронизации календарного кэша для %s", owner_name)
        await asyncio.sleep(CALENDAR_CACHE_SYNC_INTERVAL_SECONDS)


__all__ = ["run_calendar_cache_sync_loop", "sync_calendar_cache"]
