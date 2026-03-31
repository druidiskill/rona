from typing import List, Optional

from .database import DatabaseManager
from .models import BookingWithDetails, Client
from .repositories import BookingRepository, ClientRepository, ServiceRepository


class ClientService:
    """Service layer for working with clients."""

    def __init__(self, db_manager: DatabaseManager):
        self.db_manager = db_manager
        self.client_repo = ClientRepository(db_manager)
        self.booking_repo = BookingRepository(db_manager)
        self.service_repo = ServiceRepository(db_manager)

    async def get_or_create_client(
        self,
        telegram_id: Optional[int] = None,
        vk_id: Optional[int] = None,
        name: Optional[str] = None,
        phone: Optional[str] = None,
        email: Optional[str] = None,
    ) -> Client:
        if telegram_id is None and vk_id is None:
            raise ValueError("Need telegram_id or vk_id")

        client = None
        if telegram_id is not None:
            client = await self.client_repo.get_by_telegram_id(telegram_id)
        if not client and vk_id is not None:
            client = await self.client_repo.get_by_vk_id(vk_id)

        if not client:
            new_client = Client(
                telegram_id=telegram_id,
                vk_id=vk_id,
                name=name or "Пользователь",
                phone=phone,
                email=email,
            )
            client_id = await self.client_repo.create(new_client)
            client = await self.client_repo.get_by_id(client_id)

        return client

    async def get_client_bookings(self, client_id: int) -> List[BookingWithDetails]:
        bookings = await self.booking_repo.get_by_client_id(client_id)
        booking_details: List[BookingWithDetails] = []

        for booking in bookings:
            service = await self.service_repo.get_by_id(booking.service_id)
            if not service:
                continue

            client = await self.client_repo.get_by_id(booking.client_id)
            if not client:
                continue

            end_time = booking.get_end_time(service)
            booking_details.append(
                BookingWithDetails(
                    booking=booking,
                    client=client,
                    service=service,
                    end_time=end_time,
                )
            )

        return booking_details


class BookingService:
    """Service layer for bookings."""

    def __init__(self, db_manager: DatabaseManager):
        self.db_manager = db_manager
        self.booking_repo = BookingRepository(db_manager)
        self.service_repo = ServiceRepository(db_manager)
        self.client_repo = ClientRepository(db_manager)


__all__ = ["BookingService", "ClientService"]
