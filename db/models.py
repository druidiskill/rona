from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
from typing import List, Optional


class BookingStatus(Enum):
    PENDING = "pending"
    CONFIRMED = "confirmed"
    CANCELLED = "cancelled"
    COMPLETED = "completed"


@dataclass
class Service:
    """Service model."""

    id: Optional[int] = None
    name: str = ""
    description: str = ""
    base_num_clients: int = 1
    max_num_clients: int = 1
    plus_service_ids: Optional[str] = None
    price_min: float = 0.0
    price_min_weekend: float = 0.0
    fix_price: bool = False
    price_for_extra_client: float = 0.0
    price_for_extra_client_weekend: float = 0.0
    min_duration_minutes: int = 60
    duration_step_minutes: int = 60
    photo_ids: Optional[str] = None
    is_active: bool = True
    created_at: Optional[datetime] = None

    def calculate_price(self, num_clients: int, num_durations: int, is_weekend: bool = False) -> float:
        if self.fix_price:
            return self.price_min if not is_weekend else self.price_min_weekend

        base_price = self.price_min if not is_weekend else self.price_min_weekend
        extra_clients = max(0, num_clients - self.base_num_clients)
        extra_price_per_client = self.price_for_extra_client if not is_weekend else self.price_for_extra_client_weekend
        return base_price + (extra_clients * extra_price_per_client)


@dataclass
class Client:
    """Client model."""

    id: Optional[int] = None
    telegram_id: Optional[int] = None
    vk_id: Optional[int] = None
    name: str = ""
    last_name: str = ""
    phone: Optional[str] = None
    email: Optional[str] = None
    discount_code: Optional[str] = None
    sale: int = 0
    created_at: Optional[datetime] = None


@dataclass
class Booking:
    """Booking model."""

    id: Optional[int] = None
    client_id: int = 0
    service_id: int = 0
    start_time: datetime = datetime.now()
    num_durations: int = 1
    num_clients: int = 1
    status: BookingStatus = BookingStatus.PENDING
    need_photographer: bool = False
    need_makeuproom: int = 0
    notes: Optional[str] = None
    all_price: float = 0.0
    created_at: Optional[datetime] = None

    def get_end_time(self, service: Service) -> datetime:
        duration_minutes = self.num_durations * service.duration_step_minutes
        return self.start_time + timedelta(minutes=duration_minutes)

    def is_weekend(self) -> bool:
        return self.start_time.weekday() >= 5


@dataclass
class Admin:
    """Admin model."""

    id: Optional[int] = None
    telegram_id: Optional[int] = None
    vk_id: Optional[int] = None
    is_active: bool = True
    created_at: Optional[datetime] = None


@dataclass
class BookingWithDetails:
    """Booking with related entities."""

    booking: Booking
    client: Client
    service: Service
    end_time: datetime


@dataclass
class ServiceWithPhotos:
    """Service with photo URLs."""

    service: Service
    photo_urls: List[str] = None


@dataclass
class TimeSlot:
    """Time slot model."""

    start_time: datetime
    end_time: datetime
    is_available: bool = True
    booking_id: Optional[int] = None


@dataclass
class PriceCalculation:
    """Calculated pricing components."""

    base_price: float
    extra_clients_price: float
    photographer_price: float = 0.0
    makeuproom_price: float = 0.0
    total_price: float = 0.0
    discount_amount: float = 0.0
    final_price: float = 0.0


__all__ = [
    "Admin",
    "Booking",
    "BookingStatus",
    "BookingWithDetails",
    "Client",
    "PriceCalculation",
    "Service",
    "ServiceWithPhotos",
    "TimeSlot",
]
