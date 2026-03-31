def normalize_min_duration_minutes(raw_value: int | None) -> int:
    min_duration = int(raw_value or 60)
    if min_duration < 60:
        min_duration = 60
    if min_duration % 60 != 0:
        min_duration = ((min_duration // 60) + 1) * 60
    return min_duration


def normalize_max_guests(raw_value: int | None) -> int:
    max_guests = int(raw_value or 1)
    return max(1, max_guests)


def format_full_name(data: dict) -> str:
    first = (data.get("name") or "").strip()
    last = (data.get("last_name") or "").strip()
    full = " ".join(part for part in [first, last] if part)
    return full or "Не указано"


def format_optional_text(value: str | None, empty_label: str = "Не указан") -> str:
    text = (value or "").strip()
    return text or empty_label


def normalize_phone10(phone: str | None) -> str | None:
    if not phone:
        return None
    digits = "".join(ch for ch in str(phone) if ch.isdigit())
    if len(digits) == 11 and digits.startswith(("7", "8")):
        digits = digits[1:]
    return digits if len(digits) == 10 else None
