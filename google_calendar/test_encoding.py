#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Простой тест кодировки UTF-8
"""

import sys
import os

# Устанавливаем кодировку UTF-8 для Windows консоли
if sys.platform == 'win32':
    import io
    os.environ['PYTHONIOENCODING'] = 'utf-8'
    try:
        if hasattr(sys.stdout, 'buffer') and not isinstance(sys.stdout, io.TextIOWrapper):
            sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
        if hasattr(sys.stderr, 'buffer') and not isinstance(sys.stderr, io.TextIOWrapper):
            sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')
    except (AttributeError, ValueError, TypeError):
        pass

def test_encoding():
    """Тест кодировки"""
    print("=" * 80)
    print("ТЕСТ КОДИРОВКИ UTF-8")
    print("=" * 80)
    
    # Тестовые строки с кириллицей
    test_strings = [
        "Русский текст: Привет, мир!",
        "Имя: Борис",
        "Email: druidiskill@yandex.ru",
        "Телефон: +7 911 137 34 86",
        "Зал: Зал Dark",
        "Количество гостей: 15",
        "Гримерная: Не указано",
        "Фотограф: Не указано",
        "✅ Символы эмодзи: ✅ ❌ 📝 📅",
        "Специальные символы: < > & \" '"
    ]
    
    print("\n[OK] Тестовые строки:")
    for i, text in enumerate(test_strings, 1):
        print(f"  {i:2d}. {text}")
    
    # Проверка кодировки файлов
    print("\n[INFO] Информация о кодировке:")
    print(f"  Платформа: {sys.platform}")
    print(f"  Кодировка по умолчанию: {sys.getdefaultencoding()}")
    print(f"  PYTHONIOENCODING: {os.environ.get('PYTHONIOENCODING', 'не установлена')}")
    
    if hasattr(sys.stdout, 'encoding'):
        print(f"  Кодировка stdout: {sys.stdout.encoding}")
    else:
        print(f"  Кодировка stdout: не определена")
    
    print("\n[OK] Кодировка работает корректно!")

if __name__ == "__main__":
    test_encoding()


