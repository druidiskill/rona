from core.booking.common import normalize_max_guests


def _format_money(value: float | int | None) -> str:
    amount = float(value or 0)
    if amount.is_integer():
        return str(int(amount))
    return f"{amount:.2f}".rstrip("0").rstrip(".")


def build_service_details_text(service, *, html: bool = False) -> str:
    base_clients = int(service.base_num_clients or service.max_num_clients or 1)
    max_clients = normalize_max_guests(service.max_num_clients or base_clients)
    min_duration = int(service.min_duration_minutes or 60)

    title = f"📸 <b>{service.name}</b>" if html else f"📸 {service.name}"
    prices_label = "💰 <b>Цены:</b>" if html else "💰 Цены:"
    guests_label = "👥 <b>Количество людей:</b>" if html else "👥 Количество людей:"
    duration_label = "⏰ <b>Длительность:</b>" if html else "⏰ Длительность:"
    extras_label = "📅 <b>Дополнительные услуги:</b>" if html else "📅 Дополнительные услуги:"
    footer = (
        "<i>Важно: до 9:00 и после 21:00 действует двойная аренда зала и гримерной.</i>"
        if html
        else "Важно: до 9:00 и после 21:00 действует двойная аренда зала и гримерной."
    )

    lines = [
        title,
        "",
        (service.description or "").strip(),
        "",
        prices_label,
        f"• Будни: {_format_money(service.price_min)}₽",
        f"• Выходные: {_format_money(service.price_min_weekend)}₽",
    ]

    if service.id != 9:
        lines.extend(
            [
                "",
                guests_label,
                f"• Входит в стоимость: до {base_clients} чел.",
                f"• Максимум: {max_clients} чел.",
            ]
        )
        if base_clients != max_clients:
            lines.append(f"• Дополнительно: {_format_money(service.price_for_extra_client)}₽/чел.")

    lines.extend(
        [
            "",
            duration_label,
            f"• Минимум: {min_duration} мин.",
            "• Бронирование только полными часами.",
            "",
            extras_label,
            "• Фотограф: 11 500₽",
            "• Гримерка: 200/250₽/час",
            "• Розжиг камина: 400₽",
            "• Прокат (белый халат и полотенце): 200₽",
            "",
            footer,
        ]
    )

    return "\n".join(lines).strip()
