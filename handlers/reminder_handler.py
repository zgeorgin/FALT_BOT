from crontab import CronTab
from datetime import datetime, timedelta
import sys
from pathlib import Path


# TODO: в идеале бы сделать ремайндеры настраиваемыми
# аля типа напомните мне за 5 минут до и после начала стирки

def add_reminders(chat_id: int, event_time: datetime, machine_num: int):
    cron = CronTab(user=True)  # текущий пользователь

    # тут возможно стоит чуть получше сделать, но пока так придумал
    base_dir = Path(__file__).parent
    # скрипт который шлет напоминание
    script_path = base_dir.parent / "reminder" / "send_cron_remind.py"
    # todo: поменять если у нас питон какой-то особенный надо запускать
    python_path = sys.executable


    reminders = [
        (event_time - timedelta(minutes=15),
         f"🔔 Напоминаем о стирке в машинке №{machine_num}. До начала осталось 15 минут."
         ),
        (event_time - timedelta(minutes=5),
         f"🔔 Напоминаем о стирке в машинке №{machine_num}. До начала 5 минут!"
         ),
        (event_time,
         f"⏰ Напоминаем, что машинка №{machine_num} ждет вас!"
         ),
    ]

    for remind_time, msg in reminders:
        if remind_time < datetime.now():
            continue

        ts = remind_time.strftime("%d_%H_%M_%S")

        comment = f"reminder_{chat_id}_{ts}_wm_{machine_num}"
        command = f'{python_path} {script_path} {chat_id} "{msg}" "{comment}"'

        # напоминалка должна быть уникальной...
        job = cron.new(command=command, comment=comment)
        job.setall(
            remind_time.minute,
            remind_time.hour,
            remind_time.day,
            remind_time.month,
            "*"
        )

    cron.write()
