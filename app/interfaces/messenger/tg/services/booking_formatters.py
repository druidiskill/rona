from datetime import datetime, timedelta


def format_booking_date(date_value) -> str:
    if not date_value:
        return "Не выбрано"
    try:
        return datetime.strptime(str(date_value), "%Y-%m-%d").strftime("%d.%m.%Y")
    except Exception:
        return str(date_value)


def format_booking_time_range(time_value, duration_minutes: int) -> str:
    if not time_value:
        return "Не выбрано"
    try:
        start_str = str(time_value).split(" - ")[0].strip()
        start_dt = datetime.strptime(start_str, "%H:%M")
        end_dt = start_dt + timedelta(minutes=int(duration_minutes or 60))
        return f"{start_dt.strftime('%H:%M')} - {end_dt.strftime('%H:%M')}"
    except Exception:
        return str(time_value)


def format_booking_guests(guests_value) -> str:
    if guests_value is None:
        return "Не указано"
    return str(guests_value)


def format_extras_display(extras: list[str]) -> str:
    extras_labels = {
        "photographer": "Фотограф",
        "makeuproom": "Гримерка",
        "fireplace": "Розжиг камина",
        "rental": "Прокат: халат и полотенце",
    }
    if not extras:
        return "Нет"
    return ", ".join(extras_labels.get(extra, extra) for extra in extras)

