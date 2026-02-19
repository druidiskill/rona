from database.database import DatabaseManager, db_manager
from database.repositories import ServiceRepository, ClientRepository, BookingRepository, AdminRepository
from database.support_repo import SupportRepository
from database.faq_repo import FaqRepository
from database.services import BookingService, ClientService
from database.models import Service, Client, Booking, Admin, BookingStatus, BookingWithDetails, TimeSlot, PriceCalculation

# Инициализация репозиториев
service_repo = ServiceRepository(db_manager)
client_repo = ClientRepository(db_manager)
booking_repo = BookingRepository(db_manager)
admin_repo = AdminRepository(db_manager)
support_repo = SupportRepository(db_manager)
faq_repo = FaqRepository(db_manager)

# Инициализация сервисов
booking_service = BookingService(db_manager)
client_service = ClientService(db_manager)

__all__ = [
    'DatabaseManager', 'db_manager',
    'ServiceRepository', 'ClientRepository', 'BookingRepository', 'AdminRepository',
    'SupportRepository', 'FaqRepository',
    'BookingService', 'ClientService',
    'Service', 'Client', 'Booking', 'Admin', 'BookingStatus', 'BookingWithDetails', 'TimeSlot', 'PriceCalculation',
    'service_repo', 'client_repo', 'booking_repo', 'admin_repo', 'support_repo', 'faq_repo',
    'booking_service', 'client_service'
]
