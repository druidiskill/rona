import os
from dotenv import load_dotenv

load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

VK_BOT_TOKEN = os.getenv("VK_BOT_TOKEN")
VK_GROUP_ID = os.getenv("VK_GROUP_ID")

GOOGLE_CALENDAR_ID = os.getenv("GOOGLE_CALENDAR_ID")
GOOGLE_CREDENTIALS_FILE = os.getenv(
    "GOOGLE_CREDENTIALS_FILE", "google_calendar/calendar_properties_primary.json"
)
GOOGLE_TOKEN_FILE = os.getenv(
    "GOOGLE_TOKEN_FILE", "google_calendar/calendar_properties_primary.json"
)

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///photostudio.db")

ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "admin")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "admin")

ADMIN_IDS_TG = os.getenv("ADMIN_IDS_TG", "")
ADMIN_IDS_VK = os.getenv("ADMIN_IDS_VK", "")

