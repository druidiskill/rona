from __future__ import annotations

import logging
from pathlib import Path

from vkbottle import PhotoMessageUploader

from app.core.modules.services.photo_refs import (
    get_platform_photo_refs,
    update_platform_photo_refs,
)
from app.integrations.local.db import service_repo
from app.interfaces.messenger.tg.utils.photos import list_service_photos


logger = logging.getLogger(__name__)


def _chunk_paths(paths: list[Path], chunk_size: int = 10) -> list[list[Path]]:
    return [paths[index:index + chunk_size] for index in range(0, len(paths), chunk_size)]


async def _persist_db_photo_refs(service, all_photo_paths: list[Path], refs_by_name: dict[str, str]) -> None:
    if not getattr(service, "id", None) or not refs_by_name:
        return

    stored_photo_refs = update_platform_photo_refs(
        service.photo_ids,
        "vk",
        all_photo_paths,
        refs_by_name,
    )
    if stored_photo_refs == (service.photo_ids or ""):
        return

    await service_repo.update_photo_ids(int(service.id), stored_photo_refs)
    service.photo_ids = stored_photo_refs


async def _upload_local_attachments(message, service_id: int | None, photo_paths: list[Path]) -> tuple[list[str], dict[str, str]]:
    uploader = PhotoMessageUploader(message.ctx_api)
    attachments: list[str] = []
    refs_by_name: dict[str, str] = {}

    for photo_path in photo_paths:
        try:
            attachment = await uploader.upload(str(photo_path), peer_id=message.peer_id)
        except Exception:
            logger.warning(
                "Не удалось загрузить фото услуги %s в VK из локального файла %s",
                service_id,
                photo_path.name,
                exc_info=True,
            )
            continue
        attachments.append(attachment)
        refs_by_name[photo_path.name] = attachment

    return attachments, refs_by_name


async def send_service_details(message, service, *, text: str, keyboard: str) -> None:
    all_photo_paths = list_service_photos(service.id or 0)
    if not all_photo_paths:
        await message.answer(text, keyboard=keyboard)
        return

    _, cached_refs = get_platform_photo_refs(service.photo_ids, "vk", all_photo_paths)
    sent_any = False

    for chunk_index, chunk_paths in enumerate(_chunk_paths(all_photo_paths, chunk_size=10)):
        is_first_chunk = chunk_index == 0
        message_text = text if is_first_chunk else ""
        message_keyboard = keyboard if is_first_chunk else None
        can_use_cached = all(photo_path.name in cached_refs for photo_path in chunk_paths)

        if can_use_cached:
            try:
                kwargs = {
                    "peer_id": message.peer_id,
                    "random_id": 0,
                    "message": message_text,
                    "attachment": ",".join(cached_refs[path.name] for path in chunk_paths),
                }
                if message_keyboard is not None:
                    kwargs["keyboard"] = message_keyboard
                await message.ctx_api.messages.send(**kwargs)
                sent_any = True
                continue
            except Exception:
                logger.warning(
                    "Не удалось отправить фото услуги %s в VK по attachment id из БД, загружаю локальные файлы",
                    service.id,
                    exc_info=True,
                )

        attachments, refs_by_name = await _upload_local_attachments(message, service.id, chunk_paths)
        if not attachments:
            if is_first_chunk and not sent_any:
                await message.answer(text, keyboard=keyboard)
                return
            continue

        await _persist_db_photo_refs(service, all_photo_paths, refs_by_name)
        kwargs = {
            "peer_id": message.peer_id,
            "random_id": 0,
            "message": message_text,
            "attachment": ",".join(attachments),
        }
        if message_keyboard is not None:
            kwargs["keyboard"] = message_keyboard
        await message.ctx_api.messages.send(**kwargs)
        sent_any = True

    if not sent_any:
        await message.answer(text, keyboard=keyboard)
