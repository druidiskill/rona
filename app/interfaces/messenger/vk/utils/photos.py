from __future__ import annotations

from pathlib import Path
from urllib.parse import urlparse
from uuid import uuid4

import aiohttp


def _pick_photo_urls(message) -> list[str]:
    attachments = message.get_photo_attachments() or []
    if not attachments:
        return []

    urls: list[str] = []
    for attachment in attachments:
        candidates: list[tuple[int, str]] = []

        for size in getattr(attachment, "sizes", []) or []:
            url = getattr(size, "url", None) or getattr(size, "src", None)
            width = int(getattr(size, "width", 0) or 0)
            height = int(getattr(size, "height", 0) or 0)
            if url:
                candidates.append((width * height, url))

        for image in getattr(attachment, "images", []) or []:
            url = getattr(image, "url", None)
            width = int(getattr(image, "width", 0) or 0)
            height = int(getattr(image, "height", 0) or 0)
            if url:
                candidates.append((width * height, url))

        fallback_url = getattr(attachment, "photo_256", None)
        if fallback_url:
            candidates.append((256 * 256, fallback_url))

        if candidates:
            urls.append(max(candidates, key=lambda item: item[0])[1])

    return urls


async def save_message_photos(message, dest_dir: Path) -> list[Path]:
    photo_urls = _pick_photo_urls(message)
    if not photo_urls:
        raise ValueError("message has no photo attachments")

    dest_dir.mkdir(parents=True, exist_ok=True)
    saved_paths: list[Path] = []

    timeout = aiohttp.ClientTimeout(total=30)
    async with aiohttp.ClientSession(timeout=timeout) as session:
        for photo_url in photo_urls:
            suffix = Path(urlparse(photo_url).path).suffix or ".jpg"
            dest_path = dest_dir / f"{uuid4().hex}{suffix}"
            async with session.get(photo_url) as response:
                response.raise_for_status()
                dest_path.write_bytes(await response.read())
            saved_paths.append(dest_path)

    return saved_paths


async def save_message_photo(message, dest_dir: Path) -> Path:
    return (await save_message_photos(message, dest_dir))[-1]
