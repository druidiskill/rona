import unittest
from datetime import datetime, timedelta

from app.interfaces.messenger.tg.keyboards import (
    TIME_SELECTION_PAGE_SIZE,
    get_time_selection_keyboard,
    get_time_selection_total_pages,
)


def _build_slots(count: int) -> list[dict]:
    start = datetime.strptime("09:00", "%H:%M")
    slots = []
    for index in range(count):
        slot_start = start + timedelta(hours=index)
        slots.append(
            {
                "start_time": slot_start.time(),
                "end_time": (slot_start + timedelta(hours=1)).time(),
                "is_available": True,
            }
        )
    return slots


class TestTimeSelectionPagination(unittest.TestCase):
    def test_total_pages_uses_page_size(self):
        slots = _build_slots(TIME_SELECTION_PAGE_SIZE + 3)
        self.assertEqual(get_time_selection_total_pages(slots), 2)

    def test_first_page_keeps_global_slot_indexes_and_next_button(self):
        slots = _build_slots(TIME_SELECTION_PAGE_SIZE + 3)
        markup = get_time_selection_keyboard(7, slots, "2026-04-14", page=0)

        buttons = [button for row in markup.inline_keyboard for button in row]
        callback_data = [button.callback_data for button in buttons]

        self.assertIn("select_time_7_0", callback_data)
        self.assertIn(f"select_time_7_{TIME_SELECTION_PAGE_SIZE - 1}", callback_data)
        self.assertIn("time_page_7_2026-04-14_1", callback_data)

    def test_second_page_shows_remaining_slots_and_previous_button(self):
        slots = _build_slots(TIME_SELECTION_PAGE_SIZE + 3)
        markup = get_time_selection_keyboard(7, slots, "2026-04-14", page=1)

        buttons = [button for row in markup.inline_keyboard for button in row]
        callback_data = [button.callback_data for button in buttons]

        self.assertIn(f"select_time_7_{TIME_SELECTION_PAGE_SIZE}", callback_data)
        self.assertIn(f"select_time_7_{TIME_SELECTION_PAGE_SIZE + 2}", callback_data)
        self.assertIn("time_page_7_2026-04-14_0", callback_data)


if __name__ == "__main__":
    unittest.main()
