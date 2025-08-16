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
        if datetime.strptime(end_time, "%H:%M") <= datetime.strptime(start_time, "%H:%M"):
            return False #Время должно быть от меньшего к большему
        
        if date not in self.schedule.keys() or machine_id not in self.schedule[date].keys():
            return True  # Если нет записей на эту дату/машину, она свободна

        for booking in self.schedule[date][machine_id]:
            # Проверяем на пересечение интервалов (занятые слоты)
            booked_start, booked_end, _ = booking
            if datetime.strptime(booked_start, "%H:%M") < datetime.strptime(end_time, "%H:%M") <= datetime.strptime(booked_end, "%H:%M") or datetime.strptime(booked_start, "%H:%M") <= datetime.strptime(start_time, "%H:%M") < datetime.strptime(booked_end, "%H:%M") or datetime.strptime(start_time, "%H:%M") < datetime.strptime(booked_end, "%H:%M") <= datetime.strptime(end_time, "%H:%M") or datetime.strptime(start_time, "%H:%M") <= datetime.strptime(booked_start, "%H:%M") < datetime.strptime(end_time, "%H:%M"):
                return False  # Время занято

        return True
    
    def add_booking(self, date, machine_id, start_time, end_time, label):
        if date not in self.schedule:
            self.schedule[date] = {}
        if machine_id not in self.schedule[date]:
            self.schedule[date][machine_id] = []

        self.schedule[date][machine_id].append([start_time, end_time, label])
        self.save_schedule()
