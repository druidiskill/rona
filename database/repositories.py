import aiosqlite
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
from database.models import Service, Client, Booking, Admin, BookingStatus, BookingWithDetails, TimeSlot
from database.database import DatabaseManager

class ServiceRepository:
    """Р РµРїРѕР·РёС‚РѕСЂРёР№ РґР»СЏ СЂР°Р±РѕС‚С‹ СЃ СѓСЃР»СѓРіР°РјРё"""
    
    def __init__(self, db_manager: DatabaseManager):
        self.db_manager = db_manager
    
    async def get_all(self) -> List[Service]:
        """РџРѕР»СѓС‡РµРЅРёРµ РІСЃРµС… СѓСЃР»СѓРі"""
        async with aiosqlite.connect(self.db_manager.db_path) as db:
            cursor = await db.execute("""
                SELECT id, name, description, COALESCE(base_num_clients, max_num_clients) AS base_num_clients, max_num_clients, plus_service_ids, price_min, price_min_weekend, fix_price, price_for_extra_client, price_for_extra_client_weekend, min_duration_minutes, duration_step_minutes, photo_ids, is_active, created_at FROM services ORDER BY name
            """)
            rows = await cursor.fetchall()
            return [self._row_to_service(row) for row in rows]
    
    async def get_all_active(self) -> List[Service]:
        """РџРѕР»СѓС‡РµРЅРёРµ РІСЃРµС… Р°РєС‚РёРІРЅС‹С… СѓСЃР»СѓРі"""
        async with aiosqlite.connect(self.db_manager.db_path) as db:
            cursor = await db.execute("""
                SELECT id, name, description, COALESCE(base_num_clients, max_num_clients) AS base_num_clients, max_num_clients, plus_service_ids, price_min, price_min_weekend, fix_price, price_for_extra_client, price_for_extra_client_weekend, min_duration_minutes, duration_step_minutes, photo_ids, is_active, created_at FROM services WHERE is_active = 1 ORDER BY name
            """)
            rows = await cursor.fetchall()
            return [self._row_to_service(row) for row in rows]
    
    async def get_by_id(self, service_id: int) -> Optional[Service]:
        """РџРѕР»СѓС‡РµРЅРёРµ СѓСЃР»СѓРіРё РїРѕ ID"""
        async with aiosqlite.connect(self.db_manager.db_path) as db:
            cursor = await db.execute("SELECT id, name, description, COALESCE(base_num_clients, max_num_clients) AS base_num_clients, max_num_clients, plus_service_ids, price_min, price_min_weekend, fix_price, price_for_extra_client, price_for_extra_client_weekend, min_duration_minutes, duration_step_minutes, photo_ids, is_active, created_at FROM services WHERE id = ?", (service_id,))
            row = await cursor.fetchone()
            return self._row_to_service(row) if row else None
    
    async def create(self, service: Service) -> int:
        """РЎРѕР·РґР°РЅРёРµ РЅРѕРІРѕР№ СѓСЃР»СѓРіРё"""
        async with aiosqlite.connect(self.db_manager.db_path) as db:
            cursor = await db.execute("""
                INSERT INTO services (name, description, base_num_clients, max_num_clients, plus_service_ids, 
                                   price_min, price_min_weekend, fix_price, price_for_extra_client,
                                   price_for_extra_client_weekend, min_duration_minutes, 
                                   duration_step_minutes, photo_ids, is_active)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                service.name, service.description, int(service.base_num_clients or service.max_num_clients or 1), service.max_num_clients,
                service.plus_service_ids, service.price_min, service.price_min_weekend,
                service.fix_price, service.price_for_extra_client,
                service.price_for_extra_client_weekend, service.min_duration_minutes,
                service.duration_step_minutes, service.photo_ids, service.is_active
            ))
            await db.commit()
            return cursor.lastrowid
    
    async def update(self, service: Service) -> bool:
        """РћР±РЅРѕРІР»РµРЅРёРµ СѓСЃР»СѓРіРё"""
        async with aiosqlite.connect(self.db_manager.db_path) as db:
            cursor = await db.execute("""
                UPDATE services SET name=?, description=?, base_num_clients=?, max_num_clients=?, plus_service_ids=?,
                                  price_min=?, price_min_weekend=?, fix_price=?, price_for_extra_client=?,
                                  price_for_extra_client_weekend=?, min_duration_minutes=?,
                                  duration_step_minutes=?, photo_ids=?, is_active=?
                WHERE id=?
            """, (
                service.name, service.description, int(service.base_num_clients or service.max_num_clients or 1), service.max_num_clients,
                service.plus_service_ids, service.price_min, service.price_min_weekend,
                service.fix_price, service.price_for_extra_client,
                service.price_for_extra_client_weekend, service.min_duration_minutes,
                service.duration_step_minutes, service.photo_ids, service.is_active,
                service.id
            ))
            await db.commit()
            return cursor.rowcount > 0
    
    def _row_to_service(self, row) -> Service:
        """РџСЂРµРѕР±СЂР°Р·РѕРІР°РЅРёРµ СЃС‚СЂРѕРєРё Р‘Р” РІ РјРѕРґРµР»СЊ Service"""
        return Service(
            id=row[0], name=row[1], description=row[2], base_num_clients=row[3], max_num_clients=row[4], plus_service_ids=row[5], price_min=row[6], price_min_weekend=row[7], fix_price=bool(row[8]), price_for_extra_client=row[9], price_for_extra_client_weekend=row[10], min_duration_minutes=row[11], duration_step_minutes=row[12], photo_ids=row[13], is_active=bool(row[14]), created_at=datetime.fromisoformat(row[15]) if row[15] else None
        )

class ClientRepository:
    """Р РµРїРѕР·РёС‚РѕСЂРёР№ РґР»СЏ СЂР°Р±РѕС‚С‹ СЃ РєР»РёРµРЅС‚Р°РјРё"""

    CLIENT_SELECT = """
        SELECT id, telegram_id, vk_id, name, last_name, phone, email, discount_code, sale, created_at
        FROM clients
    """
    
    def __init__(self, db_manager: DatabaseManager):
        self.db_manager = db_manager
    
    async def get_by_telegram_id(self, telegram_id: int) -> Optional[Client]:
        """РџРѕР»СѓС‡РµРЅРёРµ РєР»РёРµРЅС‚Р° РїРѕ Telegram ID"""
        async with aiosqlite.connect(self.db_manager.db_path) as db:
            cursor = await db.execute(
                f"{self.CLIENT_SELECT} WHERE telegram_id = ?",
                (telegram_id,),
            )
            row = await cursor.fetchone()
            return self._row_to_client(row) if row else None
    
    async def get_by_vk_id(self, vk_id: int) -> Optional[Client]:
        """РџРѕР»СѓС‡РµРЅРёРµ РєР»РёРµРЅС‚Р° РїРѕ VK ID"""
        async with aiosqlite.connect(self.db_manager.db_path) as db:
            cursor = await db.execute(
                f"{self.CLIENT_SELECT} WHERE vk_id = ?",
                (vk_id,),
            )
            row = await cursor.fetchone()
            return self._row_to_client(row) if row else None
    
    async def get_by_phone(self, phone: str) -> Optional[Client]:
        """РџРѕР»СѓС‡РµРЅРёРµ РєР»РёРµРЅС‚Р° РїРѕ РЅРѕРјРµСЂСѓ С‚РµР»РµС„РѕРЅР°"""
        async with aiosqlite.connect(self.db_manager.db_path) as db:
            cursor = await db.execute(
                f"{self.CLIENT_SELECT} WHERE phone = ?",
                (phone,),
            )
            row = await cursor.fetchone()
            return self._row_to_client(row) if row else None
    
    async def get_by_id(self, client_id: int) -> Optional[Client]:
        """РџРѕР»СѓС‡РµРЅРёРµ РєР»РёРµРЅС‚Р° РїРѕ ID"""
        async with aiosqlite.connect(self.db_manager.db_path) as db:
            cursor = await db.execute(
                f"{self.CLIENT_SELECT} WHERE id = ?",
                (client_id,),
            )
            row = await cursor.fetchone()
            return self._row_to_client(row) if row else None
    
    async def create(self, client: Client) -> int:
        """РЎРѕР·РґР°РЅРёРµ РЅРѕРІРѕРіРѕ РєР»РёРµРЅС‚Р°"""
        async with aiosqlite.connect(self.db_manager.db_path) as db:
            cursor = await db.execute("""
                INSERT INTO clients (telegram_id, vk_id, name, last_name, phone, email, discount_code, sale)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (client.telegram_id, client.vk_id, client.name, client.last_name, client.phone, client.email, client.discount_code, client.sale))
            await db.commit()
            return cursor.lastrowid
    
    async def update(self, client: Client) -> bool:
        """РћР±РЅРѕРІР»РµРЅРёРµ РєР»РёРµРЅС‚Р°"""
        async with aiosqlite.connect(self.db_manager.db_path) as db:
            cursor = await db.execute("""
                UPDATE clients SET telegram_id=?, vk_id=?, name=?, last_name=?, phone=?, email=?, discount_code=?, sale=?
                WHERE id=?
            """, (client.telegram_id, client.vk_id, client.name, client.last_name, client.phone, client.email, client.discount_code, client.sale, client.id))
            await db.commit()
            return cursor.rowcount > 0
    
    async def get_all(self) -> List[Client]:
        """РџРѕР»СѓС‡РµРЅРёРµ РІСЃРµС… РєР»РёРµРЅС‚РѕРІ"""
        async with aiosqlite.connect(self.db_manager.db_path) as db:
            cursor = await db.execute(f"{self.CLIENT_SELECT} ORDER BY created_at DESC")
            rows = await cursor.fetchall()
            return [self._row_to_client(row) for row in rows]
    
    def _row_to_client(self, row) -> Client:
        """РџСЂРµРѕР±СЂР°Р·РѕРІР°РЅРёРµ СЃС‚СЂРѕРєРё Р‘Р” РІ РјРѕРґРµР»СЊ Client"""
        return Client(
            id=row[0], telegram_id=row[1], vk_id=row[2], name=row[3],
            last_name=row[4], phone=row[5], email=row[6], discount_code=row[7], sale=row[8],
            created_at=datetime.fromisoformat(row[9]) if row[9] else None
        )

class BookingRepository:
    """Р РµРїРѕР·РёС‚РѕСЂРёР№ РґР»СЏ СЂР°Р±РѕС‚С‹ СЃ Р±СЂРѕРЅРёСЂРѕРІР°РЅРёСЏРјРё"""
    
    def __init__(self, db_manager: DatabaseManager):
        self.db_manager = db_manager
    
    async def create(self, booking: Booking) -> int:
        """РЎРѕР·РґР°РЅРёРµ РЅРѕРІРѕРіРѕ Р±СЂРѕРЅРёСЂРѕРІР°РЅРёСЏ"""
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
        """РџРѕР»СѓС‡РµРЅРёРµ Р±СЂРѕРЅРёСЂРѕРІР°РЅРёР№ РєР»РёРµРЅС‚Р°"""
        async with aiosqlite.connect(self.db_manager.db_path) as db:
            cursor = await db.execute("""
                SELECT * FROM bookings WHERE client_id = ? ORDER BY start_time DESC
            """, (client_id,))
            rows = await cursor.fetchall()
            return [self._row_to_booking(row) for row in rows]
    
    async def get_by_date_range(self, start_date: datetime, end_date: datetime) -> List[Booking]:
        """РџРѕР»СѓС‡РµРЅРёРµ Р±СЂРѕРЅРёСЂРѕРІР°РЅРёР№ Р·Р° РїРµСЂРёРѕРґ"""
        async with aiosqlite.connect(self.db_manager.db_path) as db:
            cursor = await db.execute("""
                SELECT * FROM bookings 
                WHERE start_time >= ? AND start_time <= ? 
                ORDER BY start_time
            """, (start_date.isoformat(), end_date.isoformat()))
            rows = await cursor.fetchall()
            return [self._row_to_booking(row) for row in rows]
    
    async def get_conflicting_bookings(self, start_time: datetime, end_time: datetime, exclude_id: Optional[int] = None) -> List[Booking]:
        """РџРѕР»СѓС‡РµРЅРёРµ РєРѕРЅС„Р»РёРєС‚СѓСЋС‰РёС… Р±СЂРѕРЅРёСЂРѕРІР°РЅРёР№"""
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
        """РћР±РЅРѕРІР»РµРЅРёРµ СЃС‚Р°С‚СѓСЃР° Р±СЂРѕРЅРёСЂРѕРІР°РЅРёСЏ"""
        async with aiosqlite.connect(self.db_manager.db_path) as db:
            cursor = await db.execute("UPDATE bookings SET status = ? WHERE id = ?", (status.value, booking_id))
            await db.commit()
            return cursor.rowcount > 0
    
    def _row_to_booking(self, row) -> Booking:
        """РџСЂРµРѕР±СЂР°Р·РѕРІР°РЅРёРµ СЃС‚СЂРѕРєРё Р‘Р” РІ РјРѕРґРµР»СЊ Booking"""
        return Booking(
            id=row[0], client_id=row[1], service_id=row[2],
            start_time=datetime.fromisoformat(row[3]), num_durations=row[4],
            num_clients=row[5], status=BookingStatus(row[6]), need_photographer=bool(row[7]),
            need_makeuproom=row[8], notes=row[9], all_price=row[10],
            created_at=datetime.fromisoformat(row[11]) if row[11] else None
        )

class AdminRepository:
    """Р РµРїРѕР·РёС‚РѕСЂРёР№ РґР»СЏ СЂР°Р±РѕС‚С‹ СЃ Р°РґРјРёРЅРёСЃС‚СЂР°С‚РѕСЂР°РјРё"""
    
    def __init__(self, db_manager: DatabaseManager):
        self.db_manager = db_manager
    
    async def get_by_telegram_id(self, telegram_id: int) -> Optional[Admin]:
        """РџРѕР»СѓС‡РµРЅРёРµ Р°РґРјРёРЅР° РїРѕ Telegram ID"""
        async with aiosqlite.connect(self.db_manager.db_path) as db:
            cursor = await db.execute("SELECT * FROM admins WHERE telegram_id = ? AND is_active = 1", (telegram_id,))
            row = await cursor.fetchone()
            return self._row_to_admin(row) if row else None
    
    async def get_by_vk_id(self, vk_id: int) -> Optional[Admin]:
        """РџРѕР»СѓС‡РµРЅРёРµ Р°РґРјРёРЅР° РїРѕ VK ID"""
        async with aiosqlite.connect(self.db_manager.db_path) as db:
            cursor = await db.execute("SELECT * FROM admins WHERE vk_id = ? AND is_active = 1", (vk_id,))
            row = await cursor.fetchone()
            return self._row_to_admin(row) if row else None
    
    async def create(self, admin: Admin) -> int:
        """РЎРѕР·РґР°РЅРёРµ РЅРѕРІРѕРіРѕ Р°РґРјРёРЅРёСЃС‚СЂР°С‚РѕСЂР°"""
        async with aiosqlite.connect(self.db_manager.db_path) as db:
            cursor = await db.execute("""
                INSERT INTO admins (telegram_id, vk_id, is_active)
                VALUES (?, ?, ?)
            """, (admin.telegram_id, admin.vk_id, admin.is_active))
            await db.commit()
            return cursor.lastrowid
    
    async def get_all(self) -> List[Admin]:
        """РџРѕР»СѓС‡РµРЅРёРµ РІСЃРµС… Р°РґРјРёРЅРёСЃС‚СЂР°С‚РѕСЂРѕРІ"""
        async with aiosqlite.connect(self.db_manager.db_path) as db:
            cursor = await db.execute("SELECT * FROM admins ORDER BY created_at")
            rows = await cursor.fetchall()
            return [self._row_to_admin(row) for row in rows]
    
    async def update(self, admin: Admin) -> bool:
        """РћР±РЅРѕРІР»РµРЅРёРµ Р°РґРјРёРЅРёСЃС‚СЂР°С‚РѕСЂР°"""
        async with aiosqlite.connect(self.db_manager.db_path) as db:
            cursor = await db.execute("""
                UPDATE admins SET telegram_id=?, vk_id=?, is_active=?
                WHERE id=?
            """, (admin.telegram_id, admin.vk_id, admin.is_active, admin.id))
            await db.commit()
            return cursor.rowcount > 0
    
    async def delete(self, admin_id: int) -> bool:
        """РЈРґР°Р»РµРЅРёРµ Р°РґРјРёРЅРёСЃС‚СЂР°С‚РѕСЂР°"""
        async with aiosqlite.connect(self.db_manager.db_path) as db:
            cursor = await db.execute("DELETE FROM admins WHERE id = ?", (admin_id,))
            await db.commit()
            return cursor.rowcount > 0
    
    def _row_to_admin(self, row) -> Admin:
        """РџСЂРµРѕР±СЂР°Р·РѕРІР°РЅРёРµ СЃС‚СЂРѕРєРё Р‘Р” РІ РјРѕРґРµР»СЊ Admin"""
        return Admin(
            id=row[0], telegram_id=row[1], vk_id=row[2],
            is_active=bool(row[3]), created_at=datetime.fromisoformat(row[4]) if row[4] else None
        )


class BookingReminderLogRepository:
    """Репозиторий журнала отправленных напоминаний."""

    def __init__(self, db_manager: DatabaseManager):
        self.db_manager = db_manager

    async def was_sent(self, channel: str, event_id: str, reminder_date: str) -> bool:
        async with aiosqlite.connect(self.db_manager.db_path) as db:
            cursor = await db.execute(
                """
                SELECT 1
                FROM booking_reminder_log
                WHERE channel = ? AND event_id = ? AND reminder_date = ?
                LIMIT 1
                """,
                (channel, event_id, reminder_date),
            )
            return await cursor.fetchone() is not None

    async def mark_sent(
        self,
        channel: str,
        event_id: str,
        client_id: int,
        booking_date: str,
        reminder_date: str,
    ) -> bool:
        async with aiosqlite.connect(self.db_manager.db_path) as db:
            cursor = await db.execute(
                """
                INSERT OR IGNORE INTO booking_reminder_log (
                    channel, event_id, client_id, booking_date, reminder_date
                )
                VALUES (?, ?, ?, ?, ?)
                """,
                (channel, event_id, client_id, booking_date, reminder_date),
            )
            await db.commit()
            return cursor.rowcount > 0
