"""Shared helpers for admin service photo flows."""

from __future__ import annotations

from pathlib import Path
from typing import Awaitable, Callable


async def save_service_photo(
    message,
    target_dir: str | Path,
    save_photo_func: Callable[[object, str | Path], Awaitable[object]],
    count_photos_func: Callable[[str | Path], int],
    clear_dir_func: Callable[[str | Path], None] | None = None,
    reset_before_save: bool = False,
) -> int:
    """Save one or many uploaded photos and return current count in target dir."""
    if reset_before_save and clear_dir_func is not None:
        clear_dir_func(target_dir)
    await save_photo_func(message, target_dir)
    return count_photos_func(target_dir)


def finalize_service_photo_dir(
    temp_dir: str | Path | None,
    service_dir: str | Path,
    move_dir_contents_func: Callable[[str | Path, str | Path], None],
) -> None:
    """Move temporary photos to final service directory if temp dir is set."""
    if temp_dir:
        move_dir_contents_func(temp_dir, service_dir)
