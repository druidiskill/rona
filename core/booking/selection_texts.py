from __future__ import annotations


def build_date_selection_text(*, html: bool) -> str:
    if html:
        return "📅 <b>Выберите дату:</b>\n\nВыберите подходящий день:"
    return "📅 Выберите дату:"


def build_pick_date_first_text(*, html: bool) -> str:
    if html:
        return "Сначала выберите дату"
    return "Сначала выберите дату."


def build_duration_hint(*, is_all_day: bool, min_duration: int, selected_duration: int) -> str:
    if is_all_day:
        return "режим: весь день до 21:00"
    return f"минимум {int(min_duration)} мин., выбрано: {selected_duration} мин."


def build_time_selection_text(
    *,
    date_display: str,
    html: bool,
    duration_hint: str | None = None,
) -> str:
    if html:
        base = f"🕒 <b>Выберите время на {date_display}</b>"
        if duration_hint:
            return f"{base}\n\nДоступные слоты ({duration_hint}):"
        return f"{base}\n\nДоступные слоты:"
    return f"🕒 Выберите время на {date_display}:"


def build_no_slots_text(*, date_display: str, html: bool) -> str:
    if html:
        return (
            f"⚠️ <b>На {date_display} нет свободных слотов</b>\n\n"
            "Пожалуйста, выберите другую дату."
        )
    return "На выбранную дату нет свободных слотов."


def build_choose_guests_text(*, html: bool) -> str:
    if html:
        return "👥 <b>Выберите количество гостей:</b>"
    return "👥 Выберите количество гостей:"


def build_choose_extras_text(*, html: bool) -> str:
    if html:
        return "➕ <b>Дополнительные услуги:</b>\n\nВыберите нужные опции:\n\n"
    return "➕ Выберите дополнительные услуги:"
