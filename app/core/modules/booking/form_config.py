from __future__ import annotations


BOOKING_FORM_FIELDS = {
    "date": {"label": "Дата", "required": True},
    "time": {"label": "Время", "required": True},
    "name": {"label": "Имя", "required": True},
    "last_name": {"label": "Фамилия", "required": True},
    "phone": {"label": "Номер телефона", "required": True},
    "discount_code": {"label": "Код для скидки", "required": False},
    "comment": {"label": "Комментарий", "required": False},
    "guests_count": {"label": "Количество гостей", "required": True},
    "duration": {"label": "Продолжительность", "required": False},
    "extras": {"label": "Доп. услуги", "required": False},
    "email": {"label": "E-mail", "required": False},
}


def get_booking_field_label(field: str) -> str:
    return BOOKING_FORM_FIELDS[field]["label"]


def is_booking_field_required(field: str) -> bool:
    return bool(BOOKING_FORM_FIELDS[field]["required"])


def is_booking_field_filled(field: str, booking_data: dict) -> bool:
    return bool(booking_data.get(field))


def get_booking_field_status(
    field: str,
    booking_data: dict,
    *,
    required_filled: str,
    required_empty: str,
    optional_filled: str,
    optional_empty: str,
) -> str:
    filled = is_booking_field_filled(field, booking_data)
    if is_booking_field_required(field):
        return required_filled if filled else required_empty
    return optional_filled if filled else optional_empty
