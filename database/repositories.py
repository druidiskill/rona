import aiosqlite
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
from database.models import Service, Client, Booking, Admin, BookingStatus, BookingWithDetails, TimeSlot
from database.database import DatabaseManager

class ServiceRepository:
    """Репозиторий для работы с услугами"""
    
    def __init__(self, db_manager: DatabaseManager):
        self.db_manager = db_manager
    
    async def get_all(self) -> List[Service]:
        """Получение всех услуг"""
        async with aiosqlite.connect(self.db_manager.db_path) as db:
            cursor = await db.execute("""
                SELECT * FROM services ORDER BY name
            """)
            rows = await cursor.fetchall()
            return [self._row_to_service(row) for row in rows]
    
    async def get_all_active(self) -> List[Service]:
        """Получение всех активных услуг"""
        async with aiosqlite.connect(self.db_manager.db_path) as db:
            cursor = await db.execute("""
                SELECT * FROM services WHERE is_active = 1 ORDER BY name
            """)
            rows = await cursor.fetchall()
            return [self._row_to_service(row) for row in rows]
    
    async def get_by_id(self, service_id: int) -> Optional[Service]:
        """Получение услуги по ID"""
        async with aiosqlite.connect(self.db_manager.db_path) as db:
            cursor = await db.execute("SELECT * FROM services WHERE id = ?", (service_id,))
            row = await cursor.fetchone()
            return self._row_to_service(row) if row else None
    
    async def create(self, service: Service) -> int:
        """Создание новой услуги"""
        async with aiosqlite.connect(self.db_manager.db_path) as db:
            cursor = await db.execute("""
                INSERT INTO services (name, description, max_num_clients, plus_service_ids, 
                                   price_min, price_min_weekend, fix_price, price_for_extra_client,
                                   price_for_extra_client_weekend, min_duration_minutes, 
                                   duration_step_minutes, photo_ids, is_active)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                service.name, service.description, service.max_num_clients,
                service.plus_service_ids, service.price_min, service.price_min_weekend,
                service.fix_price, service.price_for_extra_client,
                service.price_for_extra_client_weekend, service.min_duration_minutes,
                service.duration_step_minutes, service.photo_ids, service.is_active
            ))
            await db.commit()
            return cursor.lastrowid
    
    async def update(self, service: Service) -> bool:
        """Обновление услуги"""
        async with aiosqlite.connect(self.db_manager.db_path) as db:
            cursor = await db.execute("""
                UPDATE services SET name=?, description=?, max_num_clients=?, plus_service_ids=?,
                                  price_min=?, price_min_weekend=?, fix_price=?, price_for_extra_client=?,
                                  price_for_extra_client_weekend=?, min_duration_minutes=?,
                                  duration_step_minutes=?, photo_ids=?, is_active=?
                WHERE id=?
            """, (
                service.name, service.description, service.max_num_clients,
                service.plus_service_ids, service.price_min, service.price_min_weekend,
                service.fix_price, service.price_for_extra_client,
                service.price_for_extra_client_weekend, service.min_duration_minutes,
                service.duration_step_minutes, service.photo_ids, service.is_active,
                service.id
            ))
            await db.commit()
            return cursor.rowcount > 0
    
    def _row_to_service(self, row) -> Service:
        """Преобразование строки БД в модель Service"""
        return Service(
            id=row[0], name=row[1], description=row[2], max_num_clients=row[3],
            plus_service_ids=row[4], price_min=row[5], price_min_weekend=row[6],
            fix_price=bool(row[7]), price_for_extra_client=row[8],
            price_for_extra_client_weekend=row[9], min_duration_minutes=row[10],
            duration_step_minutes=row[11], photo_ids=row[12], is_active=bool(row[13]),
            created_at=datetime.fromisoformat(row[14]) if row[14] else None
        )

class ClientRepository:
    """Репозиторий для работы с клиентами"""
    
    def __init__(self, db_manager: DatabaseManager):
        self.db_manager = db_manager
    
    async def get_by_telegram_id(self, telegram_id: int) -> Optional[Client]:
        """Получение клиента по Telegram ID"""
        async with aiosqlite.connect(self.db_manager.db_path) as db:
            cursor = await db.execute("SELECT * FROM clients WHERE telegram_id = ?", (telegram_id,))
            row = await cursor.fetchone()
            return self._row_to_client(row) if row else None
    
    async def get_by_vk_id(self, vk_id: int) -> Optional[Client]:
        """Получение клиента по VK ID"""
        async with aiosqlite.connect(self.db_manager.db_path) as db:
            cursor = await db.execute("SELECT * FROM clients WHERE vk_id = ?", (vk_id,))
            row = await cursor.fetchone()
            return self._row_to_client(row) if row else None
    
    async def get_by_phone(self, phone: str) -> Optional[Client]:
        """Получение клиента по номеру телефона"""
        async with aiosqlite.connect(self.db_manager.db_path) as db:
            cursor = await db.execute("SELECT * FROM clients WHERE phone = ?", (phone,))
            row = await cursor.fetchone()
            return self._row_to_client(row) if row else None
    
    async def get_by_id(self, client_id: int) -> Optional[Client]:
        """Получение клиента по ID"""
        async with aiosqlite.connect(self.db_manager.db_path) as db:
            cursor = await db.execute("SELECT * FROM clients WHERE id = ?", (client_id,))
            row = await cursor.fetchone()
            return self._row_to_client(row) if row else None
    
    async def create(self, client: Client) -> int:
        """Создание нового клиента"""
        async with aiosqlite.connect(self.db_manager.db_path) as db:
            cursor = await db.execute("""
                INSERT INTO clients (telegram_id, vk_id, name, phone, email, sale)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (client.telegram_id, client.vk_id, client.name, client.phone, client.email, client.sale))
            await db.commit()
            return cursor.lastrowid
    
    async def update(self, client: Client) -> bool:
        """Обновление клиента"""
        async with aiosqlite.connect(self.db_manager.db_path) as db:
            cursor = await db.execute("""
                UPDATE clients SET telegram_id=?, vk_id=?, name=?, phone=?, email=?, sale=?
                WHERE id=?
            """, (client.telegram_id, client.vk_id, client.name, client.phone, client.email, client.sale, client.id))
            await db.commit()
            return cursor.rowcount > 0
    
    async def get_all(self) -> List[Client]:
        """Получение всех клиентов"""
        async with aiosqlite.connect(self.db_manager.db_path) as db:
            cursor = await db.execute("SELECT * FROM clients ORDER BY created_at DESC")
            rows = await cursor.fetchall()
            return [self._row_to_client(row) for row in rows]
    
    def _row_to_client(self, row) -> Client:
        """Преобразование строки БД в модель Client"""
        return Client(
            id=row[0], telegram_id=row[1], vk_id=row[2], name=row[3],
            phone=row[4], email=row[5], sale=row[6],
            created_at=datetime.fromisoformat(row[7]) if row[7] else None
        )

class BookingRepository:
    """Репозиторий для работы с бронированиями"""
    
    def __init__(self, db_manager: DatabaseManager):
        self.db_manager = db_manager
    
    async def create(self, booking: Booking) -> int:
        """Создание нового бронирования"""
        async with aiosqlite.connect(self.db_manager.db_path) as db:
            cursor = await db.execute("""
                INSERT INTO bookings (client_id, service_id, start_time, num_durations, num_clients,
                                   status, need_photographer, need_makeuproom, notes, all_price)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                booking.client_id, booking.service_id, booking.start_time.isoformat(),
                booking.num_durations, booking.num_clients, booking.status.value,
                booking.need_photographer, booking.need_makeuproom, booking.notes, booking.all_price
            ))
            await db.commit()
            return cursor.lastrowid
    
    async def get_by_client_id(self, client_id: int) -> List[Booking]:
        """Получение бронирований клиента"""
        async with aiosqlite.connect(self.db_manager.db_path) as db:
            cursor = await db.execute("""
                SELECT * FROM bookings WHERE client_id = ? ORDER BY start_time DESC
            """, (client_id,))
            rows = await cursor.fetchall()
            return [self._row_to_booking(row) for row in rows]
    
    async def get_by_date_range(self, start_date: datetime, end_date: datetime) -> List[Booking]:
        """Получение бронирований за период"""
        async with aiosqlite.connect(self.db_manager.db_path) as db:
            cursor = await db.execute("""
                SELECT * FROM bookings 
                WHERE start_time >= ? AND start_time <= ? 
                ORDER BY start_time
            """, (start_date.isoformat(), end_date.isoformat()))
            rows = await cursor.fetchall()
            return [self._row_to_booking(row) for row in rows]
    
    async def get_conflicting_bookings(self, start_time: datetime, end_time: datetime, exclude_id: Optional[int] = None) -> List[Booking]:
        """Получение конфликтующих бронирований"""
        async with aiosqlite.connect(self.db_manager.db_path) as db:
            query = """
                SELECT * FROM bookings 
                WHERE status IN ('pending', 'confirmed')
                AND start_time < ? AND datetime(start_time, '+' || (num_durations * 60) || ' minutes') > ?
            """
            params = [end_time.isoformat(), start_time.isoformat()]
            
            if exclude_id:
                query += " AND id != ?"
                params.append(exclude_id)
            
            cursor = await db.execute(query, params)
            rows = await cursor.fetchall()
            return [self._row_to_booking(row) for row in rows]
    
    async def update_status(self, booking_id: int, status: BookingStatus) -> bool:
        """Обновление статуса бронирования"""
        async with aiosqlite.connect(self.db_manager.db_path) as db:
            cursor = await db.execute("UPDATE bookings SET status = ? WHERE id = ?", (status.value, booking_id))
            await db.commit()
            return cursor.rowcount > 0
    
    def _row_to_booking(self, row) -> Booking:
        """Преобразование строки БД в модель Booking"""
        return Booking(
            id=row[0], client_id=row[1], service_id=row[2],
            start_time=datetime.fromisoformat(row[3]), num_durations=row[4],
            num_clients=row[5], status=BookingStatus(row[6]), need_photographer=bool(row[7]),
            need_makeuproom=row[8], notes=row[9], all_price=row[10],
            created_at=datetime.fromisoformat(row[11]) if row[11] else None
        )

class AdminRepository:
    """Репозиторий для работы с администраторами"""
    
    def __init__(self, db_manager: DatabaseManager):
        self.db_manager = db_manager
    
    async def get_by_telegram_id(self, telegram_id: int) -> Optional[Admin]:
        """Получение админа по Telegram ID"""
        async with aiosqlite.connect(self.db_manager.db_path) as db:
            cursor = await db.execute("SELECT * FROM admins WHERE telegram_id = ? AND is_active = 1", (telegram_id,))
            row = await cursor.fetchone()
            return self._row_to_admin(row) if row else None
    
    async def get_by_vk_id(self, vk_id: int) -> Optional[Admin]:
        """Получение админа по VK ID"""
        async with aiosqlite.connect(self.db_manager.db_path) as db:
            cursor = await db.execute("SELECT * FROM admins WHERE vk_id = ? AND is_active = 1", (vk_id,))
            row = await cursor.fetchone()
            return self._row_to_admin(row) if row else None
    
    async def create(self, admin: Admin) -> int:
        """Создание нового администратора"""
        async with aiosqlite.connect(self.db_manager.db_path) as db:
            cursor = await db.execute("""
                INSERT INTO admins (telegram_id, vk_id, is_active)
                VALUES (?, ?, ?)
            """, (admin.telegram_id, admin.vk_id, admin.is_active))
            await db.commit()
            return cursor.lastrowid
    
    async def get_all(self) -> List[Admin]:
        """Получение всех администраторов"""
        async with aiosqlite.connect(self.db_manager.db_path) as db:
            cursor = await db.execute("SELECT * FROM admins ORDER BY created_at")
            rows = await cursor.fetchall()
            return [self._row_to_admin(row) for row in rows]
    
    async def update(self, admin: Admin) -> bool:
        """Обновление администратора"""
        async with aiosqlite.connect(self.db_manager.db_path) as db:
            cursor = await db.execute("""
                UPDATE admins SET telegram_id=?, vk_id=?, is_active=?
                WHERE id=?
            """, (admin.telegram_id, admin.vk_id, admin.is_active, admin.id))
            await db.commit()
            return cursor.rowcount > 0
    
    async def delete(self, admin_id: int) -> bool:
        """Удаление администратора"""
        async with aiosqlite.connect(self.db_manager.db_path) as db:
            cursor = await db.execute("DELETE FROM admins WHERE id = ?", (admin_id,))
            await db.commit()
            return cursor.rowcount > 0
    
    def _row_to_admin(self, row) -> Admin:
        """Преобразование строки БД в модель Admin"""
        return Admin(
            id=row[0], telegram_id=row[1], vk_id=row[2],
            is_active=bool(row[3]), created_at=datetime.fromisoformat(row[4]) if row[4] else None
        )