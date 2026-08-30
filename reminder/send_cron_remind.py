import sys
import asyncio
from aiogram import Bot
from crontab import CronTab
from filelock import FileLock

from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))

from config import TOKEN
from reminder.reminder_tools import CRON_LOCK_PATH


async def send(chat_id: int, message: str, comment: str):
    # удаляем напоминалку безопасно
    with FileLock(CRON_LOCK_PATH):
        cron = CronTab(user=True)
        cron.remove_all(comment=comment)
        cron.write()

    bot = Bot(token=TOKEN)
    await bot.send_message(
        chat_id,
        message
    )
    await bot.session.close()

if __name__ == "__main__":
    if len(sys.argv) != 4:
        raise RuntimeError(
            f"Reminder service got unexpected amount of arguments: {len(sys.argv)}! (expected 4)"
        )

    # тут бы ошибки половить, вдруг косо с крона прилетит, но чета лень лол
    chat_id = int(sys.argv[1])
    msg = sys.argv[2]
    # для корректного удаления увед с кронтаба нужно брать номер стиралки + таймстамп записи
    comm = sys.argv[3]

    asyncio.run(send(chat_id, msg, comm))
