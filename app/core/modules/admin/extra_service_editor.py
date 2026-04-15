from __future__ import annotations


def build_add_extra_service_editor_text(extra_service_data: dict) -> str:
    return (
        "📦 <b>Добавление доп. услуги</b>\n\n"
        f"📝 <b>Название:</b> {extra_service_data.get('name', 'Не указано')}\n"
        f"📄 <b>Описание:</b> {extra_service_data.get('description', 'Не указано')}\n"
        f"💰 <b>Цена / подпись:</b> {extra_service_data.get('price_text', 'Не указано')}\n"
        f"🔢 <b>Порядок:</b> {extra_service_data.get('sort_order', '0')}\n\n"
        "Выберите параметр для настройки:"
    )


def build_edit_extra_service_editor_text(extra_service_data: dict) -> str:
    description = extra_service_data.get("description", "Не указано")
    if len(description) > 80:
        description = f"{description[:77]}..."

    return (
        "📦 <b>Редактирование доп. услуги</b>\n\n"
        f"📝 <b>Название:</b> {extra_service_data.get('name', 'Не указано')}\n"
        f"📄 <b>Описание:</b> {description}\n"
        f"💰 <b>Цена / подпись:</b> {extra_service_data.get('price_text', 'Не указано')}\n"
        f"🔢 <b>Порядок:</b> {extra_service_data.get('sort_order', '0')}\n\n"
        "Выберите параметр для редактирования:"
    )


def get_extra_service_field_prompt(mode: str, field: str) -> str:
    prompts = {
        ("add", "name"): "📝 <b>Название доп. услуги</b>\n\nВведите название:",
        ("edit", "name"): "📝 <b>Редактирование названия</b>\n\nВведите новое название:",
        ("add", "description"): "📄 <b>Описание доп. услуги</b>\n\nВведите описание:",
        ("edit", "description"): "📄 <b>Редактирование описания</b>\n\nВведите новое описание:",
        ("add", "price_text"): "💰 <b>Цена / подпись</b>\n\nВведите текст цены, например: 200/250 ₽/час",
        ("edit", "price_text"): "💰 <b>Редактирование цены / подписи</b>\n\nВведите новый текст цены:",
        ("add", "sort_order"): "🔢 <b>Порядок отображения</b>\n\nВведите число. Меньше число - выше в списке.",
        ("edit", "sort_order"): "🔢 <b>Редактирование порядка</b>\n\nВведите новое число. Меньше число - выше в списке.",
    }
    return prompts[(mode, field)]


def parse_sort_order(raw_value: str) -> int:
    return int(raw_value.strip())
