from __future__ import annotations

import os
import shutil
import unittest
from pathlib import Path
from uuid import uuid4

from app.core.modules.admin.service_photo_menu import (
    build_service_photo_delete_text,
    build_service_photo_menu_text,
    get_service_photo_preview,
)
from app.interfaces.messenger.tg.utils.photos import delete_photo_by_index, list_photo_files


TEST_TMP_ROOT = Path(__file__).resolve().parent / "_tmp"
TEST_TMP_ROOT.mkdir(exist_ok=True)


class ServicePhotoManagementTests(unittest.TestCase):
    def _make_case_dir(self) -> Path:
        root = TEST_TMP_ROOT / uuid4().hex
        root.mkdir(parents=True, exist_ok=True)
        return root

    def _create_photo(self, root: Path, name: str, timestamp: int) -> Path:
        path = root / name
        path.write_bytes(b"photo")
        os.utime(path, (timestamp, timestamp))
        return path

    def test_delete_photo_by_index_uses_upload_order(self):
        root = self._make_case_dir()
        try:
            self._create_photo(root, "first.jpg", 100)
            self._create_photo(root, "second.jpg", 200)
            self._create_photo(root, "third.jpg", 300)

            deleted = delete_photo_by_index(root, 1)

            self.assertIsNotNone(deleted)
            self.assertEqual(deleted.name, "second.jpg")
            self.assertEqual([path.name for path in list_photo_files(root)], ["first.jpg", "third.jpg"])
        finally:
            shutil.rmtree(root, ignore_errors=True)

    def test_photo_menu_text_shows_count_without_listing(self):
        root = self._make_case_dir()
        try:
            for index in range(7):
                self._create_photo(root, f"photo_{index}.jpg", 100 + index)

            photo_paths = list_photo_files(root)
            text = build_service_photo_menu_text(photo_paths, mode="edit")

            self.assertIn("Всего фото: 7", text)
            self.assertIn("Выберите действие", text)
            self.assertNotIn("Страница:", text)
        finally:
            shutil.rmtree(root, ignore_errors=True)

    def test_photo_delete_preview_clamps_index_and_shows_position(self):
        root = self._make_case_dir()
        try:
            self._create_photo(root, "first.jpg", 100)
            self._create_photo(root, "second.jpg", 200)

            photo_paths = list_photo_files(root)
            photo_path, index, total = get_service_photo_preview(photo_paths, 10)
            text = build_service_photo_delete_text(photo_paths, 10)

            self.assertIsNotNone(photo_path)
            self.assertEqual(photo_path.name, "second.jpg")
            self.assertEqual(index, 1)
            self.assertEqual(total, 2)
            self.assertIn("Фото 2 из 2", text)
        finally:
            shutil.rmtree(root, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
