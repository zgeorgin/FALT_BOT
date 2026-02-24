#!/usr/bin/env python3
"""
Единый запуск Telegram-бота и Mini App сервера.
Использовать для Railway/Docker: python start_all.py
"""
import asyncio
import logging
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.makedirs("logs", exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("logs/logs.txt"),
    ],
)
log = logging.getLogger("start_all")


async def run_bot():
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

    init_db()
    bot = Bot(token=TOKEN)
    dp = Dispatcher()

    for router in [main_router, reg_router, admin_router, laundry_router,
                   manage_laundry_router, sr_router, wallet_router,
                   email_router, mini_app_router]:
        dp.include_router(router)

    await bot.set_my_commands(
        scope=BotCommandScopeDefault(),
        commands=[
            BotCommand(command="start", description="Главное меню"),
            BotCommand(command="miniapp", description="Открыть Mini App"),
            BotCommand(command="setemail", description="Привязать email"),
            BotCommand(command="wallet", description="Кошелёк"),
        ],
    )
    log.info("Bot started polling")
    await dp.start_polling(bot)


async def run_webapp():
    import uvicorn
    from config import WEBAPP_HOST, WEBAPP_PORT

    port = int(os.getenv("PORT", WEBAPP_PORT))  # Railway задаёт $PORT
    config = uvicorn.Config(
        "mini_app.web_server:app",
        host=WEBAPP_HOST,
        port=port,
        log_level="info",
    )
    server = uvicorn.Server(config)
    log.info(f"Mini App starting on {WEBAPP_HOST}:{port}")
    await server.serve()


async def main():
    log.info("Starting FALT Bot + Mini App")
    await asyncio.gather(run_bot(), run_webapp())


if __name__ == "__main__":
    asyncio.run(main())
