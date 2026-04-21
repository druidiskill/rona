# 🤖 Бот для фотостудии

Telegram и VK боты для управления бронированиями фотостудии с интеграцией Google Calendar.

## Требования

- Python 3.12.x (рекомендуется).
- Python 3.14.0 сейчас не подходит, так как для pydantic-core нет готовых wheels, и установка пытается собирать пакет из исходников с Rust/MSVC.


## 📋 Возможности

### Для клиентов:
- 📸 Просмотр услуг и цен
- 📅 Бронирование времени
- 👥 Выбор количества людей
- ⏰ Настройка длительности
- 📸 Дополнительные услуги (фотограф, гримерка)
- 📱 Просмотр своих бронирований

### Для администраторов:
- 🔧 Админ-панель
- 📊 Статистика бронирований
- 📸 Управление услугами
- 👥 Управление клиентами
- 📅 Просмотр загруженности

## 🚀 Быстрый старт

### 1. Установка зависимостей

```bash
py -3.12 -m venv .venv
.\.venv\Scripts\activate
python -m pip install --upgrade pip
pip install -r requirements.txt
```

### 2. Настройка переменных окружения

Создайте файл `.env` в корне проекта:

```env
# Telegram Bot
TELEGRAM_BOT_TOKEN=your_telegram_bot_token

# VK Bot
VK_BOT_TOKEN=your_vk_bot_token
VK_GROUP_ID=your_vk_group_id

# Google Calendar
GOOGLE_CREDENTIALS_FILE=credentials.json
GOOGLE_CALENDAR_ID=your_calendar_id

# Database
DATABASE_URL=sqlite:///photostudio.db

# Admin Panel
ADMIN_PASSWORD=your_admin_password
ADMIN_USERNAME=admin
```

### 3. Настройка Google Calendar

1. Создайте проект в [Google Cloud Console](https://console.cloud.google.com/)
2. Включите Google Calendar API
3. Создайте учетные данные (OAuth 2.0)
4. Скачайте файл `credentials.json` в корень проекта
5. Укажите ID календаря в переменной `GOOGLE_CALENDAR_ID`

### 4. Запуск ботов

#### Telegram бот:
```bash
python run_telegram_bot.py
```

#### VK бот:
```bash
python run_vk_bot.py
```

### Запуск через Docker на Ubuntu

В проект уже добавлены:
- `Dockerfile`
- `docker-compose.server.yml`
- `env.docker.example`

Перед запуском убедитесь, что в корне проекта на сервере есть:
- `.env`
- `google_calendar_service_account.json`
- `photostudio.db`
- папка `app/media/` при необходимости сохранить локальные фото услуг

Быстрый запуск:

```bash
cp env.docker.example .env
# заполните .env своими значениями

docker compose -f docker-compose.server.yml up -d --build
```

Логи:

```bash
docker compose -f docker-compose.server.yml logs -f
```

Остановка:

```bash
docker compose -f docker-compose.server.yml down
```

## 📁 Структура проекта

```
RONA/
├── app/
│   ├── bootstrap/                 # Настройки, логирование, контейнер, lifecycle
│   ├── core/
│   │   └── modules/               # Общая бизнес-логика
│   ├── entrypoints/               # Точки запуска TG/VK/оба бота
│   ├── integrations/
│   │   └── local/                 # SQLite и Google Calendar
│   ├── media/                     # Медиафайлы услуг
│   ├── tests/                     # Smoke и архитектурные тесты
│   └── interfaces/
│       └── messenger/
│           ├── tg/                # Telegram transport layer
│           └── vk/                # VK transport layer
├── config.py                      # Совместимый слой конфигурации
└── requirements.txt               # Зависимости
```

Основной рабочий слой сейчас:
- `app/core/modules/`
- `app/integrations/local/`
- `app/interfaces/messenger/`
- `app/media/`
- `app/tests/`

## 🔧 Настройка админов

Для добавления администратора в Telegram боте:

1. Получите ID пользователя в Telegram
2. Добавьте запись в таблицу `admins`:

```sql
INSERT INTO admins (telegram_id, is_active) VALUES (USER_ID, 1);
```

## 📊 База данных

Система использует SQLite с асинхронным доступом через `aiosqlite`.

### Основные таблицы:
- `services` - услуги студии
- `clients` - клиенты
- `bookings` - бронирования
- `admins` - администраторы

## 🔄 Интеграция с Google Calendar

Бот автоматически:
- Проверяет свободное время в календаре
- Создает события при бронировании
- Синхронизирует загруженность

## 🛠️ Разработка

### Добавление новых команд:

1. Создайте обработчик в `app/interfaces/messenger/tg/handlers/`
2. Зарегистрируйте его в `app/interfaces/messenger/tg/handlers/__init__.py`
3. Добавьте клавиатуру в `app/interfaces/messenger/tg/keyboards.py`

### Добавление новых услуг:

1. Используйте админ-панель в боте
2. Или добавьте напрямую в БД:

```sql
INSERT INTO services (name, description, max_num_clients, price_min, price_min_weekend, min_duration_minutes, duration_step_minutes) 
VALUES ('Новая услуга', 'Описание', 4, 5000.0, 6000.0, 60, 30);
```

## 📞 Поддержка

При возникновении проблем:
1. Проверьте логи бота
2. Убедитесь в правильности токенов
3. Проверьте настройки Google Calendar API

## 📝 Лицензия

Проект создан для внутреннего использования фотостудии.


