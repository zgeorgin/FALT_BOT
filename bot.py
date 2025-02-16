import logging
from aiogram import Bot, Dispatcher
import asyncio
from handlers.main_menu_handler import main_router
from handlers.registration_handler import reg_router
from handlers.admin_interaction_handler import admin_router
from handlers.laundry_handler import laundry_router
from aiogram.methods import set_my_commands
from aiogram.types import BotCommand, BotCommandScopeDefault
from database.db import init_db
from config import TOKEN
bot = Bot(token=TOKEN)
dp = Dispatcher()

logging.basicConfig(level=logging.INFO, filename="logs/logs.txt")

async def set_commands():
    commands = [BotCommand(command='start', description='Начать работу с ботом')]
    await bot.set_my_commands(scope=BotCommandScopeDefault(), commands=commands)

async def main():
    init_db()
    dp.include_router(main_router)
    dp.include_router(reg_router)
    dp.include_router(admin_router)
    dp.include_router(laundry_router)
    await dp.start_polling(bot)
    await set_commands()
    
    
if __name__ == "__main__":
    asyncio.run(main())