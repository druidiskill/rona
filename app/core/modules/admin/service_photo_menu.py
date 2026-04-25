from __future__ import annotations

from pathlib import Path


SERVICE_PHOTO_PAGE_SIZE = 6


def paginate_service_photo_paths(
    photo_paths: list[Path],
    page: int,
    *,
    page_size: int = SERVICE_PHOTO_PAGE_SIZE,
) -> tuple[list[tuple[int, Path]], int, int]:
    total_pages = max(1, (len(photo_paths) + page_size - 1) // page_size)
    page = max(0, min(page, total_pages - 1))
    start = page * page_size
    end = start + page_size
    items = list(enumerate(photo_paths[start:end], start=start))
    return items, page, total_pages

def build_service_photo_menu_text(
    photo_paths: list[Path],
    *,
    mode: str,
    page: int = 0,
    page_size: int = SERVICE_PHOTO_PAGE_SIZE,
) -> str:
    title = "Фотографии услуги" if mode == "add" else "Редактирование фотографий"
    lines = [
        f"📸 <b>{title}</b>",
        "",
        f"Всего фото: {len(photo_paths)}",
        "",
        "Выберите действие:",
    ]

    if not photo_paths:
        lines.append("Фотографии еще не загружены.")

    return "\n".join(lines)


def get_service_photo_preview(
    photo_paths: list[Path],
    index: int,
) -> tuple[Path | None, int, int]:
    total = len(photo_paths)
    if total == 0:
        return None, 0, 0
    index = max(0, min(index, total - 1))
    return photo_paths[index], index, total


def build_service_photo_delete_text(
    photo_paths: list[Path],
    index: int,
) -> str:
    _, index, total = get_service_photo_preview(photo_paths, index)
    if total == 0:
        return "📸 <b>Удаление фотографий</b>\n\nФотографий не осталось."
    return (
        "📸 <b>Удаление фотографий</b>\n\n"
        f"Фото {index + 1} из {total}"
    )
