from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

import aiosqlite

from app.integrations.local.db.database import db_manager


class CalendarCacheRepository:
    def __init__(self, database_path: str):
        self.db_path = database_path

    def _ensure_db_parent_dir(self) -> None:
        parent = Path(self.db_path).expanduser().resolve().parent
        parent.mkdir(parents=True, exist_ok=True)

    async def list_events(
        self,
        *,
        calendar_id: str,
        period_start: datetime,
        period_end: datetime,
        max_results: int = 250,
        query: str | None = None,
    ) -> list[dict]:
        sql = """
            SELECT event_id, summary, description, start_time, end_time
            FROM calendar_events_cache
            WHERE calendar_id = ?
              AND start_time IS NOT NULL
              AND start_time >= ?
              AND start_time < ?
        """
        params: list[Any] = [
            calendar_id,
            period_start.isoformat(),
            period_end.isoformat(),
        ]
        if query:
            sql += " AND (summary LIKE ? OR description LIKE ?)"
            like_value = f"%{query}%"
            params.extend([like_value, like_value])

        sql += " ORDER BY start_time LIMIT ?"
        params.append(max_results)

        self._ensure_db_parent_dir()
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(sql, params)
            rows = await cursor.fetchall()

        return [
            {
                "id": row[0],
                "summary": row[1] or "",
                "description": row[2] or "",
                "start": datetime.fromisoformat(row[3]) if row[3] else None,
                "end": datetime.fromisoformat(row[4]) if row[4] else None,
            }
            for row in rows
        ]

    async def get_event(self, event_id: str) -> dict | None:
        self._ensure_db_parent_dir()
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                """
                SELECT raw_event
                FROM calendar_events_cache
                WHERE event_id = ?
                LIMIT 1
                """,
                (event_id,),
            )
            row = await cursor.fetchone()

        if not row or not row[0]:
            return None
        return json.loads(row[0])

    async def upsert_event(
        self,
        *,
        event_id: str,
        calendar_id: str,
        summary: str,
        description: str,
        start_time: datetime | None,
        end_time: datetime | None,
        raw_event: dict,
    ) -> None:
        self._ensure_db_parent_dir()
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                """
                INSERT INTO calendar_events_cache (
                    event_id, calendar_id, summary, description, start_time, end_time, raw_event, synced_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(event_id) DO UPDATE SET
                    calendar_id = excluded.calendar_id,
                    summary = excluded.summary,
                    description = excluded.description,
                    start_time = excluded.start_time,
                    end_time = excluded.end_time,
                    raw_event = excluded.raw_event,
                    synced_at = CURRENT_TIMESTAMP
                """,
                (
                    event_id,
                    calendar_id,
                    summary,
                    description,
                    start_time.isoformat() if start_time else None,
                    end_time.isoformat() if end_time else None,
                    json.dumps(raw_event, ensure_ascii=False),
                ),
            )
            await db.commit()

    async def replace_period(
        self,
        *,
        calendar_id: str,
        period_start: datetime,
        period_end: datetime,
        rows: list[dict],
    ) -> None:
        self._ensure_db_parent_dir()
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                """
                DELETE FROM calendar_events_cache
                WHERE calendar_id = ?
                  AND start_time IS NOT NULL
                  AND start_time >= ?
                  AND start_time < ?
                """,
                (
                    calendar_id,
                    period_start.isoformat(),
                    period_end.isoformat(),
                ),
            )

            for row in rows:
                await db.execute(
                    """
                    INSERT INTO calendar_events_cache (
                        event_id, calendar_id, summary, description, start_time, end_time, raw_event, synced_at
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                    ON CONFLICT(event_id) DO UPDATE SET
                        calendar_id = excluded.calendar_id,
                        summary = excluded.summary,
                        description = excluded.description,
                        start_time = excluded.start_time,
                        end_time = excluded.end_time,
                        raw_event = excluded.raw_event,
                        synced_at = CURRENT_TIMESTAMP
                    """,
                    (
                        row["event_id"],
                        calendar_id,
                        row["summary"],
                        row["description"],
                        row["start_time"],
                        row["end_time"],
                        row["raw_event"],
                    ),
                )
            await db.commit()

    async def delete_event(self, event_id: str) -> None:
        self._ensure_db_parent_dir()
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("DELETE FROM calendar_events_cache WHERE event_id = ?", (event_id,))
            await db.commit()

    async def has_events(self, calendar_id: str) -> bool:
        self._ensure_db_parent_dir()
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                """
                SELECT 1
                FROM calendar_events_cache
                WHERE calendar_id = ?
                LIMIT 1
                """,
                (calendar_id,),
            )
            return await cursor.fetchone() is not None

    async def set_last_sync(self, *, calendar_id: str, synced_at: datetime) -> None:
        self._ensure_db_parent_dir()
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                """
                INSERT INTO calendar_cache_meta (meta_key, meta_value, updated_at)
                VALUES (?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(meta_key) DO UPDATE SET
                    meta_value = excluded.meta_value,
                    updated_at = CURRENT_TIMESTAMP
                """,
                (self._last_sync_key(calendar_id), synced_at.isoformat()),
            )
            await db.commit()

    async def get_last_sync(self, calendar_id: str) -> datetime | None:
        self._ensure_db_parent_dir()
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                """
                SELECT meta_value
                FROM calendar_cache_meta
                WHERE meta_key = ?
                LIMIT 1
                """,
                (self._last_sync_key(calendar_id),),
            )
            row = await cursor.fetchone()

        if not row or not row[0]:
            return None
        return datetime.fromisoformat(row[0])

    @staticmethod
    def _last_sync_key(calendar_id: str) -> str:
        return f"calendar_events_last_sync:{calendar_id}"


calendar_cache_repo = CalendarCacheRepository(db_manager.db_path)


__all__ = ["CalendarCacheRepository", "calendar_cache_repo"]
