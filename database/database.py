import aiosqlite
import os
from typing import Optional, List, Dict, Any
from datetime import datetime
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
        """Инициализация базы данных с созданием таблиц"""
        async with aiosqlite.connect(self.db_path) as db:
            await self._create_tables(db)
            await self._insert_initial_data(db)
    
    async def _create_tables(self, db: aiosqlite.Connection):
        """Создание всех таблиц в базе данных"""
        # Включаем поддержку FOREIGN KEY
        await db.execute("PRAGMA foreign_keys = ON")
        # Таблица услуг
        await db.execute("""
            CREATE TABLE IF NOT EXISTS services (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name VARCHAR(100) NOT NULL,
                description TEXT,
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
        """)
        
        # Таблица клиентов
        await db.execute("""
            CREATE TABLE IF NOT EXISTS clients (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                telegram_id INTEGER UNIQUE,
                vk_id INTEGER UNIQUE,
                name VARCHAR(100) NOT NULL,
                phone VARCHAR(20),
                email VARCHAR(100),
                sale INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Таблица бронирований
        await db.execute("""
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
        """)
        
        # Таблица администраторов
        await db.execute("""
            CREATE TABLE IF NOT EXISTS admins (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                telegram_id INTEGER UNIQUE,
                vk_id INTEGER UNIQUE,
                is_active BOOLEAN DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        await db.commit()
    
    async def _insert_initial_data(self, db: aiosqlite.Connection):
        """Добавление начальных данных"""
        # Проверяем, есть ли уже услуги
        cursor = await db.execute("SELECT COUNT(*) FROM services")
        count = await cursor.fetchone()
        
        if count[0] == 0:
            services = [
                # name, description, max_num_clients, plus_service_ids, price_min, price_min_weekend, 
                # fix_price, price_for_extra_client, price_for_extra_client_weekend, min_duration_minutes, duration_step_minutes, photo_ids
                ("Индивидуальная фотосессия", "Профессиональная фотосессия с ретушью", 1, None, 5000.0, 6000.0, 1, 0.0, 0.0, 60, 60, None),
                ("Семейная фотосессия", "Фотосессия для всей семьи", 4, None, 8000.0, 10000.0, 0, 2000.0, 2500.0, 90, 30, None),
                ("Love Story", "Романтическая фотосессия для пары", 2, None, 6000.0, 7500.0, 1, 0.0, 0.0, 75, 15, None),
                ("Детская фотосессия", "Фотосессия для детей", 1, None, 4000.0, 5000.0, 1, 0.0, 0.0, 45, 15, None)
            ]
            
            await db.executemany(
                """INSERT INTO services (name, description, max_num_clients, plus_service_ids, 
                   price_min, price_min_weekend, fix_price, price_for_extra_client, 
                   price_for_extra_client_weekend, min_duration_minutes, duration_step_minutes, photo_ids) 
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                services
            )
            
            await db.commit()
            print("Начальные данные добавлены в базу данных")

# Глобальный экземпляр менеджера базы данных
db_manager = DatabaseManager()
