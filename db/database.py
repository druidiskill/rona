import re

import aiosqlite

from config import DATABASE_URL


def _resolve_db_path(database_url: str) -> str:
    if database_url.startswith("sqlite:///"):
        return database_url.replace("sqlite:///", "", 1)
    if database_url.startswith("sqlite://"):
        return database_url.replace("sqlite://", "", 1)
    return database_url


class DatabaseManager:
    def __init__(self, db_path: str = None):
        self.db_path = db_path or _resolve_db_path(DATABASE_URL or "photostudio.db")

    async def init_database(self):
        """Initialize database and create tables."""
        async with aiosqlite.connect(self.db_path) as db:
            await self._create_tables(db)
            await self._insert_initial_data(db)

    async def _create_tables(self, db: aiosqlite.Connection):
        """Create all database tables."""
        await db.execute("PRAGMA foreign_keys = ON")

        await db.execute(
            """
            CREATE TABLE IF NOT EXISTS services (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name VARCHAR(100) NOT NULL,
                description TEXT,
                base_num_clients INTEGER NOT NULL DEFAULT 1,
                max_num_clients INTEGER NOT NULL,
                plus_service_ids INTEGER,
                price_min REAL NOT NULL,
                price_min_weekend REAL NOT NULL,
                fix_price BOOLEAN DEFAULT 0,
                price_for_extra_client REAL NOT NULL,
                price_for_extra_client_weekend REAL NOT NULL,
                min_duration_minutes INTEGER NOT NULL,
                duration_step_minutes INTEGER NOT NULL DEFAULT 60,
                photo_ids TEXT,
                is_active BOOLEAN DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )

        await db.execute(
            """
            CREATE TABLE IF NOT EXISTS clients (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                telegram_id INTEGER UNIQUE,
                vk_id INTEGER UNIQUE,
                name VARCHAR(100) NOT NULL,
                last_name VARCHAR(100),
                phone VARCHAR(20),
                email VARCHAR(100),
                discount_code VARCHAR(100),
                sale INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )

        await db.execute(
            """
            CREATE TABLE IF NOT EXISTS bookings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                client_id INTEGER NOT NULL,
                service_id INTEGER NOT NULL,
                start_time TIMESTAMP NOT NULL,
                num_durations INTEGER NOT NULL,
                num_clients INTEGER NOT NULL,
                status VARCHAR(20) DEFAULT 'pending',
                need_photographer BOOLEAN DEFAULT 0,
                need_makeuproom INTEGER DEFAULT 0,
                notes TEXT,
                all_price REAL NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (client_id) REFERENCES clients (id),
                FOREIGN KEY (service_id) REFERENCES services (id)
            )
            """
        )

        await db.execute(
            """
            CREATE TABLE IF NOT EXISTS admins (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                telegram_id INTEGER UNIQUE,
                vk_id INTEGER UNIQUE,
                is_active BOOLEAN DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )

        await db.execute(
            """
            CREATE TABLE IF NOT EXISTS support_messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                chat_id INTEGER NOT NULL,
                message_id INTEGER NOT NULL,
                role VARCHAR(20) NOT NULL,
                text TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )

        await db.execute(
            """
            CREATE TABLE IF NOT EXISTS faq_entries (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                question TEXT NOT NULL,
                answer TEXT NOT NULL,
                sort_order INTEGER DEFAULT 0,
                is_active BOOLEAN DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )

        await db.execute(
            """
            CREATE TABLE IF NOT EXISTS booking_reminder_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                channel VARCHAR(20) NOT NULL,
                event_id VARCHAR(255) NOT NULL,
                client_id INTEGER NOT NULL,
                booking_date DATE NOT NULL,
                reminder_date DATE NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(channel, event_id, reminder_date),
                FOREIGN KEY (client_id) REFERENCES clients (id)
            )
            """
        )

        cursor = await db.execute("PRAGMA table_info(services)")
        columns = [row[1] for row in await cursor.fetchall()]
        if "base_num_clients" not in columns:
            await db.execute("ALTER TABLE services ADD COLUMN base_num_clients INTEGER NOT NULL DEFAULT 1")
            await db.execute(
                "UPDATE services SET base_num_clients = max_num_clients "
                "WHERE base_num_clients IS NULL OR base_num_clients < 1"
            )

        cursor = await db.execute("PRAGMA table_info(clients)")
        columns = [row[1] for row in await cursor.fetchall()]
        if "last_name" not in columns:
            await db.execute("ALTER TABLE clients ADD COLUMN last_name VARCHAR(100)")
        if "discount_code" not in columns:
            await db.execute("ALTER TABLE clients ADD COLUMN discount_code VARCHAR(100)")

        await self._normalize_legacy_clients(db)

        await db.commit()

    @staticmethod
    def _normalize_phone(value: str | None) -> str | None:
        if not value:
            return None
        digits = "".join(ch for ch in str(value) if ch.isdigit())
        if len(digits) == 11 and digits.startswith(("7", "8")):
            digits = digits[1:]
        return digits if len(digits) == 10 else None

    @staticmethod
    def _normalize_last_name(value: str | None) -> str | None:
        if not value:
            return None
        text = str(value).strip()
        if len(text) < 2:
            return None
        cleaned = text.replace(" ", "").replace("-", "")
        return text if cleaned.isalpha() else None

    @staticmethod
    def _normalize_email(value: str | None) -> str | None:
        if not value:
            return None
        text = str(value).strip()
        if text in {"0", "None", "none", "-"}:
            return None
        if re.fullmatch(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[A-Za-z]{2,}", text):
            return text
        return None

    @staticmethod
    def _normalize_discount_code(value: str | None) -> str | None:
        if not value:
            return None
        text = str(value).strip()
        if text in {"0", "None", "none", "-"}:
            return None
        return text[:100]

    @staticmethod
    def _normalize_sale(value) -> int:
        try:
            return int(value)
        except (TypeError, ValueError):
            return 0

    async def _normalize_legacy_clients(self, db: aiosqlite.Connection):
        cursor = await db.execute(
            """
            SELECT id, phone, email, sale, last_name
            FROM clients
            """
        )
        rows = await cursor.fetchall()

        for client_id, phone, email, sale, last_name in rows:
            normalized_phone = self._normalize_phone(phone)
            fallback_phone = self._normalize_phone(last_name)
            normalized_last_name = self._normalize_last_name(last_name)
            normalized_email = self._normalize_email(email)
            normalized_sale = self._normalize_sale(sale)

            if normalized_phone is None and fallback_phone:
                normalized_phone = fallback_phone
                normalized_last_name = None

            await db.execute(
                """
                UPDATE clients
                SET phone = ?, email = ?, sale = ?, last_name = ?
                WHERE id = ?
                """,
                (normalized_phone, normalized_email, normalized_sale, normalized_last_name, client_id),
            )

    async def _insert_initial_data(self, db: aiosqlite.Connection):
        """Insert initial data into empty DB."""
        cursor = await db.execute("SELECT COUNT(*) FROM services")
        count = await cursor.fetchone()

        if count[0] == 0:
            services = [
                (
                    "Индивидуальная фотосессия",
                    "Профессиональная фотосессия с ретушью",
                    1,
                    1,
                    None,
                    5000.0,
                    6000.0,
                    1,
                    0.0,
                    0.0,
                    60,
                    60,
                    None,
                ),
                (
                    "Семейная фотосессия",
                    "Фотосессия для всей семьи",
                    4,
                    4,
                    None,
                    8000.0,
                    10000.0,
                    0,
                    2000.0,
                    2500.0,
                    90,
                    30,
                    None,
                ),
                (
                    "Love Story",
                    "Романтическая фотосессия для пары",
                    2,
                    2,
                    None,
                    6000.0,
                    7500.0,
                    1,
                    0.0,
                    0.0,
                    75,
                    15,
                    None,
                ),
                (
                    "Детская фотосессия",
                    "Фотосессия для детей",
                    1,
                    1,
                    None,
                    4000.0,
                    5000.0,
                    1,
                    0.0,
                    0.0,
                    45,
                    15,
                    None,
                ),
            ]

            await db.executemany(
                """
                INSERT INTO services (
                    name, description, base_num_clients, max_num_clients, plus_service_ids,
                    price_min, price_min_weekend, fix_price, price_for_extra_client,
                    price_for_extra_client_weekend, min_duration_minutes,
                    duration_step_minutes, photo_ids
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                services,
            )

            await db.commit()
            print("Initial services inserted")


db_manager = DatabaseManager()

__all__ = ["DatabaseManager", "db_manager"]
