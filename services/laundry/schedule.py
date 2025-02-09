import json
from datetime import datetime

class Schedule():
    def __init__(self, filepath):
        self.filepath = filepath
        self.schedule = None
    
    def load_schedule(self):
        try:
            with open(self.filepath, "r") as file:
                self.schedule = json.load(file)
        except FileNotFoundError:
            self.schedule = {}
    
    def save_schedule(self):
        with open(self.filepath, "w") as file:
            json.dump(self.schedule, file, indent=4)
            
    def is_time_available(self, date, machine_id, start_time, end_time):
        if date not in self.schedule or machine_id not in self.schedule[date]:
            return True  # Если нет записей на эту дату/машину, она свободна

        for booking in self.schedule[date][machine_id]:
            # Проверяем на пересечение интервалов (занятые слоты)
            booked_start, booked_end, _ = booking
            if not (end_time <= booked_start or start_time >= booked_end):
                return False  # Время занято

        return True
    
    def add_booking(self, date, machine_id, start_time, end_time, label):
        if date not in self.schedule:
            self.schedule[date] = {}
        if machine_id not in self.schedule[date]:
            self.schedule[date][machine_id] = []

        # Добавляем новую запись
        self.schedule[date][machine_id].append([start_time, end_time, label])
        self.save_schedule()  # Сохраняем изменения
