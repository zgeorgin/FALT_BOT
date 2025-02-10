import matplotlib.pyplot as plt
from datetime import datetime, timedelta
from PIL import Image, ImageDraw, ImageFont

def plot_schedule(schedule, date, filepath):
    """
    Отрисовывает расписание на заданную дату.

    :param schedule: словарь расписания в формате {дата: {машина: [[начало, конец], ...]}}
    :param date: дата для отображения расписания (строка в формате "ГГГГ-ММ-ДД")
    :return: изображение (Matplotlib Figure)
    """

    # Параметры графика
    machines = [str(i) for i in range(1, 7)]
    num_machines = 6
    time_slots = [f"{hour:02}:00" for hour in range(0, 25, 2)]  # Шкала времени (по 2 часа)
    y_ticks = range(len(time_slots))  # Чтобы подстроить шкалу времени в графике

    fig, ax = plt.subplots(figsize=(15, 8))  # Определяем размер графика
    ax.set_title(f"Расписание на {date}", fontsize=16, pad=20)
    
    # Рисуем временные рамки для каждой машины
    for i, machine_id in enumerate(machines):
        # Границы столбца машины
        x_left = i
        x_right = i + 1
        ax.vlines(x=[x_left, x_right], ymin=0, ymax=24, colors="black", linewidth=0.5)

        # Записываем название машин (номер/подпись)
        label = f"#{machine_id}"
        ax.text((x_left + x_right) / 2, 24.5, label, ha="center", va="center", fontsize=12)

    
    if date in schedule.keys():
        for i, machine_id in enumerate(machines):
            x_left = i
            x_right = i + 1
            # Отображаем записи для машины
            if machine_id not in schedule[date].keys():
                continue
            
            bookings = schedule[date][machine_id]
            for booking in bookings:
                start_time = datetime.strptime(booking[0], "%H:%M").time()
                end_time = datetime.strptime(booking[1], "%H:%M").time()
                label = booking[2]
                # Конвертация времени в индексы для отрисовки
                start_hours = 24 - start_time.hour - start_time.minute / 60
                end_hours = 24 - end_time.hour - end_time.minute / 60

                # Создаём прямоугольник для записи
                ax.fill_betweenx(
                    [start_hours, end_hours],
                    x_left,
                    x_right,
                    color="skyblue",
                    edgecolor="black",
                    linewidth=0.5,
                )
                # Подпись внутри слота
                middle_time = (start_hours + end_hours) / 2
                ax.text(
                    (x_left + x_right) / 2,
                    middle_time,
                    f"{label} \n {booking[0]}-{booking[1]}",
                    ha="center",
                    va="center",
                    fontsize=10,
                )

    # Настройка шкалы времени
    ax.set_yticks(range(25))
    ax.set_yticklabels([f"{hour:02}:00" for hour in reversed(range(25))])
    ax.set_xlim(0, num_machines)
    ax.set_ylim(0, 24)
    ax.set_xticks([])  # Убираем Ось X

    ax.xaxis.set_visible(False)  # Убираем горизонтальные линии оси

    # Настройка сетки
    ax.grid(axis="y", color="gray", linestyle="--", linewidth=0.5)

    plt.tight_layout()
    plt.savefig(filepath)