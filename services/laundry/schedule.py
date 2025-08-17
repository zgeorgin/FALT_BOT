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
            booked_start, booked_end = booking[0], booking[1]
            if datetime.strptime(booked_start, "%H:%M") < datetime.strptime(end_time, "%H:%M") <= datetime.strptime(booked_end, "%H:%M") or datetime.strptime(booked_start, "%H:%M") <= datetime.strptime(start_time, "%H:%M") < datetime.strptime(booked_end, "%H:%M") or datetime.strptime(start_time, "%H:%M") < datetime.strptime(booked_end, "%H:%M") <= datetime.strptime(end_time, "%H:%M") or datetime.strptime(start_time, "%H:%M") <= datetime.strptime(booked_start, "%H:%M") < datetime.strptime(end_time, "%H:%M"):
                return False  # Время занято

        return True
    
    def add_booking(self, date, machine_id, start_time, end_time, label, user_id=None):
        if date not in self.schedule:
            self.schedule[date] = {}
        if machine_id not in self.schedule[date]:
            self.schedule[date][machine_id] = []
        record = [start_time, end_time, label] if user_id is None else [start_time, end_time, label, str(user_id)]
        self.schedule[date][machine_id].append(record)
        self.save_schedule()

    def get_user_bookings(self, user_id):
        res = []
        uid = str(user_id)
        for date, machines in self.schedule.items():
            for machine_id, items in machines.items():
                for booking in items:
                    if len(booking) >= 4 and str(booking[3]) == uid:
                        res.append((date, machine_id, booking[0], booking[1], booking[2]))
        return sorted(res, key=lambda x: (x[0], x[1], x[2]))

    def remove_booking(self, date, machine_id, start_time, end_time, user_id):
        uid = str(user_id)
        if date not in self.schedule or machine_id not in self.schedule[date]:
            return False
        items = self.schedule[date][machine_id]
        new_items = []
        removed = False
        for booking in items:
            bs, be = booking[0], booking[1]
            owner_ok = len(booking) >= 4 and str(booking[3]) == uid
            if bs == start_time and be == end_time and owner_ok and not removed:
                removed = True
                continue
            new_items.append(booking)
        if removed:
            self.schedule[date][machine_id] = new_items
            self.save_schedule()
        return removed
