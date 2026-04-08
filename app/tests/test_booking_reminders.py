import unittest
from datetime import datetime
from zoneinfo import ZoneInfo

from app.core.modules.booking.presentation import (
    build_booking_summary,
    build_telegram_calendar_description,
    build_vk_calendar_description,
)
from app.interfaces.messenger.tg.services.booking_reminders import (
    ReminderEvent,
    _build_reminder_text,
    _event_matches_channel,
    _is_primary_booking_event,
)
from app.interfaces.messenger.tg.services.contact_utils import extract_booking_contact_details


class TestBookingReminders(unittest.TestCase):
    def test_primary_booking_event_filters_extra_slot(self):
        description = "Service ID: 9\nLinked Service ID: 3\nСвязано с событием: abc123"
        self.assertFalse(_is_primary_booking_event(description))
        self.assertTrue(_is_primary_booking_event("Service ID: 3\nTelegram: https://t.me/testuser"))

    def test_event_matches_expected_channel(self):
        self.assertTrue(_event_matches_channel("Telegram: https://t.me/testuser", "telegram"))
        self.assertFalse(_event_matches_channel("VK ID: 123", "telegram"))
        self.assertTrue(_event_matches_channel("VK ID: 123", "vk"))
        self.assertFalse(_event_matches_channel("Telegram: https://t.me/testuser", "vk"))

    def test_extract_booking_contact_details_parses_vk_id(self):
        details = extract_booking_contact_details(
            "<b>Кто забронировал</b>\nИван Иванов\n+7 911 123 45 67\nVK ID: 40506735"
        )
        self.assertEqual(details["vk_id"], "40506735")

    def test_build_reminder_text_uses_earliest_event(self):
        tz = ZoneInfo("Europe/Moscow")
        events = [
            ReminderEvent(
                client_id=1,
                chat_id=100,
                event_id="late",
                summary="Second booking",
                start=datetime(2026, 3, 14, 18, 0, tzinfo=tz),
                end=datetime(2026, 3, 14, 19, 0, tzinfo=tz),
            ),
            ReminderEvent(
                client_id=1,
                chat_id=100,
                event_id="early",
                summary="First booking",
                start=datetime(2026, 3, 14, 10, 0, tzinfo=tz),
                end=datetime(2026, 3, 14, 11, 0, tzinfo=tz),
            ),
        ]

        text = _build_reminder_text(events)

        self.assertIn("14", text)
        self.assertIn("10:00", text)
        self.assertIn("11:00", text)
        self.assertIn("First booking", text)
        self.assertNotIn("Second booking", text)

    def test_calendar_descriptions_keep_channel_markers_for_reminders(self):
        summary = build_booking_summary(
            booking_data={
                "name": "Иван",
                "last_name": "Иванов",
                "phone": "+7 999 123 45 67",
                "email": "ivan@example.com",
                "guests_count": 2,
                "extras": [],
                "discount_code": "SALE10",
                "comment": "Комментарий",
            },
            service_name="White Hall",
            service_id=3,
            date_display="05.04.2026",
            time_range="18:00 - 19:00",
            duration_minutes=60,
        )

        tg_description = build_telegram_calendar_description(summary, telegram_link="https://t.me/testuser")
        vk_description = build_vk_calendar_description(summary, vk_id=40506735)

        self.assertIn("Telegram: https://t.me/testuser", tg_description)
        self.assertIn("VK ID: 40506735", vk_description)
        self.assertIn("Service ID: 3", tg_description)
        self.assertIn("Service ID: 3", vk_description)


if __name__ == "__main__":
    unittest.main()
