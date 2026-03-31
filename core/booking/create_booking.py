from __future__ import annotations

from db.models import Client

from core.booking.common import normalize_phone10


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
    client = await client_repo.get_by_telegram_id(telegram_id)
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
    client = await get_or_create_vk_client(
        client_repo=client_repo,
        vk_id=vk_id,
        fallback_name=fallback_name,
    )
    client.name = booking_data["name"]
    client.last_name = booking_data.get("last_name") or ""
    client.email = booking_data.get("email")
    client.discount_code = booking_data.get("discount_code")
    phone10 = normalize_phone10(booking_data.get("phone"))
    if phone10:
        client.phone = phone10
    await client_repo.update(client)
    return client
