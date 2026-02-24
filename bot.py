import logging
import asyncio
import os

from aiogram import Bot, Dispatcher
from aiogram.types import BotCommand, BotCommandScopeDefault

from handlers.main_menu_handler import main_router
from handlers.registration_handler import reg_router
from handlers.admin_interaction_handler import admin_router
from handlers.laundry_handler import laundry_router
from handlers.admin_manage_laundry import manage_laundry_router
from handlers.study_room_handler import sr_router
from handlers.wallet_handler import wallet_router
from handlers.email_handler import email_router
from handlers.mini_app_handler import mini_app_router

from database.db import init_db
from config import TOKEN

os.makedirs("logs", exist_ok=True)
os.makedirs("data", exist_ok=True)
os.makedirs("database", exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    filename="logs/logs.txt",
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)


async def set_commands(bot: Bot):
    commands = [
        BotCommand(command="start", description="Главное меню"),
        BotCommand(command="miniapp", description="Открыть Mini App"),
        BotCommand(command="setemail", description="Привязать email к Mini App"),
        BotCommand(command="wallet", description="Кошелёк"),
        BotCommand(command="bookings", description="Мои записи"),
    ]
    await bot.set_my_commands(scope=BotCommandScopeDefault(), commands=commands)


async def main():
    init_db()

    bot = Bot(token=TOKEN)
    dp = Dispatcher()

    dp.include_router(main_router)
    dp.include_router(reg_router)
    dp.include_router(admin_router)
    dp.include_router(laundry_router)
    dp.include_router(manage_laundry_router)
    dp.include_router(sr_router)
    dp.include_router(wallet_router)
    dp.include_router(email_router)
    dp.include_router(mini_app_router)

    await set_commands(bot)
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
