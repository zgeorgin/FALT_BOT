# Интеграция Mini App в FALT_BOT - Полная документация

## 📋 Сводка изменений

### Что было добавлено из FALT_BOT_NEW

| Компонент | Назначение | Файл |
|-----------|-----------|------|
| **Mini App Server** | FastAPI веб-сервер | `mini_app/web_server.py` |
| **Web Interface** | HTML/JS интерфейс | `mini_app/templates/index.html` |
| **Email Handler** | Привязка email | `handlers/email_handler.py` |
| **Mini App Handler** | Команды /miniapp, /bookings | `handlers/mini_app_handler.py` |
| **JWT Auth** | Сессии Mini App | `database/db.py` (функции) |
| **Unified Config** | Объединенная конфигурация | `config.py` |
| **Migration Script** | Миграция БД | `migrate.py` |
| **Docker Support** | Контейнеризация | `Dockerfile`, `docker-compose.yml` |
| **Railway Config** | Деплой на Railway | `railway.json`, `Procfile` |

### Ключевые изменения в существующих файлах

#### 1. `database/db.py`
**Добавлено:**
- Поле `email` в класс `User`
- Функция `get_user_by_email()` - поиск по email
- Функция `update_user_email()` - обновление email
- Функция `create_mini_app_session()` - создание JWT токена
- Функция `validate_session()` - проверка токена
- Таблица `mini_app_sessions` в `init_db()`

**Сохранено:** Все существующие функции FALT_BOT без изменений

#### 2. `config.py`
**Добавлено:**
```python
# Mini App
MINI_APP_URL = os.getenv("MINI_APP_URL", "")
WEBAPP_HOST = os.getenv("WEBAPP_HOST", "0.0.0.0")
WEBAPP_PORT = int(os.getenv("WEBAPP_PORT", "8000"))

# JWT
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY")
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
JWT_EXPIRATION_DAYS = int(os.getenv("JWT_EXPIRATION_DAYS", "7"))

# CORS
CORS_ORIGINS = os.getenv("CORS_ORIGINS", "*").split(",")
```

#### 3. `bot.py`
**Добавлено:**
```python
from handlers.email_handler import email_router
from handlers.mini_app_handler import mini_app_router

# В main():
dp.include_router(email_router)
dp.include_router(mini_app_router)

# Новые команды в set_commands():
BotCommand(command="miniapp", description="Открыть Mini App"),
BotCommand(command="setemail", description="Привязать email к Mini App"),
BotCommand(command="bookings", description="Мои записи"),
```

#### 4. `requirements.txt`
**Добавлено:**
```
fastapi==0.115.0
uvicorn[standard]==0.32.0
python-multipart==0.0.12
pydantic[email]==2.10.6
email-validator==2.2.0
```

## 🔧 Переменные окружения

### Обязательные (из существующего FALT_BOT)
- `TOKEN` - токен Telegram бота
- `ADMIN_CHAT_ID` - ID администратора

### Новые обязательные для Mini App
- `MINI_APP_URL` - HTTPS URL деплоя (например, `https://falt-bot.up.railway.app`)
- `JWT_SECRET_KEY` - секретный ключ для JWT (генерируется командой `python -c "import secrets; print(secrets.token_hex(32))"`)

### Опциональные
- `WEBAPP_HOST` - хост для FastAPI (default: `0.0.0.0`)
- `WEBAPP_PORT` - порт для FastAPI (default: `8000`)
- `JWT_EXPIRATION_DAYS` - срок жизни сессии (default: `7`)
- `CORS_ORIGINS` - разрешенные домены для CORS (default: `*`)

## 🚀 Пошаговая инструкция по деплою

### Шаг 1: Миграция базы данных
```bash
# На сервере с существующей БД
python migrate.py
```
Это добавит:
- Колонку `email` в таблицу `users`
- Таблицу `mini_app_sessions` для JWT

### Шаг 2: Настройка переменных окружения
```bash
# Добавьте в .env:
MINI_APP_URL=https://your-domain.up.railway.app
JWT_SECRET_KEY=your_generated_secret_key
```

### Шаг 3: Деплой на Railway (рекомендуется)
1. Подключите GitHub репозиторий к Railway
2. Railway автоматически найдет `railway.json` и `Procfile`
3. Установите переменные окружения в Dashboard
4. Получите домен вида `https://falt-bot.up.railway.app`
5. Обновите `MINI_APP_URL` этим значением

### Шаг 4: Настройка BotFather
```
/mybots → Ваш бот → Bot Settings → Menu Button → Web App
Название: 🧺 FALT App
URL: https://your-domain.up.railway.app
```

### Шаг 5: Тестирование
1. Отправьте `/start` - бот должен работать как раньше
2. Отправьте `/setemail` и укажите email
3. Отправьте `/miniapp` - должна появиться кнопка WebApp
4. Нажмите кнопку - Mini App должен открыться

## 🧪 Тестирование

### Тест 1: Обратная совместимость
```
/start → Главное меню (как раньше)
/registration → Регистрация (как раньше)
/wallet → Кошелек (как раньше)
```

### Тест 2: Mini App
```
/setemail → Ввод email → ✅ Email привязан
/miniapp → Кнопка "Открыть Mini App" → WebApp открывается
В Mini App:
  - Вход по email
  - Просмотр баланса
  - Выбор машинки
  - Бронирование
  - Списание средств
```

### Тест 3: Безопасность
- Попытка входа с неверным email → Ошибка
- Попытка бронирования без токена → 401 Unauthorized
- Истекший токен → Перенаправление на логин

## 📁 Структура файлов

```
FALT_BOT_INTEGRATED/
├── bot.py                    # Точка входа (только бот)
├── start_all.py             # Единый запуск (бот + Mini App)
├── config.py                # Объединенная конфигурация
├── migrate.py               # Миграция БД
├── requirements.txt         # Все зависимости
├── Dockerfile               # Контейнер
├── docker-compose.yml       # Локальный запуск
├── railway.json             # Конфиг Railway
├── Procfile                 # Команда запуска
├── .env.example             # Шаблон переменных
├── .gitignore
├── README.md
├── logs/                    # Логи
├── data/                    # Данные расписания
├── database/
│   ├── __init__.py
│   └── db.py               # Обновленная БД (+Mini App)
├── handlers/
│   ├── __init__.py
│   ├── main_menu_handler.py
│   ├── registration_handler.py
│   ├── admin_interaction_handler.py
│   ├── admin_manage_laundry.py
│   ├── laundry_handler.py
│   ├── study_room_handler.py
│   ├── wallet_handler.py
│   ├── email_handler.py      # НОВЫЙ
│   └── mini_app_handler.py   # НОВЫЙ
├── keyboards/
│   └── __init__.py
├── services/
│   ├── __init__.py
│   ├── laundry/
│   ├── wallet/
│   └── payments/
└── mini_app/                 # НОВАЯ ДИРЕКТОРИЯ
    ├── __init__.py
    ├── web_server.py        # FastAPI сервер
    ├── schedule.json        # Заглушка расписания
    ├── api/
    │   └── __init__.py
    ├── static/
    │   ├── css/
    │   └── js/
    └── templates/
        └── index.html       # Интерфейс Mini App
```

## ⚠️ Важные замечания

### Безопасность
1. **JWT_SECRET_KEY** должен быть минимум 32 символа
2. **MINI_APP_URL** должен использовать HTTPS
3. Токены хранятся в `localStorage` (автоматическая очистка при logout)
4. Сессии валидируются на сервере каждый запрос

### Ограничения
- Mini App работает только у зарегистрированных пользователей
- Требуется привязка email через `/setemail`
- Бронирование требует достаточного баланса

### Откат изменений
Если нужно отключить Mini App:
1. Удалить `mini_app/` директорию
2. Удалить импорты `email_router` и `mini_app_router` из `bot.py`
3. Удалить команды из `set_commands()`
4. Оставить `database/db.py` - он обратно совместим

## 🔍 Отладка

### Логи Railway
```bash
railway logs
```

### Локальный запуск с отладкой
```bash
DEBUG=True python start_all.py
```

### Проверка БД
```bash
sqlite3 database/falt.db ".schema users"
sqlite3 database/falt.db ".schema mini_app_sessions"
```

## 📞 Поддержка

При возникновении проблем:
1. Проверьте логи в `logs/logs.txt`
2. Убедитесь, что все переменные окружения установлены
3. Проверьте, что миграция БД выполнена
4. Проверьте доступность URL Mini App извне
