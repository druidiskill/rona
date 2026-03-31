from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime, time, timedelta
from zoneinfo import ZoneInfo

from db import booking_reminder_log_repo, client_repo
from telegram_bot.services.calendar_queries import list_events
from telegram_bot.services.contact_utils import extract_booking_contact_details, normalize_phone
from config import REMINDER_HOUR_MSK


logger = logging.getLogger(__name__)

MOSCOW_TZ = ZoneInfo("Europe/Moscow")
CHECK_INTERVAL_SECONDS = 30


@dataclass
class ReminderEvent:
    client_id: int
    chat_id: int
    event_id: str
    summary: str
    start: datetime
    end: datetime | None


def _is_primary_booking_event(description: str) -> bool:
    text = description or ""
    if "Linked Service ID:" in text:
        return False
    if "Service ID: 9" in text and "Связано с событием:" in text:
        return False
    return True


def _event_matches_channel(description: str, channel: str) -> bool:
    text = description or ""
    if channel == "telegram":
        return "Telegram:" in text or "Telegram ID:" in text
    if channel == "vk":
        return "VK ID:" in text
    return False


def _build_reminder_text(events: list[ReminderEvent]) -> str:
    events_sorted = sorted(events, key=lambda item: item.start)
    first = events_sorted[0] if events_sorted else None
    if first:
        month_names = [
            "января", "февраля", "марта", "апреля", "мая", "июня",
            "июля", "августа", "сентября", "октября", "ноября", "декабря",
        ]
        day = first.start.day
        month_label = month_names[first.start.month - 1]
        date_label = f"{day} {month_label}"
        time_start = first.start.strftime("%H:%M")
        time_end = first.end.strftime("%H:%M") if first.end else ""
        time_range = f"с {time_start} до {time_end} часов" if time_end else f"в {time_start}"
        hall_label = first.summary or "зал"
    else:
        date_label = "завтра"
        time_range = "в назначенное время"
        hall_label = "зал"
    return (
        "Здравствуйте!\n"
        f"Ждём вас завтра {date_label} {time_range} в нашей студии, {hall_label}.\n\n"
        "Напоминаем!\n\n"
        "ОПЛАТА НАЛИЧНЫМИ перед съёмкой. \n\n"
        "Адрес: ул.Володи Дубинина 3, домофон 2 (сигнал идёт долго, ждите).\n"
        "Студия находится в жилом доме, поэтому не нужно беспокоить соседей и нажимать другие цифры на домофоне.\n\n"
        "Сменная обувь обязательна. Бахилы не являются сменной обувью.\n"
        "При нахождении в зале White в обуви, подошва заклеивается бумажным скотчем(предоставляем).\n\n"
        "Съёмочный час-55 минут.\n\n"
        "Как нас найти\n"
        "https://vk.com/clip-174809315_456239321?c=1\n\n"
        "Правила студии\n"
        "https://vk.com/pages?oid=-174809315&p=%D0%9F%D0%A0%D0%90%D0%92%D0%98%D0%9B%D0%90_%D0%90%D0%A0%D0%95%D0%9D%D0%94%D0%AB_%D0%A4%D0%9E%D0%A2%D0%9E%D0%A1%D0%A2%D0%A3%D0%94%D0%98%D0%98\n\n"
        "‼️Пожалуйста, ознакомьте с данной информацией и правилами студии всех гостей."
    )


async def collect_tomorrow_reminder_events(channel: str) -> dict[int, list[ReminderEvent]]:
    now_msk = datetime.now(MOSCOW_TZ)
    reminder_date = now_msk.date().isoformat()
    target_date = (now_msk + timedelta(days=1)).date()
    period_start = datetime.combine(target_date, time.min, tzinfo=MOSCOW_TZ)
    period_end = datetime.combine(target_date + timedelta(days=1), time.min, tzinfo=MOSCOW_TZ)

    events = await list_events(period_start, period_end, max_results=250)
    grouped: dict[int, list[ReminderEvent]] = {}

    for event in events:
        description = event.get("description") or ""
        if not _is_primary_booking_event(description):
            continue
        if not _event_matches_channel(description, channel):
            continue

        start = event.get("start")
        event_id = event.get("id")
        if not start or not event_id:
            continue

        details = extract_booking_contact_details(description)
        phone = normalize_phone(details.get("phone"))
        if not phone:
            continue

        client = await client_repo.get_by_phone(phone)
        if not client:
            continue

        chat_id = client.telegram_id if channel == "telegram" else client.vk_id
        if not chat_id:
            continue

        if await booking_reminder_log_repo.was_sent(channel, event_id, reminder_date):
            continue

        grouped.setdefault(client.id, []).append(
            ReminderEvent(
                client_id=client.id,
                chat_id=chat_id,
                event_id=event_id,
                summary=event.get("summary") or "Бронирование",
                start=start,
                end=event.get("end"),
            )
        )

    return grouped


async def send_telegram_booking_reminders(bot) -> int:
    reminders_by_client = await collect_tomorrow_reminder_events("telegram")
    reminder_date = datetime.now(MOSCOW_TZ).date().isoformat()
    sent_events_count = 0

    for events in reminders_by_client.values():
        try:
            await bot.send_message(
                chat_id=events[0].chat_id,
                text=_build_reminder_text(events),
            )
        except Exception as exc:
            logger.warning("Не удалось отправить Telegram-напоминание chat_id=%s: %s", events[0].chat_id, exc)
            continue

        for event in events:
            if await booking_reminder_log_repo.mark_sent(
                "telegram",
                event.event_id,
                event.client_id,
                event.start.date().isoformat(),
                reminder_date,
            ):
                sent_events_count += 1

    return sent_events_count


async def send_vk_booking_reminders(bot) -> int:
    reminders_by_client = await collect_tomorrow_reminder_events("vk")
    reminder_date = datetime.now(MOSCOW_TZ).date().isoformat()
    sent_events_count = 0

    for events in reminders_by_client.values():
        try:
            await bot.api.messages.send(
                peer_id=events[0].chat_id,
                random_id=0,
                message=_build_reminder_text(events),
            )
        except Exception as exc:
            logger.warning("Не удалось отправить VK-напоминание peer_id=%s: %s", events[0].chat_id, exc)
            continue

        for event in events:
            if await booking_reminder_log_repo.mark_sent(
                "vk",
                event.event_id,
                event.client_id,
                event.start.date().isoformat(),
                reminder_date,
            ):
                sent_events_count += 1

    return sent_events_count


async def run_booking_reminder_loop(sender_name: str, send_callback) -> None:
    last_processed_date = None

    while True:
        now_msk = datetime.now(MOSCOW_TZ)
        if now_msk.hour == REMINDER_HOUR_MSK and last_processed_date != now_msk.date():
            try:
                sent_count = await send_callback()
                logger.info("%s reminders processed for %s events", sender_name, sent_count)
            except Exception:
                logger.exception("Ошибка фоновой рассылки напоминаний для %s", sender_name)
            last_processed_date = now_msk.date()

        await asyncio.sleep(CHECK_INTERVAL_SECONDS)
