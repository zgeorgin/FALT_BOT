CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL UNIQUE,
    name TEXT,
    status TEXT DEFAULT "pending",
    wallet REAL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS laundry (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    start_time TEXT,
    end_time TEXT,
    FOREIGN KEY(user_id) REFERENCES users(user_id)
);
