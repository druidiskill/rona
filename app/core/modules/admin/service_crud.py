from __future__ import annotations

from dataclasses import dataclass

from app.integrations.local.db.models import Service


SERVICE_REQUIRED_FIELDS = [
    "name",
    "description",
    "price_weekday",
    "price_weekend",
    "max_clients",
    "min_duration",
    "step_duration",
]

SERVICE_REQUIRED_FIELD_LABELS = {
    "name": "Название",
    "description": "Описание",
    "price_weekday": "Цена (будни)",
    "price_weekend": "Цена (выходные)",
    "max_clients": "Макс. человек",
    "min_duration": "Длительность",
    "step_duration": "Шаг длительности",
}


def get_missing_service_fields(service_data: dict) -> list[str]:
    return [field for field in SERVICE_REQUIRED_FIELDS if not service_data.get(field)]


def get_missing_service_field_labels(service_data: dict) -> list[str]:
    return [SERVICE_REQUIRED_FIELD_LABELS[field] for field in get_missing_service_fields(service_data)]


def build_service_model(service_data: dict, *, service_id: int | None = None) -> Service:
    max_clients = service_data["max_clients"]
    return Service(
        id=service_id,
        name=service_data["name"],
        description=service_data["description"],
        base_num_clients=service_data.get("base_clients", max_clients),
        max_num_clients=max_clients,
        plus_service_ids=",".join(map(str, service_data.get("extra_services", []))),
        price_min=service_data["price_weekday"],
        price_min_weekend=service_data["price_weekend"],
        fix_price=service_data.get("price_group", 0),
        price_for_extra_client=service_data.get("price_extra_weekday", 0),
        price_for_extra_client_weekend=service_data.get("price_extra_weekend", 0),
        min_duration_minutes=service_data["min_duration"],
        duration_step_minutes=service_data["step_duration"],
        photo_ids=service_data.get("photo_ids"),
        is_active=True,
    )


@dataclass
class ServiceSaveSummary:
    title: str
    service_name: str
    description: str
    price_weekday: float
    price_weekend: float
    max_clients: int
    min_duration_minutes: int
    duration_step_minutes: int
    extras_text: str
    photos_count: int
    service_id: int


def build_service_save_summary(
    service: Service,
    service_data: dict,
    *,
    title: str,
    service_id: int,
) -> ServiceSaveSummary:
    return ServiceSaveSummary(
        title=title,
        service_name=service.name,
        description=service.description,
        price_weekday=service.price_min,
        price_weekend=service.price_min_weekend,
        max_clients=service.max_num_clients,
        min_duration_minutes=service.min_duration_minutes,
        duration_step_minutes=service.duration_step_minutes,
        extras_text=service_data.get("extras", "Не выбрано")
        if title == "Услуга успешно создана!"
        else f"{len(service_data.get('extra_services', []))} услуг",
        photos_count=service_data.get("photos_count", 0),
        service_id=service_id,
    )


def build_service_save_text(summary: ServiceSaveSummary) -> str:
    return (
        f"\u2705 <b>{summary.title}</b>\n\n"
        f"\U0001f4f8 <b>Название:</b> {summary.service_name}\n"
        f"\U0001f4dd <b>Описание:</b> {summary.description}\n"
        f"\U0001f4b0 <b>Цены:</b> {summary.price_weekday}\u20bd - {summary.price_weekend}\u20bd\n"
        f"\U0001f465 <b>Макс. человек:</b> {summary.max_clients}\n"
        f"\u23f0 <b>Длительность:</b> {summary.min_duration_minutes} мин. "
        f"(шаг {summary.duration_step_minutes})\n"
        f"\U0001f527 <b>Доп. услуги:</b> {summary.extras_text}\n"
        f"\U0001f4f8 <b>Фото:</b> {summary.photos_count} шт.\n\n"
        f"\U0001f194 <b>ID услуги:</b> {summary.service_id}"
    )
