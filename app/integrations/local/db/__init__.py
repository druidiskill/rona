"""Primary access point for the database layer."""

from .database import DatabaseManager, db_manager
from .models import (
    Admin,
    Booking,
    BookingStatus,
    BookingWithDetails,
    Client,
    PriceCalculation,
    Service,
    ServiceWithPhotos,
    TimeSlot,
)
from .repositories import (
    AdminRepository,
    BookingReminderLogRepository,
    BookingRepository,
    ClientRepository,
    ServiceRepository,
)
from .services import BookingService, ClientService
from .faq_repo import FaqEntry, FaqRepository
from .support_repo import SupportRepository

service_repo = ServiceRepository(db_manager)
client_repo = ClientRepository(db_manager)
booking_repo = BookingRepository(db_manager)
admin_repo = AdminRepository(db_manager)
support_repo = SupportRepository(db_manager)
faq_repo = FaqRepository(db_manager)
booking_reminder_log_repo = BookingReminderLogRepository(db_manager)

booking_service = BookingService(db_manager)
client_service = ClientService(db_manager)

__all__ = [
    "Admin",
    "AdminRepository",
    "Booking",
    "BookingReminderLogRepository",
    "BookingRepository",
    "BookingService",
    "BookingStatus",
    "BookingWithDetails",
    "Client",
    "ClientRepository",
    "ClientService",
    "DatabaseManager",
    "FaqEntry",
    "FaqRepository",
    "PriceCalculation",
    "Service",
    "ServiceWithPhotos",
    "ServiceRepository",
    "SupportRepository",
    "TimeSlot",
    "admin_repo",
    "booking_reminder_log_repo",
    "booking_repo",
    "booking_service",
    "client_repo",
    "client_service",
    "db_manager",
    "faq_repo",
    "service_repo",
    "support_repo",
]
