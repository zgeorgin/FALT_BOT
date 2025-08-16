import sqlite3
from config import DB_PATH as DATABASE_PATH

class User():
    def __init__(self, user_id, name, surname, wallet = 0, label = 0):
        self.name = name
        self.surname = surname
        self.user_id = user_id
        self.wallet = wallet
        self.label = label

def get_connection():
    return sqlite3.connect(DATABASE_PATH)

def init_db():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.executescript(open("database/init_db.sql", "r").read())
    conn.commit()
    conn.close()

def add_user(user : User):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO users (user_id, name, surname, wallet, label) VALUES (?, ?, ?, ?, ?)",
                   (user.user_id, user.name, user.surname, user.wallet, user.label, ))
    conn.commit()
    conn.close()

def is_registered(user_id) -> User | None:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE user_id == ? LIMIT 1", (user_id, ))
    user = cursor.fetchone()
    conn.close()
    if user is not None:
        return User(user_id = user[1], name = user[2], surname = user[3], wallet=user[4], label=user[5])
    return None