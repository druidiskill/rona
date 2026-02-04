from typing import Optional, List
from datetime import datetime
import aiosqlite

from database.database import DatabaseManager
from database.models import Client, Booking, BookingWithDetails, BookingStatus, Service
from database.repositories import ClientRepository, BookingRepository, ServiceRepository


class ClientService:
    """Сервис для работы с клиентами"""
    
    def __init__(self, db_manager: DatabaseManager):
        self.db_manager = db_manager
        self.client_repo = ClientRepository(db_manager)
        self.booking_repo = BookingRepository(db_manager)
        self.service_repo = ServiceRepository(db_manager)
    
    async def get_or_create_client(
        self, 
        telegram_id: int, 
        name: Optional[str] = None,
        phone: Optional[str] = None,
        email: Optional[str] = None
    ) -> Client:
        """Получение или создание клиента по Telegram ID"""
        client = await self.client_repo.get_by_telegram_id(telegram_id)
        
        if not client:
            # Создаем нового клиента
            new_client = Client(
                telegram_id=telegram_id,
                name=name or "Пользователь",
                phone=phone,
                email=email
            )
            client_id = await self.client_repo.create(new_client)
            client = await self.client_repo.get_by_id(client_id)
        
        return client
    
    async def get_client_bookings(self, client_id: int) -> List[BookingWithDetails]:
        """Получение бронирований клиента с деталями"""
        bookings = await self.booking_repo.get_by_client_id(client_id)
        booking_details = []
        
        for booking in bookings:
            # Получаем сервис
            service = await self.service_repo.get_by_id(booking.service_id)
            if not service:
                continue
            
            # Получаем клиента
            client = await self.client_repo.get_by_id(booking.client_id)
            if not client:
                continue
            
            # Вычисляем время окончания
            from datetime import timedelta
            duration_minutes = booking.num_durations * service.duration_step_minutes
            end_time = booking.start_time + timedelta(minutes=duration_minutes)
            
            booking_detail = BookingWithDetails(
                booking=booking,
                client=client,
                service=service,
                end_time=end_time
            )
            booking_details.append(booking_detail)
        
        return booking_details


class BookingService:
    """Сервис для работы с бронированиями"""
    
    def __init__(self, db_manager: DatabaseManager):
        self.db_manager = db_manager
        self.booking_repo = BookingRepository(db_manager)
        self.service_repo = ServiceRepository(db_manager)
        self.client_repo = ClientRepository(db_manager)

