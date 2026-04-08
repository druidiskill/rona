from __future__ import annotations

from app.integrations.local.db.models import Client

from app.core.modules.booking.common import normalize_phone10


async def _get_client_by_channel_or_phone(
    *,
    client_repo,
    channel: str,
    channel_id: int,
    phone10: str | None,
) -> Client | None:
    if channel == "telegram":
        client = await client_repo.get_by_telegram_id(channel_id)
        channel_attr = "telegram_id"
    else:
        client = await client_repo.get_by_vk_id(channel_id)
        channel_attr = "vk_id"

    if client:
        return client

    if not phone10:
        return None

    candidates = await client_repo.get_all_by_phone(phone10)
    for candidate in candidates:
        if getattr(candidate, channel_attr, None) == channel_id:
            return candidate
    for candidate in candidates:
        if getattr(candidate, channel_attr, None) is None:
            return candidate
    return None


async def get_or_create_vk_client(*, client_repo, vk_id: int, fallback_name: str | None = None) -> Client:
    client = await client_repo.get_by_vk_id(vk_id)
    if client:
        return client
    client_id = await client_repo.create(
        Client(
            vk_id=vk_id,
            name=(fallback_name or "Пользователь").strip() or "Пользователь",
            last_name="",
        )
    )
    return await client_repo.get_by_id(client_id)


async def sync_telegram_booking_client(*, client_repo, telegram_id: int, booking_data: dict) -> Client:
    phone10 = normalize_phone10(booking_data.get("phone"))
    client = await _get_client_by_channel_or_phone(
        client_repo=client_repo,
        channel="telegram",
        channel_id=telegram_id,
        phone10=phone10,
    )
    if not client:
        client_id = await client_repo.create(
            Client(
                telegram_id=telegram_id,
                name=booking_data["name"],
                last_name=booking_data.get("last_name") or "",
                phone=phone10,
                email=booking_data.get("email"),
                discount_code=booking_data.get("discount_code"),
            )
        )
        return await client_repo.get_by_id(client_id)

    client.telegram_id = telegram_id
    client.name = booking_data["name"]
    client.last_name = booking_data.get("last_name") or ""
    if phone10:
        client.phone = phone10
    client.discount_code = booking_data.get("discount_code")
    if booking_data.get("email"):
        client.email = booking_data.get("email")
    await client_repo.update(client)
    return client


async def sync_vk_booking_client(
    *,
    client_repo,
    vk_id: int,
    booking_data: dict,
    fallback_name: str | None = None,
) -> Client:
    phone10 = normalize_phone10(booking_data.get("phone"))
    client = await _get_client_by_channel_or_phone(
        client_repo=client_repo,
        channel="vk",
        channel_id=vk_id,
        phone10=phone10,
    )
    if not client:
        client = await get_or_create_vk_client(
            client_repo=client_repo,
            vk_id=vk_id,
            fallback_name=fallback_name,
        )

    client.vk_id = vk_id
    client.name = booking_data["name"]
    client.last_name = booking_data.get("last_name") or ""
    client.email = booking_data.get("email")
    client.discount_code = booking_data.get("discount_code")
    if phone10:
        client.phone = phone10
    await client_repo.update(client)
    return client
