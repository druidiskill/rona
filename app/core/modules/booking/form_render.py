from __future__ import annotations

from app.core.modules.booking.form_fields import get_booking_misc_fields, get_booking_required_menu_fields


def _field_line(*, mark: str, label: str, value: str, bold: bool) -> str:
    if bold:
        return f"{mark} <b>{label}:</b> {value}"
    return f"{mark} {label}: {value}"


def _section_title(title: str, *, bold: bool) -> str:
    return f"<b>{title}</b>" if bold else title


def _date_time_value(date_display: str, time_display: str) -> str:
    date_text = (date_display or "").strip()
    time_text = (time_display or "").strip()
    if date_text and time_text:
        return f"{date_text}, {time_text}"
    if date_text:
        return f"{date_text}, Не выбрано"
    if time_text:
        return time_text
    return "Не указано"


def build_booking_form_text(
    *,
    service_name: str,
    date_display: str,
    time_display: str,
    name_display: str,
    last_name_display: str,
    phone_display: str,
    discount_code_display: str,
    comment_display: str,
    guests_display: str,
    duration_display: str,
    extras_display: str,
    email_display: str,
    required_mark: str,
    optional_mark: str,
    instruction_text: str,
    bold: bool = False,
    discount_code_mark: str | None = None,
    comment_mark: str | None = None,
    duration_mark: str | None = None,
    extras_mark: str | None = None,
    email_mark: str | None = None,
    db_prefilled_fields: list[str] | None = None,
) -> str:
    title = (
        f"📝 <b>Бронирование услуги: {service_name}</b>"
        if bold
        else f"📝 Бронирование услуги: {service_name}"
    )
    subtitle = (
        "📋 <b>Заполните данные для бронирования:</b>"
        if bold
        else "📋 Заполните данные для бронирования:"
    )
    booking_data = {"db_prefilled_fields": list(db_prefilled_fields or [])}
    field_values = {
        "date_time": _date_time_value(date_display, time_display),
        "name": name_display,
        "last_name": last_name_display,
        "phone": phone_display,
        "discount_code": discount_code_display,
        "comment": comment_display,
        "guests_count": guests_display,
        "duration": duration_display,
        "extras": extras_display,
        "email": email_display,
    }
    field_labels = {
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
    field_marks = {
        "date_time": required_mark,
        "name": required_mark,
        "last_name": required_mark,
        "phone": required_mark,
        "guests_count": required_mark,
        "duration": duration_mark or required_mark,
        "discount_code": discount_code_mark or optional_mark,
        "comment": comment_mark or optional_mark,
        "extras": extras_mark or optional_mark,
        "email": email_mark or optional_mark,
    }

    lines = [title, "", subtitle, "", _section_title("Обязательные поля", bold=bold)]
    for field in get_booking_required_menu_fields(booking_data):
        lines.append(
            _field_line(
                mark=field_marks[field],
                label=field_labels[field],
                value=field_values[field],
                bold=bold,
            )
        )
    lines.extend(["", _section_title("Прочее", bold=bold)])
    for field in get_booking_misc_fields(booking_data):
        lines.append(
            _field_line(
                mark=field_marks[field],
                label=field_labels[field],
                value=field_values[field],
                bold=bold,
            )
        )
    lines.extend(["", instruction_text])
    return "\n".join(lines)


def build_booking_other_text(
    *,
    service_name: str,
    name_display: str,
    last_name_display: str,
    phone_display: str,
    discount_code_display: str,
    comment_display: str,
    extras_display: str,
    email_display: str,
    optional_mark: str,
    instruction_text: str,
    bold: bool = False,
    discount_code_mark: str | None = None,
    comment_mark: str | None = None,
    extras_mark: str | None = None,
    email_mark: str | None = None,
    db_prefilled_fields: list[str] | None = None,
) -> str:
    title = f"📝 <b>Прочее: {service_name}</b>" if bold else f"📝 Прочее: {service_name}"
    booking_data = {"db_prefilled_fields": list(db_prefilled_fields or [])}
    field_values = {
        "name": name_display,
        "last_name": last_name_display,
        "phone": phone_display,
        "discount_code": discount_code_display,
        "comment": comment_display,
        "extras": extras_display,
        "email": email_display,
    }
    field_labels = {
        "name": "Имя",
        "last_name": "Фамилия",
        "phone": "Номер телефона",
        "discount_code": "Код для скидки",
        "comment": "Комментарий",
        "extras": "Доп. услуги",
        "email": "E-mail",
    }
    field_marks = {
        "name": optional_mark,
        "last_name": optional_mark,
        "phone": optional_mark,
        "discount_code": discount_code_mark or optional_mark,
        "comment": comment_mark or optional_mark,
        "extras": extras_mark or optional_mark,
        "email": email_mark or optional_mark,
    }

    lines = [title, ""]
    for field in get_booking_misc_fields(booking_data):
        lines.append(
            _field_line(
                mark=field_marks[field],
                label=field_labels[field],
                value=field_values[field],
                bold=bold,
            )
        )
    lines.extend(["", instruction_text])
    return "\n".join(lines)
