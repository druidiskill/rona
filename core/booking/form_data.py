from core.booking.common import normalize_max_guests, normalize_min_duration_minutes


def build_initial_booking_data(
    *,
    service_id: int,
    service_name: str,
    max_num_clients: int | None,
    min_duration_minutes: int | None,
    name: str | None = None,
    last_name: str | None = None,
    phone: str | None = None,
    email: str | None = None,
    discount_code: str | None = None,
) -> dict:
    return {
        "service_id": service_id,
        "service_name": service_name,
        "max_num_clients": normalize_max_guests(max_num_clients),
        "date": None,
        "time": None,
        "name": name,
        "last_name": last_name,
        "phone": phone,
        "discount_code": discount_code,
        "comment": None,
        "guests_count": None,
        "duration": normalize_min_duration_minutes(min_duration_minutes),
        "is_all_day": False,
        "extras": [],
        "email": email,
    }


def merge_booking_data(
    current_booking_data: dict | None,
    *,
    state_service_name: str | None = None,
    updates: dict | None = None,
) -> dict:
    booking_data = dict(current_booking_data or {})
    if updates:
        booking_data.update(updates)
    if not booking_data.get("service_name"):
        booking_data["service_name"] = state_service_name or ""
    return booking_data


def resolve_booking_service_name(state_data: dict, booking_data: dict | None = None) -> str:
    data = booking_data or state_data.get("booking_data", {})
    return data.get("service_name") or state_data.get("service_name", "")
