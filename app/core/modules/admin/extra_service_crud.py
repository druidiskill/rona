from __future__ import annotations

from dataclasses import dataclass

from app.integrations.local.db.models import ExtraService


EXTRA_SERVICE_REQUIRED_FIELDS = ["name", "price_text"]

EXTRA_SERVICE_REQUIRED_FIELD_LABELS = {
    "name": "Название",
    "price_text": "Цена / подпись",
}


def get_missing_extra_service_field_labels(extra_service_data: dict) -> list[str]:
    return [
        EXTRA_SERVICE_REQUIRED_FIELD_LABELS[field]
        for field in EXTRA_SERVICE_REQUIRED_FIELDS
        if not str(extra_service_data.get(field, "") or "").strip()
    ]


def build_extra_service_model(extra_service_data: dict, *, extra_service_id: int | None = None) -> ExtraService:
    return ExtraService(
        id=extra_service_id,
        name=str(extra_service_data.get("name", "") or "").strip(),
        description=str(extra_service_data.get("description", "") or "").strip(),
        price_text=str(extra_service_data.get("price_text", "") or "").strip(),
        sort_order=int(extra_service_data.get("sort_order", 0) or 0),
        is_active=bool(extra_service_data.get("is_active", True)),
    )


@dataclass
class ExtraServiceSaveSummary:
    title: str
    extra_service_name: str
    description: str
    price_text: str
    sort_order: int
    extra_service_id: int


def build_extra_service_save_summary(
    extra_service: ExtraService,
    *,
    title: str,
    extra_service_id: int,
) -> ExtraServiceSaveSummary:
    return ExtraServiceSaveSummary(
        title=title,
        extra_service_name=extra_service.name,
        description=extra_service.description or "Не указано",
        price_text=extra_service.price_text or "Не указано",
        sort_order=extra_service.sort_order,
        extra_service_id=extra_service_id,
    )


def build_extra_service_save_text(summary: ExtraServiceSaveSummary) -> str:
    return (
        f"✅ <b>{summary.title}</b>\n\n"
        f"📦 <b>Название:</b> {summary.extra_service_name}\n"
        f"📄 <b>Описание:</b> {summary.description}\n"
        f"💰 <b>Цена / подпись:</b> {summary.price_text}\n"
        f"🔢 <b>Порядок:</b> {summary.sort_order}\n\n"
        f"🆔 <b>ID доп. услуги:</b> {summary.extra_service_id}"
    )
