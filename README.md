# FALT_BOT
## Установка и запуск
1. Клонировать репозиторий
```bash
git clone https://github.com/zgeorgin/FALT_BOT.git
cd FALT_BOT
```
2. Установить библиотеки
```bash
pip install -r requirements.txt
```
3. Создать .env файл и указать в нём настройки
```bash
TOKEN=YOUR_TOKEN
ADMIN_CHAT_ID=YOUR_ADMIN_CHAT_ID
DB_PATH=YOUR_DB_PATH
LAUNDRY_DATA_PATH=YOUR_LAUNDRY_DATA_PATH
```
4. Запустить бота:
```bash
nohup python bot.py &
```