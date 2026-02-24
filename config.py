import os
from dotenv import load_dotenv

dotenv_path = os.path.join(os.path.dirname(__file__), ".env")
if os.path.exists(dotenv_path):
    load_dotenv(dotenv_path)

# Telegram Bot
TOKEN = os.getenv("TOKEN")
ADMIN_CHAT_ID = os.getenv("ADMIN_CHAT_ID")

# Database
DB_PATH = os.getenv("DB_PATH", "database/falt.db")
LAUNDRY_DATA_PATH = os.getenv("LAUNDRY_DATA_PATH", "data/schedule.json")

# YooKassa
YOOKASSA_SHOP_ID = os.getenv("YOOKASSA_SHOP_ID")
YOOKASSA_SECRET_KEY = os.getenv("YOOKASSA_SECRET_KEY")
YOOKASSA_RETURN_URL = os.getenv("YOOKASSA_RETURN_URL")

# Laundry pricing
LAUNDRY_PRICE_PER_HOUR_RUB = os.getenv("LAUNDRY_PRICE_PER_HOUR_RUB", "75")
LAUNDRY_PRICE_PER_HOUR_WASH_RUB = os.getenv("LAUNDRY_PRICE_PER_HOUR_WASH_RUB", "75")
LAUNDRY_PRICE_PER_HOUR_DRY_RUB = os.getenv("LAUNDRY_PRICE_PER_HOUR_DRY_RUB", "75")

# Mini App
MINI_APP_URL = os.getenv("MINI_APP_URL", "")  # Обязательно задать в .env!
WEBAPP_HOST = os.getenv("WEBAPP_HOST", "0.0.0.0")
WEBAPP_PORT = int(os.getenv("WEBAPP_PORT", "8000"))

# JWT для Mini App сессий
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY")  # Генерировать: python -c "import secrets; print(secrets.token_hex(32))"
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
JWT_EXPIRATION_DAYS = int(os.getenv("JWT_EXPIRATION_DAYS", "7"))

# CORS
CORS_ORIGINS = os.getenv("CORS_ORIGINS", "*").split(",")

# Debug
DEBUG = os.getenv("DEBUG", "False").lower() in ("true", "1", "yes")
