from __future__ import annotations


REQUIRED_BOOKING_FIELDS = [
    "date",
    "time",
    "name",
    "last_name",
    "phone",
    "guests_count",
]


BOOKING_FIELD_LABELS = {
    "date": "Дата",
    "time": "Время",
    "name": "Имя",
    "last_name": "Фамилия",
    "phone": "Номер телефона",
    "guests_count": "Количество гостей",
}


def get_missing_booking_fields(booking_data: dict) -> list[str]:
    return [field for field in REQUIRED_BOOKING_FIELDS if not booking_data.get(field)]


def get_missing_booking_field_labels(booking_data: dict) -> list[str]:
    missing_fields = get_missing_booking_fields(booking_data)
    return [BOOKING_FIELD_LABELS[field] for field in missing_fields]
