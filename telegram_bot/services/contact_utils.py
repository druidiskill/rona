import re


def extract_booking_contact_details(description: str) -> dict:
    text = re.sub(r"<[^>]+>", "", description or "")
    lines = [line.strip() for line in text.splitlines() if line.strip()]

    name = None
    for i, line in enumerate(lines):
        if line.lower() == "кто забронировал" and i + 1 < len(lines):
            name = lines[i + 1]
            break

    email_match = re.search(r"[\w.\-+%]+@[\w.\-]+\.\w+", text)
    phone_match = re.search(r"(\+?\d[\d\-\s\(\)]{8,}\d)", text)
    tg_id_match = re.search(r"Telegram ID:\s*(\d+)", text, flags=re.IGNORECASE)
    tg_link_match = re.search(r"https?://t\.me/([A-Za-z0-9_]{5,32})", text, flags=re.IGNORECASE)
    tg_username_match = re.search(r"(?:^|\s)@([A-Za-z0-9_]{5,32})(?:\s|$)", text)

    return {
        "name": name,
        "email": email_match.group(0) if email_match else None,
        "phone": phone_match.group(1) if phone_match else None,
        "telegram_id": tg_id_match.group(1) if tg_id_match else None,
        "telegram_username": (
            tg_link_match.group(1)
            if tg_link_match
            else (tg_username_match.group(1) if tg_username_match else None)
        ),
    }


def normalize_phone(phone: str | None) -> str | None:
    if not phone:
        return None
    digits = "".join(ch for ch in str(phone) if ch.isdigit())
    if len(digits) == 11 and digits.startswith(("7", "8")):
        digits = digits[1:]
    if len(digits) == 10:
        return digits
    return None


def format_phone_plus7(phone: str | None) -> str | None:
    if not phone:
        return None
    digits = "".join(ch for ch in str(phone) if ch.isdigit())
    if len(digits) == 11 and digits.startswith(("7", "8")):
        digits = digits[1:]
    if len(digits) != 10:
        return str(phone)
    return f"+7 {digits[:3]} {digits[3:6]} {digits[6:8]} {digits[8:10]}"


def format_phone_for_search(phone: str | None) -> str | None:
    if not phone:
        return None
    phone = str(phone).strip()
    if len(phone) == 10 and phone.isdigit():
        return f"+7 {phone[:3]} {phone[3:6]} {phone[6:8]} {phone[8:10]}"
    return phone

