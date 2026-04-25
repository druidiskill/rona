from __future__ import annotations

import logging
from pathlib import Path

from aiogram.types import FSInputFile, InputMediaPhoto, Message

from app.core.modules.services.photo_refs import (
    get_platform_photo_refs,
    update_platform_photo_refs,
)
from app.integrations.local.db import service_repo
from app.interfaces.messenger.tg.utils.photos import list_service_photos


logger = logging.getLogger(__name__)


def _chunk_paths(paths: list[Path], chunk_size: int = 10) -> list[list[Path]]:
    return [paths[index:index + chunk_size] for index in range(0, len(paths), chunk_size)]


def _extract_file_id(message: Message) -> str | None:
    photos = getattr(message, "photo", None) or []
    if not photos:
        return None
    return photos[-1].file_id


async def _persist_db_photo_refs(service, all_photo_paths: list[Path], refs_by_name: dict[str, str]) -> None:
    if not getattr(service, "id", None) or not refs_by_name:
        return

    stored_photo_refs = update_platform_photo_refs(
        service.photo_ids,
        "tg",
        all_photo_paths,
        refs_by_name,
    )
    if stored_photo_refs == (service.photo_ids or ""):
        return

    await service_repo.update_photo_ids(int(service.id), stored_photo_refs)
    service.photo_ids = stored_photo_refs


async def send_service_cover(message, service, *, caption: str, reply_markup, parse_mode: str = "HTML") -> Message | None:
    all_photo_paths = list_service_photos(service.id or 0)
    if not all_photo_paths:
        return None

    cover_path = all_photo_paths[0]
    _, cached_refs = get_platform_photo_refs(service.photo_ids, "tg", all_photo_paths)
    cached_file_id = cached_refs.get(cover_path.name)
    photo = cached_file_id or FSInputFile(cover_path)

    try:
        sent_message = await message.answer_photo(
            photo=photo,
            caption=caption,
            parse_mode=parse_mode,
            reply_markup=reply_markup,
        )
    except Exception:
        if not cached_file_id:
            raise
        logger.warning(
            "Не удалось отправить фото услуги %s по TG file_id из БД, загружаю локальный файл",
            service.id,
            exc_info=True,
        )
        sent_message = await message.answer_photo(
            photo=FSInputFile(cover_path),
            caption=caption,
            parse_mode=parse_mode,
            reply_markup=reply_markup,
        )

    file_id = _extract_file_id(sent_message)
    if file_id:
        await _persist_db_photo_refs(service, all_photo_paths, {cover_path.name: file_id})

    return sent_message


async def send_service_gallery(message, service, *, caption: str, parse_mode: str = "HTML") -> list[Message]:
    all_photo_paths = list_service_photos(service.id or 0)
    gallery_paths = all_photo_paths[1:]
    if not gallery_paths:
        return []

    _, cached_refs = get_platform_photo_refs(service.photo_ids, "tg", all_photo_paths)
    if len(gallery_paths) == 1:
        gallery_path = gallery_paths[0]
        cached_file_id = cached_refs.get(gallery_path.name)
        photo = cached_file_id or FSInputFile(gallery_path)
        try:
            sent_message = await message.answer_photo(
                photo=photo,
                caption=caption,
                parse_mode=parse_mode,
            )
        except Exception:
            if not cached_file_id:
                raise
            logger.warning(
                "Не удалось отправить галерею услуги %s по TG file_id из БД, загружаю локальный файл",
                service.id,
                exc_info=True,
            )
            sent_message = await message.answer_photo(
                photo=FSInputFile(gallery_path),
                caption=caption,
                parse_mode=parse_mode,
            )

        file_id = _extract_file_id(sent_message)
        if file_id:
            await _persist_db_photo_refs(service, all_photo_paths, {gallery_path.name: file_id})
        return [sent_message]

    def _build_media_group(chunk_paths: list[Path], *, use_cached_refs: bool, chunk_caption: str | None) -> list[InputMediaPhoto]:
        media_group: list[InputMediaPhoto] = []
        for index, photo_path in enumerate(chunk_paths):
            media = cached_refs.get(photo_path.name) if use_cached_refs else None
            media = media or FSInputFile(photo_path)
            if index == 0 and chunk_caption:
                media_group.append(
                    InputMediaPhoto(
                        media=media,
                        caption=chunk_caption,
                        parse_mode=parse_mode,
                    )
                )
            else:
                media_group.append(InputMediaPhoto(media=media))
        return media_group

    sent_messages: list[Message] = []
    refs_by_name: dict[str, str] = {}
    for chunk_index, chunk_paths in enumerate(_chunk_paths(gallery_paths, chunk_size=10)):
        chunk_caption = caption if chunk_index == 0 else None
        chunk_used_cached_refs = any(path.name in cached_refs for path in chunk_paths)
        try:
            chunk_sent_messages = await message.answer_media_group(
                media=_build_media_group(chunk_paths, use_cached_refs=True, chunk_caption=chunk_caption)
            )
        except Exception:
            if not chunk_used_cached_refs:
                raise
            logger.warning(
                "Не удалось отправить галерею услуги %s по TG file_id из БД, загружаю локальные файлы",
                service.id,
                exc_info=True,
            )
            chunk_sent_messages = await message.answer_media_group(
                media=_build_media_group(chunk_paths, use_cached_refs=False, chunk_caption=chunk_caption)
            )

        sent_messages.extend(chunk_sent_messages)
        for photo_path, sent_message in zip(chunk_paths, chunk_sent_messages):
            file_id = _extract_file_id(sent_message)
            if file_id:
                refs_by_name[photo_path.name] = file_id

    await _persist_db_photo_refs(service, all_photo_paths, refs_by_name)

    return sent_messages
