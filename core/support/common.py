from __future__ import annotations

import html


FAQ_PAGE_SIZE = 6


def truncate_question(question: str, *, max_length: int) -> str:
    question = str(question or "").strip()
    if len(question) <= max_length:
        return question
    return f"{question[: max_length - 3]}..."


def build_faq_list_text(*, has_items: bool, html_mode: bool = False) -> str:
    if html_mode:
        title = "ℹ️ <b>Часто задаваемые вопросы</b>\n\n"
    else:
        title = "ℹ️ Часто задаваемые вопросы\n\n"

    if not has_items:
        return title + "Список FAQ пока пуст.\n\nВы можете связаться с администратором."

    suffix = "Выберите вопрос кнопкой ниже:" if html_mode else "Выберите вопрос кнопкой ниже или напишите администратору."
    return title + suffix


async def get_faq_page_data(*, faq_repo, page: int, page_size: int = FAQ_PAGE_SIZE) -> tuple[list[tuple[int, str]], int, int]:
    faqs = await faq_repo.get_all_active()
    total = len(faqs)
    total_pages = max(1, (total + page_size - 1) // page_size)
    page = max(0, min(page, total_pages - 1))
    start = page * page_size
    end = min(start + page_size, total)
    items = [(entry.id, entry.question) for entry in faqs[start:end] if entry.id is not None]
    return items, total_pages, page


def get_active_admin_targets(admins: list, *, channel: str) -> list[int]:
    field_name = {"telegram": "telegram_id", "vk": "vk_id"}[channel]
    return [
        int(getattr(admin, field_name))
        for admin in admins
        if getattr(admin, "is_active", False) and getattr(admin, field_name, None)
    ]


def build_vk_support_alert_text(*, question: str, dialog_link: str) -> str:
    return f"{question}\n{dialog_link}"


def build_telegram_support_alert_text(
    *,
    user_full_name: str,
    user_id: int,
    username: str | None,
    history_rows: list[tuple[str, str | None]],
) -> str:
    history_text = ""
    if history_rows:
        lines = []
        for role, text in history_rows:
            label = "Пользователь" if role == "user" else "Админ"
            lines.append(f"• {label}: {html.escape(text or '')}")
        history_text = "\n\n<b>История (последние 6 сообщений):</b>\n" + "\n".join(lines)

    header = (
        "🆘 <b>Новый запрос поддержки</b>\n\n"
        f"👤 Пользователь: {html.escape(user_full_name)}\n"
        f"🆔 ID: {user_id}\n"
    )
    if username:
        header += f"🔗 https://t.me/{username}\n"
    header += history_text
    return header
