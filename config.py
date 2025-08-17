import os
from dotenv import load_dotenv
dotenv_path = os.path.join(os.path.dirname(__file__), '.env')
if os.path.exists(dotenv_path):
    load_dotenv(dotenv_path)


TOKEN = os.getenv("TOKEN")
ADMIN_CHAT_ID = os.getenv("ADMIN_CHAT_ID")
DB_PATH = os.getenv("DB_PATH")
LAUNDRY_DATA_PATH = os.getenv("LAUNDRY_DATA_PATH")