import os

# Telegram Bot
TELEGRAM_BOT_TOKEN = "6904258299:AAHFNHi6KYpMkrcztIDfLS-m78Vd74PqDo0"

# VK Bot
VK_BOT_TOKEN = os.getenv('VK_BOT_TOKEN')
VK_GROUP_ID = int(os.getenv('VK_GROUP_ID', 0))

# Google Calendar
GOOGLE_CREDENTIALS_FILE = os.getenv('GOOGLE_CREDENTIALS_FILE', 'credentials.json')
GOOGLE_CALENDAR_ID = os.getenv('GOOGLE_CALENDAR_ID')

# Database
DATABASE_URL = os.getenv('DATABASE_URL', 'sqlite:///photostudio.db')
