from __future__ import annotations


def build_name_validation_error(*, field_label: str, html: bool) -> str:
    if html:
        return (
            f"⚠️ <b>{field_label} указано некорректно</b>\n\n"
            f"Пожалуйста, введите {field_label.lower()} длиннее 1 символа."
        )
    return f"{field_label} должно содержать только буквы и быть длиннее 1 символа."


def build_phone_validation_error(*, html: bool) -> str:
    if html:
        return (
            "⚠️ <b>Неверный формат номера телефона</b>\n\n"
            "Пожалуйста, введите номер в одном из форматов:\n"
            "• +7 900 123 45 67\n"
            "• 8 900 123 45 67\n"
            "• 7 900 123 45 67\n"
            "• 900 123 45 67"
        )
    return "Некорректный формат телефона. Введите 10 цифр номера."


def build_discount_code_validation_error(*, max_length: int, html: bool) -> str:
    if html:
        return (
            "⚠️ <b>Код слишком длинный</b>\n\n"
            f"Максимальная длина скидочного кода: {max_length} символов."
        )
    return f"Код для скидки не должен превышать {max_length} символов."


def build_comment_validation_error(*, max_length: int, html: bool) -> str:
    if html:
        return (
            "⚠️ <b>Комментарий слишком длинный</b>\n\n"
            f"Максимальная длина комментария: {max_length} символов."
        )
    return f"Комментарий не должен превышать {max_length} символов."


def build_email_validation_error(*, html: bool, skip_label: str) -> str:
    if html:
        return (
            "⚠️ <b>Некорректный e-mail</b>\n\n"
            "Пожалуйста, введите корректный адрес электронной почты.\n"
            "Пример: example@mail.ru\n\n"
            f"Чтобы пропустить шаг, отправьте {skip_label}."
        )
    return f"Некорректный e-mail. Введите корректный адрес или '{skip_label}' для пропуска."


def build_guests_validation_error(*, max_guests: int, html: bool) -> str:
    if html:
        return (
            "⚠️ <b>Слишком много гостей</b>\n\n"
            f"Максимальная вместимость этой услуги: {max_guests} чел."
        )
    return f"Максимальная вместимость этой услуги: {max_guests} чел."


def build_duration_too_small_error(*, min_duration: int, html: bool) -> str:
    if html:
        return (
            f"⚠️ <b>Минимальная продолжительность: {min_duration} мин.</b>\n\n"
            f"Пожалуйста, выберите длительность не меньше {min_duration} минут."
        )
    return f"Минимальная продолжительность: {min_duration} мин."


def build_duration_too_large_error(*, html: bool) -> str:
    if html:
        return (
            "⚠️ <b>Слишком большая длительность</b>\n\n"
            "Максимальная продолжительность: 720 минут (весь день).\n"
            "Если нужен особый формат, согласуйте его отдельно."
        )
    return "Максимальная продолжительность: 720 минут."


def build_duration_invalid_step_error(*, html: bool) -> str:
    if html:
        return (
            "⚠️ <b>Длительность должна быть кратна 60 минутам</b>\n\n"
            "Допустимые значения: 60, 120, 180, 240..."
        )
    return "Длительность должна быть кратна 60 минутам."
