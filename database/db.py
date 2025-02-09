import sqlite3
import os

DATABASE_PATH = os.environ.get("DB_PATH")

def get_connection():
    return sqlite3.connect(DATABASE_PATH)

def init_db():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.executescript(open("database/init_db.sql", "r").read())
    conn.commit()
    conn.close()

def add_user(user_id, name):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO users (user_id, name, status, wallet) VALUES (?, ?, ?, ?)",
                   (user_id, name, "pending", 0))
    conn.commit()
    conn.close()

def is_registered(user_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT 1 FROM users WHERE user_id == ? LIMIT 1", (user_id, ))
    all_matches = cursor.fetchone()
    conn.close()
    return all_matches is not None