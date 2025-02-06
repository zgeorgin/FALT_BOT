import sqlite3
import os

DATABASE_PATH = os.environ.get("DB_PATH")

def get_connection():
    return sqlite3.connect(DATABASE_PATH)

def create_tables():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(open("database/init_db.sql", "r").read())
    conn.commit()
    conn.close()

def add_user(user_id, name):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO users (user_id, name, status, wallet) VALUES (?, ?, ?, ?)",
                   (user_id, name, "pending", 0))
    conn.commit()
    conn.close()