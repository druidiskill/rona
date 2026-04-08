import json
import shutil
import unittest
from pathlib import Path
from uuid import uuid4

from app.core.modules.services.photo_refs import (
    get_platform_photo_refs,
    parse_service_photo_refs,
    update_platform_photo_refs,
)


TEST_TMP_ROOT = Path(__file__).resolve().parent / "_tmp"
TEST_TMP_ROOT.mkdir(exist_ok=True)


def _make_temp_dir() -> Path:
    temp_dir = TEST_TMP_ROOT / uuid4().hex
    temp_dir.mkdir(parents=True, exist_ok=True)
    return temp_dir


class TestServicePhotoCache(unittest.TestCase):
    def test_updates_and_reads_platform_refs(self):
        root = _make_temp_dir()
        try:
            photo_a = root / "a.jpg"
            photo_b = root / "b.jpg"
            photo_a.write_bytes(b"a")
            photo_b.write_bytes(b"bb")
            photo_paths = [photo_a, photo_b]

            raw_cache = update_platform_photo_refs(
                None,
                "tg",
                photo_paths,
                {"a.jpg": "file-id-a"},
            )

            payload = parse_service_photo_refs(raw_cache)
            self.assertEqual("file-id-a", payload["tg"]["a.jpg"])

            _, refs = get_platform_photo_refs(raw_cache, "tg", photo_paths)
            self.assertEqual({"a.jpg": "file-id-a"}, refs)
        finally:
            shutil.rmtree(root, ignore_errors=True)

    def test_signature_change_invalidates_cached_refs(self):
        root = _make_temp_dir()
        try:
            photo = root / "a.jpg"
            photo.write_bytes(b"first")
            photo_paths = [photo]

            raw_cache = update_platform_photo_refs(
                None,
                "vk",
                photo_paths,
                {"a.jpg": "photo-1_1"},
            )
            photo.write_bytes(b"second")

            _, refs = get_platform_photo_refs(raw_cache, "vk", photo_paths)
            self.assertEqual({}, refs)
        finally:
            shutil.rmtree(root, ignore_errors=True)

    def test_keeps_other_platform_cache_when_same_signature(self):
        root = _make_temp_dir()
        try:
            photo = root / "a.jpg"
            photo.write_bytes(b"photo")
            photo_paths = [photo]

            raw_cache = update_platform_photo_refs(
                None,
                "tg",
                photo_paths,
                {"a.jpg": "tg-file"},
            )
            raw_cache = update_platform_photo_refs(
                raw_cache,
                "vk",
                photo_paths,
                {"a.jpg": "vk-photo"},
            )

            payload = json.loads(raw_cache)
            self.assertEqual("tg-file", payload["tg"]["a.jpg"])
            self.assertEqual("vk-photo", payload["vk"]["a.jpg"])
        finally:
            shutil.rmtree(root, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
