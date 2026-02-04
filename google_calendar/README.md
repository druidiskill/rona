# Настройка Google Calendar API

## 1. Создание проекта в Google Cloud Console

1. Перейдите в [Google Cloud Console](https://console.cloud.google.com/)
2. Создайте новый проект или выберите существующий
3. Включите Google Calendar API:
   - Перейдите в "APIs & Services" > "Library"
   - Найдите "Google Calendar API"
   - Нажмите "Enable"

## 2. Создание учетных данных

1. Перейдите в "APIs & Services" > "Credentials"
2. Нажмите "Create Credentials" > "OAuth client ID"
3. Выберите "Desktop application"
4. Введите название (например, "RONA Photo Studio Bot")
5. Нажмите "Create"
6. Скачайте файл JSON с учетными данными
7. Переименуйте файл в `credentials.json`
8. Поместите файл в папку `google_calendar/`

## 3. Структура файла credentials.json

Файл должен выглядеть примерно так:

```json
{
  "installed": {
    "client_id": "123456789012-abcdefghijklmnopqrstuvwxyz123456.apps.googleusercontent.com",
    "project_id": "your-project-name-123456",
    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
    "token_uri": "https://oauth2.googleapis.com/token",
    "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
    "client_secret": "GOCSPX-abcdefghijklmnopqrstuvwxyz123456",
    "redirect_uris": ["http://localhost"]
  }
}
```

**Важно:** Не коммитьте этот файл в Git! Он содержит секретные ключи.

## 3. Структура файлов

```
google_calendar/
├── README.md
├── credentials.json  # Скачанный файл с учетными данными
├── token.json        # Автоматически создается после первой авторизации
└── calendar_service.py
```

## 4. Первый запуск

При первом запуске:
1. Откроется браузер для авторизации
2. Войдите в свой Google аккаунт
3. Разрешите доступ к календарю
4. Файл `token.json` будет создан автоматически

## 5. Использование

```python
from google_calendar.calendar_service import get_calendar_service

# Получение сервиса
service = await get_calendar_service()

# Проверка доступности времени
is_available = await service.check_time_availability(
    start_time=datetime(2024, 1, 15, 10, 0),
    end_time=datetime(2024, 1, 15, 11, 0)
)

# Получение свободных слотов
free_slots = await service.get_free_slots(
    date=datetime(2024, 1, 15),
    duration_minutes=60
)
```

## 6. Безопасность

- Не коммитьте файлы `credentials.json` и `token.json` в Git
- Добавьте их в `.gitignore`
- Регулярно обновляйте токены доступа
