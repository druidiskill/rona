import unittest

from app.core.modules.admin.extra_service_crud import get_missing_extra_service_field_labels
from app.core.modules.booking.extra_services import (
    build_extra_service_booking_label,
    build_extra_service_label_map,
    format_extra_labels,
    has_extra_named,
)
from app.integrations.local.db.models import ExtraService


class TestExtraServices(unittest.TestCase):
    def test_label_map_and_formatting_support_ids(self):
        extras = [
            ExtraService(id=1, name="Фотограф", price_text="11 500 ₽"),
            ExtraService(id=2, name="Гримерка", price_text="200/250 ₽/час"),
        ]
        labels = build_extra_service_label_map(extras)

        self.assertEqual(labels, {"1": "Фотограф", "2": "Гримерка"})
        self.assertEqual(format_extra_labels([1, "2"], labels), "Фотограф, Гримерка")

    def test_booking_label_includes_price_text(self):
        extra = ExtraService(name="Фотограф", price_text="11 500 ₽")
        self.assertEqual(build_extra_service_booking_label(extra), "Фотограф (11 500 ₽)")

    def test_named_lookup_works_with_label_map(self):
        labels = {"1": "Фотограф", "2": "Гримерка"}
        self.assertTrue(has_extra_named([1], labels, "фотограф"))
        self.assertTrue(has_extra_named(["2"], labels, "гример"))

    def test_missing_fields_for_extra_service(self):
        self.assertEqual(
            get_missing_extra_service_field_labels({"name": "Фотограф", "price_text": ""}),
            ["Цена / подпись"],
        )


if __name__ == "__main__":
    unittest.main()
