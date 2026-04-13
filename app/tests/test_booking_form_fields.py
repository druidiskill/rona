import unittest

from app.core.modules.booking.form_fields import (
    get_booking_misc_fields,
    get_booking_required_fields,
    get_booking_required_menu_fields,
    get_missing_booking_field_labels,
)


class TestBookingFormFields(unittest.TestCase):
    def test_required_fields_include_identity_fields_when_not_prefilled_from_db(self):
        booking_data = {"db_prefilled_fields": []}

        self.assertEqual(
            get_booking_required_fields(booking_data),
            ["date", "time", "guests_count", "duration", "name", "last_name", "phone"],
        )
        self.assertEqual(
            get_booking_required_menu_fields(booking_data),
            ["date_time", "guests_count", "duration", "name", "last_name", "phone"],
        )
        self.assertIn("discount_code", get_booking_misc_fields(booking_data))

    def test_prefilled_identity_fields_move_to_misc(self):
        booking_data = {"db_prefilled_fields": ["name", "last_name", "phone", "discount_code"]}

        self.assertEqual(
            get_booking_required_fields(booking_data),
            ["date", "time", "guests_count", "duration"],
        )
        self.assertEqual(
            get_booking_misc_fields(booking_data),
            ["name", "last_name", "phone", "discount_code", "comment", "extras", "email"],
        )

    def test_missing_labels_collapse_date_and_time_into_one_label(self):
        booking_data = {
            "db_prefilled_fields": ["name", "last_name", "phone", "discount_code"],
            "date": None,
            "time": None,
            "guests_count": None,
            "duration": 60,
        }

        self.assertEqual(
            get_missing_booking_field_labels(booking_data),
            ["Дата и время", "Количество гостей"],
        )

    def test_discount_code_is_not_required_even_when_empty(self):
        booking_data = {
            "db_prefilled_fields": [],
            "date": "2026-04-14",
            "time": "12:00 - 13:00",
            "guests_count": 2,
            "duration": 60,
            "name": "Иван",
            "last_name": "Иванов",
            "phone": "+7 900 000 00 00",
            "discount_code": None,
        }

        self.assertEqual(get_missing_booking_field_labels(booking_data), [])


if __name__ == "__main__":
    unittest.main()
