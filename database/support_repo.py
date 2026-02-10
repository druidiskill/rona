import aiosqlite
from typing import List, Tuple, Optional
from database.database import DatabaseManager

class SupportRepository:
    """Репозиторий для сообщений поддержки"""

    def __init__(self, db_manager: DatabaseManager):
        self.db_manager = db_manager

    async def add_message(
        self,
        user_id: int,
        chat_id: int,
        message_id: int,
        role: str,
        text: Optional[str] = None,
    ) -> None:
        async with aiosqlite.connect(self.db_manager.db_path) as db:
            await db.execute(
                """
                INSERT INTO support_messages (user_id, chat_id, message_id, role, text)
                VALUES (?, ?, ?, ?, ?)
                """,
                (user_id, chat_id, message_id, role, text),
            )
            await db.commit()

    async def get_last_messages(self, user_id: int, limit: int = 6) -> List[Tuple[str, Optional[str]]]:
        async with aiosqlite.connect(self.db_manager.db_path) as db:
            cursor = await db.execute(
                """
                SELECT role, text FROM support_messages
                WHERE user_id = ? AND role IN ('user', 'admin')
                ORDER BY id DESC
                LIMIT ?
                """,
                (user_id, limit),
            )
            rows = await cursor.fetchall()
            rows.reverse()
            return [(row[0], row[1]) for row in rows]

    async def get_message_ids(self, user_id: int) -> List[Tuple[int, int]]:
        async with aiosqlite.connect(self.db_manager.db_path) as db:
            cursor = await db.execute(
                """
                SELECT chat_id, message_id FROM support_messages
                WHERE user_id = ?
                """,
                (user_id,),
            )
            rows = await cursor.fetchall()
            return [(row[0], row[1]) for row in rows]

    async def get_admin_alerts(self, user_id: int) -> List[Tuple[int, int]]:
        async with aiosqlite.connect(self.db_manager.db_path) as db:
            cursor = await db.execute(
                """
                SELECT chat_id, message_id FROM support_messages
                WHERE user_id = ? AND role = 'admin_alert'
                """,
                (user_id,),
            )
            rows = await cursor.fetchall()
            return [(row[0], row[1]) for row in rows]

    async def delete_admin_alerts(self, user_id: int) -> None:
        async with aiosqlite.connect(self.db_manager.db_path) as db:
            await db.execute(
                """
                DELETE FROM support_messages
                WHERE user_id = ? AND role = 'admin_alert'
                """,
                (user_id,),
            )
            await db.commit()

    async def delete_by_user(self, user_id: int) -> None:
        async with aiosqlite.connect(self.db_manager.db_path) as db:
            await db.execute(
                """
                DELETE FROM support_messages
                WHERE user_id = ?
                """,
                (user_id,),
            )
            await db.commit()
