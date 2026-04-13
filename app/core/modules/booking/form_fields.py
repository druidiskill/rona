from __future__ import annotations


ALWAYS_REQUIRED_BOOKING_FIELDS = [
    "date",
    "time",
    "guests_count",
    "duration",
]

DB_DEPENDENT_BOOKING_FIELDS = [
    "name",
    "last_name",
    "phone",
]

ALWAYS_MISC_BOOKING_FIELDS = [
    "discount_code",
    "comment",
    "extras",
    "email",
]


BOOKING_FIELD_LABELS = {
    "date": "Дата",
    "time": "Время",
    "date_time": "Дата и время",
    "name": "Имя",
    "last_name": "Фамилия",
    "phone": "Номер телефона",
    "discount_code": "Код для скидки",
    "comment": "Комментарий",
    "guests_count": "Количество гостей",
    "duration": "Продолжительность",
    "extras": "Доп. услуги",
    "email": "E-mail",
}


def get_db_prefilled_fields(booking_data: dict) -> set[str]:
    return set(booking_data.get("db_prefilled_fields") or [])


def get_booking_required_fields(booking_data: dict) -> list[str]:
    db_prefilled_fields = get_db_prefilled_fields(booking_data)
    fields = list(ALWAYS_REQUIRED_BOOKING_FIELDS)
    for field in DB_DEPENDENT_BOOKING_FIELDS:
        if field not in db_prefilled_fields:
            fields.append(field)
    return fields


def get_booking_misc_fields(booking_data: dict) -> list[str]:
    db_prefilled_fields = get_db_prefilled_fields(booking_data)
    fields = [field for field in DB_DEPENDENT_BOOKING_FIELDS if field in db_prefilled_fields]
    fields.extend(ALWAYS_MISC_BOOKING_FIELDS)
    return fields


def get_booking_required_menu_fields(booking_data: dict) -> list[str]:
    fields = ["date_time", "guests_count", "duration"]
    db_prefilled_fields = get_db_prefilled_fields(booking_data)
    for field in DB_DEPENDENT_BOOKING_FIELDS:
        if field not in db_prefilled_fields:
            fields.append(field)
    return fields


def get_missing_booking_fields(booking_data: dict) -> list[str]:
    return [field for field in get_booking_required_fields(booking_data) if not booking_data.get(field)]


def get_missing_booking_field_labels(booking_data: dict) -> list[str]:
    missing_fields = get_missing_booking_fields(booking_data)
    labels: list[str] = []
    if "date" in missing_fields or "time" in missing_fields:
        labels.append(BOOKING_FIELD_LABELS["date_time"])
    for field in missing_fields:
        if field in {"date", "time"}:
            continue
        labels.append(BOOKING_FIELD_LABELS[field])
    return labels
