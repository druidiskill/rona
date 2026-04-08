from __future__ import annotations


def build_name_prompt(*, html: bool) -> str:
    if html:
        return (
            "👤 <b>Введите ваше имя:</b>\n\n"
            "Имя должно содержать только буквы и быть длиннее 1 символа.\n"
            "Пример: Анна, Иван, Мария"
        )
    return "👤 Введите имя:"


def build_last_name_prompt(*, html: bool) -> str:
    if html:
        return (
            "🧾 <b>Введите вашу фамилию:</b>\n\n"
            "Фамилия должна содержать только буквы и быть длиннее 1 символа.\n"
            "Пример: Иванова, Петров, Соколова"
        )
    return "🧾 Введите фамилию:"


def build_phone_prompt(*, html: bool) -> str:
    if html:
        return (
            "📱 <b>Введите номер телефона:</b>\n\n"
            "Номер можно указать в формате +7, 8 или просто 10 цифр.\n"
            "Пример: +7 900 123 45 67 или 8 900 123 45 67"
        )
    return "📱 Введите телефон (например +7 911 123 45 67):"


def build_discount_code_prompt(*, html: bool, back_label: str) -> str:
    if html:
        return (
            "🏷️ <b>Введите код для скидки:</b>\n\n"
            f"Поле необязательное. Если код не нужен, нажмите кнопку «{back_label}»."
        )
    return (
        "🏷️ Введите код для скидки.\n\n"
        f"Поле необязательное. Если код не нужен, нажмите «{back_label}»."
    )


def build_comment_prompt(*, html: bool, back_label: str) -> str:
    if html:
        return (
            "💬 <b>Введите комментарий к бронированию:</b>\n\n"
            f"Поле необязательное. Если комментарий не нужен, нажмите кнопку «{back_label}»."
        )
    return (
        "💬 Введите комментарий к бронированию.\n\n"
        f"Поле необязательное. Если комментарий не нужен, нажмите «{back_label}»."
    )


def build_guests_count_prompt(*, max_guests: int, html: bool) -> str:
    if html:
        return (
            "👥 <b>Введите количество гостей:</b>\n\n"
            "Укажите количество человек, которые будут присутствовать на съемке.\n"
            f"Максимум для этой услуги: {max_guests}.\n"
            "Пример: 2, 4, 6"
        )
    return f"👥 Введите количество гостей. Максимум: {max_guests}."


def build_duration_prompt(*, min_duration: int, html: bool, detailed: bool) -> str:
    if detailed:
        if html:
            return (
                f"⏰ <b>Выберите продолжительность бронирования:</b>\n\n"
                f"Выберите подходящий вариант.\n\n"
                f"ℹ️ <b>Важно:</b>\n"
                f"• Минимальная продолжительность: {min_duration} мин.\n"
                "• Бронирование доступно шагом в 60 минут."
            )
        return (
            "⏰ Выберите продолжительность:\n\n"
            f"Минимальная продолжительность: {min_duration} мин.\n"
            "Шаг бронирования: 60 минут."
        )

    if html:
        return "⏰ <b>Выберите продолжительность:</b>"
    return "⏰ Выберите продолжительность:"


def build_email_prompt(*, html: bool, skip_label: str) -> str:
    if html:
        return (
            "📧 <b>Введите ваш e-mail (необязательно):</b>\n\n"
            "E-mail нужен для отправки подтверждения бронирования.\n"
            "Пример: example@mail.ru\n\n"
            f"Чтобы пропустить шаг, отправьте {skip_label}."
        )
    return f"📧 Введите e-mail (или '{skip_label}' чтобы пропустить):"
