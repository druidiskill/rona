from database.database import DatabaseManager, db_manager
from database.repositories import ServiceRepository, ClientRepository, BookingRepository, AdminRepository
from database.services import BookingService, ClientService
from database.models import Service, Client, Booking, Admin, BookingStatus, BookingWithDetails, TimeSlot, PriceCalculation

# Инициализация репозиториев
service_repo = ServiceRepository(db_manager)
client_repo = ClientRepository(db_manager)
booking_repo = BookingRepository(db_manager)
admin_repo = AdminRepository(db_manager)

# Инициализация сервисов
booking_service = BookingService(db_manager)
client_service = ClientService(db_manager)

__all__ = [
    'DatabaseManager', 'db_manager',
    'ServiceRepository', 'ClientRepository', 'BookingRepository', 'AdminRepository',
    'BookingService', 'ClientService',
    'Service', 'Client', 'Booking', 'Admin', 'BookingStatus', 'BookingWithDetails', 'TimeSlot', 'PriceCalculation',
    'service_repo', 'client_repo', 'booking_repo', 'admin_repo',
    'booking_service', 'client_service'
]
