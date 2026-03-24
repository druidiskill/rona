from vkbottle import Keyboard, KeyboardButtonColor, Text


def get_main_menu_keyboard(is_admin: bool = False) -> str:
    keyboard = Keyboard(one_time=False, inline=False)
    keyboard.add(Text("📸 Услуги"), color=KeyboardButtonColor.PRIMARY).row()
    keyboard.add(Text("📅 Мои бронирования"), color=KeyboardButtonColor.PRIMARY).row()
    keyboard.add(Text("📞 Контакты"), color=KeyboardButtonColor.SECONDARY).row()
    keyboard.add(Text("ℹ️ Помощь"), color=KeyboardButtonColor.SECONDARY)
    if is_admin:
        keyboard.row().add(Text("🔧 Админ-панель"), color=KeyboardButtonColor.NEGATIVE)
    return keyboard.get_json()


def get_back_to_main_keyboard() -> str:
    return get_main_menu_keyboard()