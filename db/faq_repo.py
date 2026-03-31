import aiosqlite
from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional

from .database import DatabaseManager


@dataclass
class FaqEntry:
    id: Optional[int] = None
    question: str = ""
    answer: str = ""
    sort_order: int = 0
    is_active: bool = True
    created_at: Optional[datetime] = None


class FaqRepository:
    """Repository for FAQ entries."""

    def __init__(self, db_manager: DatabaseManager):
        self.db_manager = db_manager

    async def get_all(self) -> List[FaqEntry]:
        async with aiosqlite.connect(self.db_manager.db_path) as db:
            cursor = await db.execute(
                """
                SELECT id, question, answer, sort_order, is_active, created_at
                FROM faq_entries
                ORDER BY sort_order ASC, id ASC
                """
            )
            rows = await cursor.fetchall()
            return [self._row_to_faq(row) for row in rows]

    async def get_all_active(self) -> List[FaqEntry]:
        async with aiosqlite.connect(self.db_manager.db_path) as db:
            cursor = await db.execute(
                """
                SELECT id, question, answer, sort_order, is_active, created_at
                FROM faq_entries
                WHERE is_active = 1
                ORDER BY sort_order ASC, id ASC
                """
            )
            rows = await cursor.fetchall()
            return [self._row_to_faq(row) for row in rows]

    async def add(
        self,
        question: str,
        answer: str,
        sort_order: int = 0,
        is_active: bool = True,
    ) -> int:
        async with aiosqlite.connect(self.db_manager.db_path) as db:
            cursor = await db.execute(
                """
                INSERT INTO faq_entries (question, answer, sort_order, is_active)
                VALUES (?, ?, ?, ?)
                """,
                (question, answer, sort_order, 1 if is_active else 0),
            )
            await db.commit()
            return int(cursor.lastrowid or 0)

    async def update_question(self, faq_id: int, question: str) -> None:
        async with aiosqlite.connect(self.db_manager.db_path) as db:
            await db.execute(
                "UPDATE faq_entries SET question = ? WHERE id = ?",
                (question, faq_id),
            )
            await db.commit()

    async def update_answer(self, faq_id: int, answer: str) -> None:
        async with aiosqlite.connect(self.db_manager.db_path) as db:
            await db.execute(
                "UPDATE faq_entries SET answer = ? WHERE id = ?",
                (answer, faq_id),
            )
            await db.commit()

    async def set_active(self, faq_id: int, is_active: bool) -> None:
        async with aiosqlite.connect(self.db_manager.db_path) as db:
            await db.execute(
                "UPDATE faq_entries SET is_active = ? WHERE id = ?",
                (1 if is_active else 0, faq_id),
            )
            await db.commit()

    async def delete(self, faq_id: int) -> None:
        async with aiosqlite.connect(self.db_manager.db_path) as db:
            await db.execute("DELETE FROM faq_entries WHERE id = ?", (faq_id,))
            await db.commit()

    async def get_by_id(self, faq_id: int) -> Optional[FaqEntry]:
        async with aiosqlite.connect(self.db_manager.db_path) as db:
            cursor = await db.execute(
                """
                SELECT id, question, answer, sort_order, is_active, created_at
                FROM faq_entries
                WHERE id = ?
                """,
                (faq_id,),
            )
            row = await cursor.fetchone()
            return self._row_to_faq(row) if row else None

    def _row_to_faq(self, row) -> FaqEntry:
        return FaqEntry(
            id=row[0],
            question=row[1],
            answer=row[2],
            sort_order=row[3] or 0,
            is_active=bool(row[4]),
            created_at=datetime.fromisoformat(row[5]) if row[5] else None,
        )


__all__ = ["FaqEntry", "FaqRepository"]
