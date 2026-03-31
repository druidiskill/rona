from __future__ import annotations


def build_add_service_editor_text(service_data: dict) -> str:
    """Текст главного экрана создания услуги."""
    photos_count = service_data.get("photos_count", 0)
    return (
        "\U0001f4f8 <b>Добавление новой услуги</b>\n\n"
        f"\U0001f4dd <b>Название:</b> {service_data.get('name', 'Не указано')}\n"
        f"\U0001f4c4 <b>Описание:</b> {service_data.get('description', 'Не указано')}\n"
        f"\U0001f4b0 <b>Цена (будни):</b> {service_data.get('price_weekday', 'Не указано')}\u20bd\n"
        f"\U0001f4b0 <b>Цена (выходные):</b> {service_data.get('price_weekend', 'Не указано')}\u20bd\n"
        f"\U0001f464 <b>Цена за доп. человека (будни):</b> {service_data.get('price_extra_weekday', 'Не указано')}\u20bd\n"
        f"\U0001f464 <b>Цена за доп. человека (выходные):</b> {service_data.get('price_extra_weekend', 'Не указано')}\u20bd\n"
        f"\U0001f465 <b>Цена от 10 человек:</b> {service_data.get('price_group', 'Не указано')}\u20bd\n"
        f"\U0001f465 <b>Макс. человек:</b> {service_data.get('max_clients', 'Не указано')}\n"
        f"\U0001f527 <b>Доп. услуги:</b> {service_data.get('extras', 'Не указано')}\n"
        f"\u23f0 <b>Длительность:</b> {service_data.get('duration', 'Не указано')}\n"
        f"\U0001f4f8 <b>Фото:</b> {photos_count} шт.\n\n"
        "Выберите параметр для настройки:"
    )


def build_edit_service_editor_text(service_data: dict) -> str:
    """Текст главного экрана редактирования услуги."""
    description = service_data.get("description", "Не указано")
    if len(description) > 50:
        description = f"{description[:50]}..."

    price_text = f"{service_data.get('price_weekday', 0)}\u20bd - {service_data.get('price_weekend', 0)}\u20bd"
    extra_weekday = service_data.get("price_extra_weekday", 0)
    if extra_weekday > 0:
        price_text += f" (+{extra_weekday}\u20bd доп.)"

    extras_text = service_data.get("extras", "Не выбрано")
    extra_services = service_data.get("extra_services", [])
    if extra_services:
        extras_text = f"{len(extra_services)} услуг"

    photos_count = service_data.get("photos_count", 0)
    photos_text = f"{photos_count} шт." if photos_count > 0 else "Не загружены"
    duration_text = f"{service_data.get('min_duration', 0)} мин. (шаг {service_data.get('step_duration', 0)})"

    return (
        "\U0001f527 <b>Редактирование услуги</b>\n\n"
        f"\U0001f4f8 <b>Название:</b> {service_data.get('name', 'Не указано')}\n"
        f"\U0001f4dd <b>Описание:</b> {description}\n"
        f"\U0001f4b0 <b>Цены:</b> {price_text}\n"
        f"\U0001f465 <b>Макс. человек:</b> {service_data.get('max_clients', 'Не указано')}\n"
        f"\U0001f527 <b>Доп. услуги:</b> {extras_text}\n"
        f"\u23f0 <b>Длительность:</b> {duration_text}\n"
        f"\U0001f4f8 <b>Фото:</b> {photos_text}\n\n"
        "Выберите параметр для редактирования:"
    )


def parse_positive_price(raw_value: str, *, allow_zero: bool = False) -> float:
    value = float(raw_value.strip())
    if allow_zero:
        if value < 0:
            raise ValueError("Цена не может быть отрицательной")
    elif value <= 0:
        raise ValueError("Цена должна быть положительной")
    return value


def parse_positive_int(raw_value: str) -> int:
    value = int(raw_value.strip())
    if value <= 0:
        raise ValueError("Значение должно быть положительным")
    return value


def parse_duration_pair(raw_value: str) -> tuple[int, int]:
    parts = raw_value.strip().split()
    if len(parts) != 2:
        raise ValueError("Неверный формат")
    min_duration = int(parts[0])
    step_duration = int(parts[1])
    if min_duration <= 0 or step_duration <= 0:
        raise ValueError("Значения должны быть положительными")
    return min_duration, step_duration
