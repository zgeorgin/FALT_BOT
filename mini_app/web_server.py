"""
Mini App Web Server — FastAPI
Запуск: uvicorn mini_app.web_server:app --host 0.0.0.0 --port 8000
"""
import sys
import os
import re
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi import FastAPI, HTTPException, Depends, Header, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta

from database.db import (
    get_user_by_email, is_registered, create_mini_app_session,
    validate_session, update_user_email, get_wallet_balance,
    debit_wallet, credit_wallet, get_machine_names, get_machine_status,
    get_connection
)
from services.laundry.schedule import Schedule
from config import (
    CORS_ORIGINS, LAUNDRY_DATA_PATH
)

app = FastAPI(title="FALT Laundry Mini App", version="2.1")

_static_dir = os.path.join(os.path.dirname(__file__), "static")
if os.path.exists(_static_dir):
    app.mount("/static", StaticFiles(directory=_static_dir), name="static")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

_static_dir = os.path.join(os.path.dirname(__file__), "static")
if os.path.exists(_static_dir):
    app.mount("/static", StaticFiles(directory=_static_dir), name="static")

# ═══════════════════════════════════════════════════════════════════════════════
# МОДЕЛИ
# ═══════════════════════════════════════════════════════════════════════════════

class LoginRequest(BaseModel):
    email: EmailStr
    telegram_id: Optional[int] = None

class BookingSlot(BaseModel):
    date: str = Field(..., pattern=r"^\d{2}\.\d{2}\.\d{4}$")
    machine_id: str
    start_time: str = Field(..., pattern=r"^\d{2}:\d{2}$")
    end_time: str = Field(..., pattern=r"^\d{2}:\d{2}$")

class MultiBookingRequest(BaseModel):
    bookings: List[BookingSlot]

class CancelRequest(BaseModel):
    date: str
    machine_id: str
    start_time: str
    end_time: str

# ═══════════════════════════════════════════════════════════════════════════════
# AUTH
# ═══════════════════════════════════════════════════════════════════════════════

async def get_current_user(authorization: str = Header(None)) -> int:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Not authenticated")
    token = authorization.split(" ", 1)[1]
    user_id = validate_session(token)
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid or expired session")
    return user_id

@app.get("/", response_class=HTMLResponse)
async def serve_index():
    template = os.path.join(os.path.dirname(__file__), "templates", "index.html")
    with open(template, encoding="utf-8") as f:
        return f.read()

@app.post("/api/auth/login")
async def login(req: LoginRequest):
    user = get_user_by_email(req.email)
    if not user:
        raise HTTPException(status_code=404, detail="Пользователь не найден")
    
    token = create_mini_app_session(user.user_id, device_info="Mini App")
    return {
        "success": True,
        "token": token,
        "user": {
            "id": user.user_id,
            "name": user.name,
            "surname": user.surname,
            "email": user.email,
            "wallet": get_wallet_balance(user.user_id),
        },
    }

# ═══════════════════════════════════════════════════════════════════════════════
# MACHINES & SLOTS (ПОЧАСОВЫЕ, 50₽/ЧАС)
# ═══════════════════════════════════════════════════════════════════════════════

PRICE_PER_HOUR = 50

@app.get("/api/machines")
async def get_machines():
    machines = []
    for name in get_machine_names():
        m = re.search(r"(\d+)", name)
        mid = m.group(1) if m else name
        machines.append({
            "id": mid,
            "name": name,
            "is_working": get_machine_status(name),
            "price_per_hour": PRICE_PER_HOUR,
        })
    return machines

@app.get("/api/slots/{date}")
async def get_slots(date: str):
    try:
        datetime.strptime(date, "%d.%m.%Y")
    except ValueError:
        raise HTTPException(status_code=400, detail="Формат: DD.MM.YYYY")

    schedule = Schedule(LAUNDRY_DATA_PATH)
    schedule.load_schedule()

    result = {}
    for name in get_machine_names():
        if not get_machine_status(name):
            continue
            
        m = re.search(r"(\d+)", name)
        mid = m.group(1) if m else name
        
        slots = []
        # Слоты по 1 часу: 00:00-01:00, 01:00-02:00 ... 23:00-23:59
        for hour in range(0, 24):
            start = f"{hour:02d}:00"
            end = f"{hour+1:02d}:00" if hour < 23 else "23:59"
            
            available = schedule.is_time_available(date, mid, start, end)
            booked_by = None
            if not available and date in schedule.schedule and mid in schedule.schedule[date]:
                for booking in schedule.schedule[date][mid]:
                    if booking[0] == start and booking[1] == end:
                        booked_by = booking[2] if len(booking) > 2 else "Занято"
                        break
            
            slots.append({
                "start": start,
                "end": end,
                "available": available,
                "booked_by": booked_by
            })
        
        result[mid] = {
            "name": name,
            "slots": slots
        }

    return {"date": date, "machines": result}

# ═══════════════════════════════════════════════════════════════════════════════
# BOOKINGS (ЕДИНЫЙ API)
# ═══════════════════════════════════════════════════════════════════════════════

@app.post("/api/bookings/create")
async def create_booking(req: MultiBookingRequest, user_id: int = Depends(get_current_user)):
    """Создание брони: проверка → списание 50₽/час → запись в schedule.json"""
    user = is_registered(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    schedule = Schedule(LAUNDRY_DATA_PATH)
    schedule.load_schedule()

    # Проверяем доступность
    for b in req.bookings:
        if not schedule.is_time_available(b.date, b.machine_id, b.start_time, b.end_time):
            raise HTTPException(status_code=400, detail=f"Слот {b.start_time}-{b.end_time} занят")

    # Считаем стоимость: 50₽ × количество часов
    total_hours = len(req.bookings)  # Каждая бронь = 1 час
    total = total_hours * PRICE_PER_HOUR

    # Проверяем баланс
    balance = get_wallet_balance(user_id)
    if balance < total:
        raise HTTPException(status_code=400, detail=f"Недостаточно средств: нужно {total}₽")

    # Списываем
    if not debit_wallet(user_id, total, "laundry_booking"):
        raise HTTPException(status_code=400, detail="Ошибка списания")

    # Создаем брони
    label = f"{user.surname} {user.name[0]}."
    for b in req.bookings:
        schedule.add_booking(b.date, b.machine_id, b.start_time, b.end_time, label, str(user_id))

    return {
        "success": True,
        "charged": total,
        "new_balance": get_wallet_balance(user_id)
    }

@app.get("/api/bookings/my")
async def my_bookings(user_id: int = Depends(get_current_user)):
    schedule = Schedule(LAUNDRY_DATA_PATH)
    schedule.load_schedule()
    bookings = schedule.get_user_bookings(str(user_id))
    
    return {"bookings": [
        {"date": d, "machine_id": m, "start_time": b, "end_time": e, "label": label}
        for d, m, b, e, label in bookings
    ]}

@app.post("/api/bookings/cancel")
async def cancel_booking(req: CancelRequest, user_id: int = Depends(get_current_user)):
    schedule = Schedule(LAUNDRY_DATA_PATH)
    schedule.load_schedule()
    
    ok = schedule.remove_booking(req.date, req.machine_id, req.start_time, req.end_time, str(user_id))
    if not ok:
        raise HTTPException(status_code=400, detail="Бронь не найдена")

    # Возврат 50₽ за час
    credit_wallet(user_id, PRICE_PER_HOUR, "laundry_cancel")
    
    return {"success": True, "refund": PRICE_PER_HOUR}

@app.get("/api/wallet/balance")
async def get_balance(user_id: int = Depends(get_current_user)):
    return {"balance": get_wallet_balance(user_id)}

@app.get("/api/health")
async def health():
    return {"status": "ok", "version": "2.1"}

@app.get("/app.js")
async def serve_app_js():
    with open(os.path.join(os.path.dirname(__file__), "app.js"), encoding="utf-8") as f:
        return f.read()