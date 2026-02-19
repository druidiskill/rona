import aiosqlite
from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional

from database.database import DatabaseManager


@dataclass
class FaqEntry:
    id: Optional[int] = None
    question: str = ""
    answer: str = ""
    sort_order: int = 0
    is_active: bool = True
    created_at: Optional[datetime] = None


class FaqRepository:
    """Репозиторий FAQ."""

    def __init__(self, db_manager: DatabaseManager):
        self.db_manager = db_manager

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

