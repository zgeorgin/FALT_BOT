import sqlite3

from crontab import CronTab
from datetime import datetime, timedelta
from filelock import FileLock
import tempfile
import sys
from pathlib import Path
import json
sys.path.append(str(Path(__file__).parent.parent))

from config import LAUNDRY_DATA_PATH, DB_PATH

# TODO: в идеале бы сделать ремайндеры настраиваемыми
# аля типа напомните мне за 5 минут до и после начала стирки

# напоминалка и основной бот могут устроить гонку за ресурсом
# поэтому нада аля мьютексы
CRON_LOCK_PATH = Path(tempfile.gettempdir()) / "falt_wash_cron.lock"

_REMINDER_OFFSETS = (timedelta(minutes=15), timedelta(minutes=5), timedelta(0))


def _reminder_texts(machine_num: int):
    return {
        _REMINDER_OFFSETS[0]: f"🔔 Напоминаем о стирке в машинке №{machine_num}. До начала осталось 15 минут.",
        _REMINDER_OFFSETS[1]: f"🔔 Напоминаем о стирке в машинке №{machine_num}. До начала 5 минут!",
        _REMINDER_OFFSETS[2]: f"⏰ Напоминаем, что машинка №{machine_num} ждет вас!",
    }


def _reminder_comment(chat_id: int, remind_time: datetime, machine_num: int) -> str:
    ts = remind_time.strftime("%d_%H_%M_%S")
    return f"reminder_{chat_id}_{ts}_wm_{machine_num}"


def add_reminders(chat_id: int, event_time: datetime, machine_num: int):
    base_dir = Path(__file__).parent
    # скрипт который шлет напоминание
    script_path = base_dir.parent / "reminder" / "send_cron_remind.py"
    # todo: поменять если у нас питон какой-то особенный надо запускать
    python_path = sys.executable

    texts = _reminder_texts(machine_num)

    with FileLock(CRON_LOCK_PATH):
        cron = CronTab(user=True)  # текущий пользователь

        for offset in _REMINDER_OFFSETS:
            remind_time = event_time - offset
            if remind_time < datetime.now():
                continue

            comment = _reminder_comment(chat_id, remind_time, machine_num)
            command = f'{python_path} {script_path} {chat_id} "{texts[offset]}" "{comment}"'

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


def remove_reminders(chat_id: int, event_time: datetime, machine_num: int):
    with FileLock(CRON_LOCK_PATH):
        cron = CronTab(user=True)
        for offset in _REMINDER_OFFSETS:
            remind_time = event_time - offset
            comment = _reminder_comment(chat_id, remind_time, machine_num)
            cron.remove_all(comment=comment)
        cron.write()

#гавнакод чтоб всем поставить уведы
def add_remind_to_all():
    def find_user_id(initials: str): # легаси, вместо фио теперь id
        # "marathon j." -> имя "marathon", инициал "j"
        parts = initials.strip().rstrip(".").split()
        if len(parts) < 2:
            return None

        surname = parts[0]
        name_initial = parts[1].rstrip(".")

        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT user_id FROM users
                WHERE LOWER(surname) = LOWER(?)
                AND LOWER(SUBSTR(name, 1, 1)) = LOWER(?)
                LIMIT 1
            """, (surname, name_initial))
            row = cursor.fetchone()
            return row[0] if row else None

    with open(LAUNDRY_DATA_PATH, mode="r") as f:
        data = json.load(f)

    now = datetime.now() + timedelta(minutes=20)
    for date_str, numbers in data.items():
        for num, events in numbers.items():
            for event in events:
                event_time = datetime.strptime(f"{event[0]} {date_str}", "%H:%M %d.%m.%Y")
                if event_time > now:
                    # новые записи хранят реальный chat_id - кто же знал что у нас оно есть))
                    # на старых записях без этого поля так уж и быть фолбек к фио
                    user_id = int(event[3]) if len(event) >= 4 else find_user_id(event[2])
                    if user_id is not None:
                        print(f"уведомляем: дата [{event_time}]; машинка {num}; объект {event}; user_id: {user_id}")
                        add_reminders(user_id, event_time, num)



if __name__ == "__main__":
    add_remind_to_all()
