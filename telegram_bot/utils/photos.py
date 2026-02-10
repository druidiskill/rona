from pathlib import Path
from uuid import uuid4
import shutil

MEDIA_ROOT = Path("media") / "services"


def _ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def get_service_dir(service_id: int) -> Path:
    return MEDIA_ROOT / str(service_id)


def get_temp_dir(user_id: int) -> Path:
    return MEDIA_ROOT / "_tmp" / str(user_id)


def count_photos_in_dir(path: Path) -> int:
    if not path.exists():
        return 0
    return sum(1 for p in path.iterdir() if p.is_file())


def list_service_photos(service_id: int) -> list[Path]:
    path = get_service_dir(service_id)
    if not path.exists():
        return []
    return sorted([p for p in path.iterdir() if p.is_file()])


def clear_dir(path: Path) -> None:
    if not path.exists():
        return
    for item in path.iterdir():
        if item.is_file():
            item.unlink(missing_ok=True)
        else:
            shutil.rmtree(item, ignore_errors=True)


def move_dir_contents(src: Path, dest: Path) -> None:
    if not src.exists():
        return
    _ensure_dir(dest)
    for item in src.iterdir():
        shutil.move(str(item), dest / item.name)
    try:
        src.rmdir()
    except OSError:
        pass


async def save_message_photo(message, dest_dir: Path) -> Path:
    _ensure_dir(dest_dir)

    if not message.photo:
        raise ValueError("message has no photo")

    photo = message.photo[-1]
    file = await message.bot.get_file(photo.file_id)
    suffix = Path(file.file_path).suffix or ".jpg"
    filename = f"{uuid4().hex}{suffix}"
    dest_path = dest_dir / filename

    await message.bot.download_file(file.file_path, destination=dest_path)
    return dest_path
