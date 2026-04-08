import asyncio
import os
import unittest
from datetime import datetime
from unittest.mock import patch

from app.integrations.local.calendar.service import GoogleCalendarService


class TestCalendarBooking(unittest.TestCase):
    def setUp(self):
        os.environ["GOOGLE_CALENDAR_ID"] = "test-calendar-id"

    def tearDown(self):
        os.environ.pop("GOOGLE_CALENDAR_ID", None)

    @patch("app.integrations.local.calendar.service.calendar_cache_repo.upsert_event")
    @patch("app.integrations.local.calendar.service.build_calendar_service")
    @patch("app.integrations.local.calendar.service.book_slot")
    def test_create_event_writes_to_calendar(self, mock_book_slot, mock_build_service, mock_cache_upsert):
        mock_build_service.return_value = object()
        mock_book_slot.return_value = {"id": "event-123"}

        service = GoogleCalendarService(time_zone="Europe/Moscow")
        start = datetime(2026, 2, 7, 12, 0, 0)
        end = datetime(2026, 2, 7, 13, 0, 0)

        result = asyncio.run(
            service.create_event(
                title="Test Event",
                description="Test Description",
                start_time=start,
                end_time=end,
            )
        )

        self.assertEqual(result["id"], "event-123")
        mock_book_slot.assert_called_once()
        args, kwargs = mock_book_slot.call_args
        self.assertEqual(args[1], "test-calendar-id")
        self.assertEqual(kwargs["title"], "Test Event")
        self.assertEqual(kwargs["description"], "Test Description")
        self.assertEqual(kwargs["time_zone"], "Europe/Moscow")
        mock_cache_upsert.assert_called_once()


if __name__ == "__main__":
    unittest.main()
