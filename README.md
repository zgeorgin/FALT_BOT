# FALT Bot + Mini App (Интегрированная версия)

Telegram-бот + Mini App для бронирования стиральных машин и учебных комнат в общежитии ФАЛТ МФТИ.

## 🚀 Быстрый старт

### 1. Миграция базы данных
```bash
python migrate.py
```
Это добавит:
- Колонку `email` в таблицу `users`
- Таблицу `mini_app_sessions` для JWT токенов

### 2. Настройка окружения
```bash
cp .env.example .env
# Отредактируйте .env, добавьте MINI_APP_URL и JWT_SECRET_KEY
```

### 3. Запуск
```bash
# Только бот (обратная совместимость)
python bot.py

# Бот + Mini App (для Railway/Docker)
python start_all.py
```

## 📋 Переменные окружения

### Обязательные (из существующего FALT_BOT)
| Переменная | Описание |
|------------|----------|
| `TOKEN` | Токен Telegram бота от BotFather |
| `ADMIN_CHAT_ID` | Chat ID администратора |

### Новые для Mini App (ОБЯЗАТЕЛЬНЫ)
| Переменная | Описание | Пример |
|------------|----------|--------|
| `MINI_APP_URL` | HTTPS URL деплоя | `https://falt-bot.up.railway.app` |
| `JWT_SECRET_KEY` | Секрет для JWT (мин. 32 символа) | `a1b2c3d4e5f6...` |

### Генерация JWT_SECRET_KEY
```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

### Опциональные
| Переменная | Default | Описание |
|------------|---------|----------|
| `WEBAPP_HOST` | `0.0.0.0` | Хост для FastAPI |
| `WEBAPP_PORT` | `8000` | Порт для FastAPI |
| `JWT_EXPIRATION_DAYS` | `7` | Срок жизни сессии |
| `CORS_ORIGINS` | `*` | Разрешенные домены |
| `DB_PATH` | `database/falt.db` | Путь к БД |
| `LAUNDRY_DATA_PATH` | `data/schedule.json` | Путь к расписанию |

## 🐳 Деплой на Railway (рекомендуется)

1. Подключите GitHub репозиторий к Railway
2. Railway автоматически найдет `railway.json` и `Procfile`
3. Установите переменные окружения в Dashboard:
   - `TOKEN`
   - `ADMIN_CHAT_ID`
   - `MINI_APP_URL` (после получения домена)
   - `JWT_SECRET_KEY`
4. Получите домен вида `https://falt-bot.up.railway.app`
5. Обновите `MINI_APP_URL` этим значением

## 🤖 Настройка BotFather

После деплоя:

```
/mybots → Ваш бот → Bot Settings → Menu Button → Web App
Название: 🧺 FALT App
URL: https://your-domain.up.railway.app
```

## 📱 Команды бота

| Команда | Описание |
|---------|----------|
| `/start` | Главное меню |
| `/miniapp` | Открыть Mini App (требуется email) |
| `/setemail` | Привязать email для Mini App |
| `/wallet` | Кошелёк |
| `/bookings` | Мои записи |

## 🏗️ Структура проекта

```
FALT_BOT/
├── bot.py                 # Только бот (обратная совместимость)
├── start_all.py          # Бот + Mini App (Railway/Docker)
├── config.py             # Объединенная конфигурация
├── migrate.py            # Миграция БД
├── requirements.txt      # Все зависимости
├── Dockerfile            # Контейнер
├── docker-compose.yml    # Локальный запуск
├── railway.json          # Конфиг Railway
├── Procfile              # Команда запуска
├── .env.example          # Шаблон переменных
├── database/
│   └── db.py            # Обновленная БД (+Mini App)
├── handlers/
│   ├── main_menu_handler.py
│   ├── registration_handler.py
│   ├── laundry_handler.py
│   ├── wallet_handler.py
│   ├── email_handler.py      # 🆕 Привязка email
│   └── mini_app_handler.py   # 🆕 Команды Mini App
└── mini_app/               # 🆕 НОВАЯ ДИРЕКТОРИЯ
    ├── web_server.py       # FastAPI сервер
    └── templates/
        └── index.html      # Web интерфейс
```

## 🧪 Тестирование

### Тест 1: Обратная совместимость
```
/start → Главное меню (как раньше)
/registration → Регистрация (как раньше)
/wallet → Кошелёк (как раньше)
```

### Тест 2: Mini App flow
```
/setemail → Ввод email → ✅ Email привязан
/miniapp → Кнопка "Открыть Mini App"
Нажать кнопку → Mini App открывается
```

### Тест 3: Бронирование в Mini App
```
1. Войти по email
2. Выбрать машинку
3. Выбрать дату и время
4. Нажать "Забронировать"
5. Проверить списание средств
```

## 🔒 Безопасность

- JWT токены для сессий Mini App
- Валидация email на сервере
- Проверка авторизации на каждом API запросе
- CORS защита
- Проверка баланса перед бронированием

## ⚠️ Важные замечания

1. **MINI_APP_URL должен быть HTTPS** - требование Telegram
2. **JWT_SECRET_KEY минимум 32 символа**
3. **Пользователь должен быть зарегистрирован** в боте перед использованием Mini App
4. **Требуется привязка email** через `/setemail`

## 🐛 Отладка

### Проблема: Mini App не открывается
- Проверьте `MINI_APP_URL` в .env
- Убедитесь, что URL использует HTTPS
- Проверьте логи: `logs/logs.txt`

### Проблема: "Пользователь не найден"
- Нужно сначала зарегистрироваться в боте через `/start`
- Затем привязать email через `/setemail`

### Проблема: Ошибка авторизации
- Проверьте `JWT_SECRET_KEY`
- Убедитесь, что email совпадает с тем, что в БД

## 📚 Дополнительная документация

- `INTEGRATION_GUIDE.md` - Подробная инструкция по интеграции
- `FINAL_REPORT.txt` - Полный отчет о проделанной работе

## 🔄 Обновление существующего бота

Если у вас уже есть работающий FALT_BOT:

1. Сделайте бэкап БД: `cp database/falt.db database/falt.db.backup`
2. Скопируйте новые файлы из архива
3. Запустите миграцию: `python migrate.py`
4. Добавьте новые переменные в `.env`
5. Перезапустите бота

## 📝 Лицензия

Проект создан для общежития ФАЛТ МФТИ.
