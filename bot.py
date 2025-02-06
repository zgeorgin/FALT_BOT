import logging
from aiogram import Bot, Dispatcher, executor
from handlers import main_handlers, user_handlers, admin_handlers
from database.db import init_db
import os

logging.basicConfig(level=logging.INFO)

TOKEN = os.environ.get("TOKEN")

bot = Bot(token=TOKEN)
init_db()

