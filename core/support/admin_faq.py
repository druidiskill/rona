from __future__ import annotations

from dataclasses import dataclass
import html


MAX_ADMIN_FAQ_QUESTION_LENGTH = 40


@dataclass(slots=True)
class AdminFaqViewItem:
    faq_id: int
    question: str
    is_active: bool


def build_admin_faq_overview_text(faqs: list) -> str:
    text = "❓ <b>Помощь (FAQ)</b>\n\n"
    if not faqs:
        return text + "Список вопросов пуст."

    for idx, entry in enumerate(faqs, start=1):
        status = "✅" if entry.is_active else "❌"
        text += f"{status} {idx}. {html.escape(entry.question or '')}\n"
    return text


def build_admin_faq_keyboard_items(faqs: list) -> list[tuple[int, str, bool]]:
    return [
        (int(entry.id or 0), entry.question or "", bool(entry.is_active))
        for entry in faqs
    ]


def build_admin_faq_detail_text(entry) -> str:
    return (
        "❓ <b>Вопрос</b>\n"
        f"{html.escape(entry.question or '')}\n\n"
        "💡 <b>Ответ</b>\n"
        f"{html.escape(entry.answer or '')}"
    )


def validate_admin_faq_question(question: str) -> str | None:
    if not question:
        return "❌ Вопрос не может быть пустым. Введите вопрос:"
    if len(question) > MAX_ADMIN_FAQ_QUESTION_LENGTH:
        return (
            f"❌ Вопрос не должен быть длиннее {MAX_ADMIN_FAQ_QUESTION_LENGTH} символов. "
            "Введите короче:"
        )
    return None


def validate_admin_faq_answer(answer: str) -> str | None:
    if not answer:
        return "❌ Ответ не может быть пустым. Введите ответ:"
    return None
