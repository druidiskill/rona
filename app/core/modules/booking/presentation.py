from __future__ import annotations

from app.core.modules.booking.extra_services import format_extra_labels, has_extra_named


def _format_full_name(data: dict) -> str:
    first = str(data.get("name") or "").strip()
    last = str(data.get("last_name") or "").strip()
    full_name = " ".join(part for part in (first, last) if part)
    return full_name or "Не указано"


def _optional_text(value: str | None, empty_label: str = "Не указан") -> str:
    text = str(value or "").strip()
    return text or empty_label


def format_extras_display(extras: list | None, extra_labels: dict | None = None) -> str:
    return format_extra_labels(extras or [], extra_labels)


def build_booking_summary(
    *,
    booking_data: dict,
    service_name: str,
    service_id: int,
    date_display: str,
    time_range: str,
    duration_minutes: int,
) -> dict:
    extras = booking_data.get("extras", [])
    extra_labels = booking_data.get("extra_labels") or {}
    return {
        "service_name": service_name,
        "service_id": service_id,
        "date_display": date_display,
        "time_range": time_range,
        "duration_minutes": int(duration_minutes or 60),
        "full_name": _format_full_name(booking_data),
        "email": _optional_text(booking_data.get("email")),
        "phone": _optional_text(booking_data.get("phone")),
        "guests_count": booking_data.get("guests_count") or "Не указано",
        "extras_display": format_extras_display(extras, extra_labels),
        "discount_code": _optional_text(booking_data.get("discount_code")),
        "comment": _optional_text(booking_data.get("comment")),
        "need_photographer": "Да" if has_extra_named(extras, extra_labels, "фотограф") else "Нет",
        "need_makeuproom": "Да" if has_extra_named(extras, extra_labels, "гример") else "Нет",
    }


def build_telegram_calendar_description(summary: dict, *, telegram_link: str) -> str:
    return f"""
<b>Кто забронировал</b>
{summary["full_name"]}
email: {summary["email"]}
{summary["phone"]}
Telegram: {telegram_link}

<b>Какой зал вы хотите забронировать?</b>
{summary["service_name"]}

Service ID: {summary["service_id"]}

<b>Какое количество гостей планируется, включая фотографа?</b>
{summary["guests_count"]}

<b>Нужна ли гримерная за час до съемки?</b>
{summary["need_makeuproom"]}

<b>Нужен ли фотограф?</b>
{summary["need_photographer"]}

<b>Дополнительные услуги:</b>
{summary["extras_display"]}

<b>Код для скидки:</b>
{summary["discount_code"]}

<b>Комментарий:</b>
{summary["comment"]}

<b><u>ВНИМАНИЕ</u></b> Автоматически на вашу электронную почту приходит подтверждение о <b><u>предварительном бронировании времени</u></b><u>.</u> Вам нужно:

<ul><li>дождаться информации о предоплате</li><li>отправить нам скриншот оплаты в течение 24-х часов</li><li>получить от нас подтверждение, что желаемая дата и время забронировано.</li></ul>

Пожалуйста, ознакомьтесь с <a href="https://www.google.com/url?q=https%3A%2F%2Fvk.com%2Fpages%3Fhash%3Ddd2aea6878aabba105%26oid%3D-174809315%26p%3D%25D0%259F%25D0%25A0%25D0%2590%25D0%2592%25D0%2598%25D0%259B%25D0%2590_%25D0%2590%25D0%25A0%25D0%2595%25D0%259D%25D0%2594%25D0%25AB_%25D0%25A4%25D0%259E%25D0%25A2%25D0%259E%25D0%25A1%25D0%25A2%25D0%25A3%25D0%2594%25D0%2598%25D0%2598&amp;sa=D&amp;source=calendar&amp;ust=1762503000000000&amp;usg=AOvVaw0LR6y1Ukh_SRdIeJXIrHOT" target="_blank" data-link-id="34" rel="noopener noreferrer">правилами нашей фотостудии</a>
    """.strip()


def build_vk_calendar_description(summary: dict, *, vk_id: int) -> str:
    return (
        f"<b>Кто забронировал</b>\n{summary['full_name']}\n"
        f"email: {summary['email']}\n"
        f"{summary['phone']}\n"
        f"VK ID: {vk_id}\n\n"
        f"<b>Какой зал вы хотите забронировать?</b>\n{summary['service_name']}\n\n"
        f"Service ID: {summary['service_id']}\n\n"
        f"<b>Какое количество гостей планируется?</b>\n{summary['guests_count']}\n\n"
        f"<b>Дополнительные услуги:</b>\n{summary['extras_display']}\n\n"
        f"<b>Код для скидки:</b>\n{summary['discount_code']}\n\n"
        f"<b>Комментарий:</b>\n{summary['comment']}"
    )


def build_telegram_admin_text(summary: dict, *, phone_html: str) -> str:
    return (
        "📅 <b>Новая бронь</b>\n\n"
        f"🎯 Услуга: {summary['service_name']}\n"
        f"📅 Дата: {summary['date_display']}\n"
        f"🕒 Время: {summary['time_range']}\n"
        f"👤 Клиент: {summary['full_name']}\n"
        f"📱 Телефон: {phone_html}\n"
        f"👥 Гостей: {summary['guests_count']}\n"
        f"➕ Доп. услуги: {summary['extras_display']}\n"
        f"🏷️ Код для скидки: {summary['discount_code']}\n"
        f"💬 Комментарий: {summary['comment']}\n"
    )


def build_vk_to_telegram_admin_text(summary: dict, *, vk_id: int) -> str:
    return (
        "📅 <b>Новая бронь (VK)</b>\n\n"
        f"📸 Услуга: {summary['service_name']}\n"
        f"📅 Дата: {summary['date_display']}\n"
        f"🕒 Время: {summary['time_range']}\n"
        f"👤 Клиент: {summary['full_name']}\n"
        f"📱 Телефон: {summary['phone']}\n"
        f"👥 Гостей: {summary['guests_count']}\n"
        f"➕ Доп. услуги: {summary['extras_display']}\n"
        f"🏷️ Код для скидки: {summary['discount_code']}\n"
        f"💬 Комментарий: {summary['comment']}\n"
        f"VK ID: {vk_id}\n"
    )


def build_vk_admin_text(summary: dict, *, source_label: str, contact_line: str | None = None) -> str:
    lines = [
        f"📅 Новая бронь ({source_label})",
        "",
        f"📸 Услуга: {summary['service_name']}",
        f"📅 Дата: {summary['date_display']}",
        f"🕒 Время: {summary['time_range']}",
        f"👤 Клиент: {summary['full_name']}",
        f"📱 Телефон: {summary['phone']}",
        f"👥 Гостей: {summary['guests_count']}",
        f"➕ Доп. услуги: {summary['extras_display']}",
        f"🏷️ Код для скидки: {summary['discount_code']}",
        f"💬 Комментарий: {summary['comment']}",
    ]
    if contact_line:
        lines.append(contact_line)
    return "\n".join(lines)


def build_telegram_confirmation_text(summary: dict) -> str:
    return (
        f"✅ <b>Бронирование оформлено!</b>\n\n"
        f"📅 <b>Дата:</b> {summary['date_display']}\n"
        f"🕒 <b>Время:</b> {summary['time_range']}\n"
        f"👤 <b>Клиент:</b> {summary['full_name']}\n"
        f"📱 <b>Телефон:</b> {summary['phone']}\n"
        f"👥 <b>Гостей:</b> {summary['guests_count']}\n"
        f"🏷️ <b>Код для скидки:</b> {summary['discount_code']}\n"
        f"💬 <b>Комментарий:</b> {summary['comment']}\n"
        f"⏰ <b>Продолжительность:</b> {summary['duration_minutes']} мин.\n\n"
        f"🎯 <b>Услуга:</b> {summary['service_name']}\n\n"
        f"📩 <b>Спасибо за бронирование! Ожидайте информацию о предоплате.</b>"
    )


def build_vk_confirmation_text(summary: dict, *, calendar_event_created: bool) -> str:
    lines = [
        "✅ Бронирование подтверждено!",
        "",
        f"📅 Дата: {summary['date_display']}",
        f"🕒 Время: {summary['time_range']}",
        f"👤 Клиент: {summary['full_name']}",
        f"📱 Телефон: {summary['phone']}",
        f"👥 Гостей: {summary['guests_count']}",
        f"🏷️ Код для скидки: {summary['discount_code']}",
        f"💬 Комментарий: {summary['comment']}",
        f"⏰ Продолжительность: {summary['duration_minutes']} мин.",
        f"🎯 Услуга: {summary['service_name']}",
    ]
    if calendar_event_created:
        lines.append("📅 Событие создано в календаре")
    lines.extend(["", "Дождитесь информацию о предоплате."])
    return "\n".join(lines)
