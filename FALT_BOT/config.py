import os
from dotenv import load_dotenv
dotenv_path = os.path.join(os.path.dirname(__file__), '.env')
if os.path.exists(dotenv_path):
    load_dotenv(dotenv_path)


TOKEN = os.getenv("TOKEN")
ADMIN_CHAT_ID = os.getenv("ADMIN_CHAT_ID")
DB_PATH = os.getenv("DB_PATH")
LAUNDRY_DATA_PATH = os.getenv("LAUNDRY_DATA_PATH")
YOOKASSA_SHOP_ID = os.getenv("YOOKASSA_SHOP_ID")
YOOKASSA_SECRET_KEY = os.getenv("YOOKASSA_SECRET_KEY")
YOOKASSA_RETURN_URL = os.getenv("YOOKASSA_RETURN_URL")
LAUNDRY_PRICE_PER_HOUR_RUB = os.getenv("LAUNDRY_PRICE_PER_HOUR_RUB", "75")
LAUNDRY_PRICE_PER_HOUR_WASH_RUB = os.getenv("LAUNDRY_PRICE_PER_HOUR_WASH_RUB")
LAUNDRY_PRICE_PER_HOUR_DRY_RUB = os.getenv("LAUNDRY_PRICE_PER_HOUR_DRY_RUB")
LAUNDRY_CANCEL_DEADLINE_MINUTES = os.getenv("LAUNDRY_CANCEL_DEADLINE_MINUTES", "15")
