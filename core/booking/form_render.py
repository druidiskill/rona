from __future__ import annotations


def _field_line(*, mark: str, label: str, value: str, bold: bool) -> str:
    if bold:
        return f"{mark} <b>{label}:</b> {value}"
    return f"{mark} {label}: {value}"


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

    lines = [
        title,
        "",
        subtitle,
        "",
        _field_line(mark=required_mark, label="Дата", value=date_display, bold=bold),
        _field_line(mark=required_mark, label="Время", value=time_display, bold=bold),
        _field_line(mark=required_mark, label="Имя", value=name_display, bold=bold),
        _field_line(mark=required_mark, label="Фамилия", value=last_name_display, bold=bold),
        _field_line(mark=required_mark, label="Номер телефона", value=phone_display, bold=bold),
        _field_line(mark=discount_code_mark or optional_mark, label="Код для скидки", value=discount_code_display, bold=bold),
        _field_line(mark=comment_mark or optional_mark, label="Комментарий", value=comment_display, bold=bold),
        _field_line(mark=required_mark, label="Количество гостей", value=guests_display, bold=bold),
        _field_line(mark=duration_mark or optional_mark, label="Продолжительность", value=duration_display, bold=bold),
        _field_line(mark=extras_mark or optional_mark, label="Доп. услуги", value=extras_display, bold=bold),
        _field_line(mark=email_mark or optional_mark, label="E-mail", value=email_display, bold=bold),
        "",
        instruction_text,
    ]
    return "\n".join(lines)
