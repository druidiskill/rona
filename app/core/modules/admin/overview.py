from __future__ import annotations


def build_admin_stats_text(*, services_count: int) -> str:
    return (
        "📊 <b>Статистика студии</b>\n\n"
        f"📸 <b>Услуги:</b> {services_count} активных\n"
        "📅 <b>Бронирования сегодня:</b> [будет добавлено]\n"
        "💰 <b>Выручка за месяц:</b> [будет добавлено]\n"
        "👥 <b>Новых клиентов:</b> [будет добавлено]"
    )


def build_admin_services_text(services: list) -> str:
    text = "📸 <b>Управление услугами</b>\n\n"
    for service in services:
        status = "✅ Активна" if service.is_active else "❌ Неактивна"
        text += f"📸 <b>{service.name}</b>\n"
        text += f"💰 {service.price_min}₽ - {service.price_min_weekend}₽\n"
        text += f"👥 До {service.max_num_clients} чел.\n"
        text += f"⏰ {service.min_duration_minutes} мин.\n"
        text += f"📊 {status}\n\n"
    return text


def build_admin_clients_text(client_rows: list[dict]) -> str:
    text = "👥 <b>Управление клиентами</b>\n\n"
    text += f"📊 Всего клиентов: {len(client_rows)}\n\n"

    if not client_rows:
        return text + "Клиентов пока нет."

    text += "📋 <b>Последние клиенты:</b>\n"
    for row in client_rows[:5]:
        text += f"👤 {row['name']}\n"
        if row.get("telegram_label"):
            text += f"   Telegram: {row['telegram_label']}\n"
        if row.get("phone_display"):
            text += f"   📞 {row['phone_display']}\n"
        text += "\n"
    return text


def build_admin_admins_text(admin_rows: list[dict]) -> str:
    text = "👨‍💼 <b>Управление администраторами</b>\n\n"
    for row in admin_rows:
        status = "✅ Активен" if row["is_active"] else "❌ Неактивен"
        text += f"👤 ID: {row['id']}\n"
        text += f"📱 Telegram: {row['telegram_label']}\n"
        text += f"📧 VK: {row['vk_label']}\n"
        text += f"📊 Статус: {status}\n\n"
    return text
