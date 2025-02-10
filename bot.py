import logging
from aiogram import Bot, Dispatcher
import asyncio
from handlers.main_menu_handler import main_router
from handlers.registration_handler import reg_router
from handlers.admin_interaction_handler import admin_router
from handlers.laundry_handler import laundry_router
from database.db import init_db
import os
from dotenv import load_dotenv
dotenv_path = os.path.join(os.path.dirname(__file__), '.env')
if os.path.exists(dotenv_path):
    load_dotenv(dotenv_path)

logging.basicConfig(level=logging.INFO)

TOKEN = os.getenv("TOKEN")

bot = Bot(token=TOKEN)
dp = Dispatcher()
async def main():
    init_db()
    dp.include_router(main_router)
    dp.include_router(reg_router)
    dp.include_router(admin_router)
    dp.include_router(laundry_router)
    await dp.start_polling(bot)
    
    
if __name__ == "__main__":
    asyncio.run(main())