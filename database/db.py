import sqlite3
from dataclasses import dataclass
from typing import Optional
from config import DB_PATH


@dataclass
class User:
    user_id: int
    name: str
    surname: str
    wallet: float = 0.0
    email: Optional[str] = None


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_connection()
    cur = conn.cursor()

    cur.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            user_id   INTEGER PRIMARY KEY,
            name      TEXT NOT NULL,
            surname   TEXT NOT NULL,
            wallet    REAL DEFAULT 0,
            email     TEXT UNIQUE
        );

        CREATE TABLE IF NOT EXISTS registration_clicks (
            user_id INTEGER PRIMARY KEY
        );

        CREATE TABLE IF NOT EXISTS washing_machines (
            name       TEXT PRIMARY KEY,
            is_working INTEGER DEFAULT 1
        );

        CREATE TABLE IF NOT EXISTS wallet_transactions (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id    INTEGER NOT NULL,
            amount     REAL NOT NULL,
            direction  TEXT NOT NULL,
            reason     TEXT,
            reference  TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(user_id) REFERENCES users(user_id)
        );

        CREATE TABLE IF NOT EXISTS payments (
            payment_id  TEXT PRIMARY KEY,
            user_id     INTEGER NOT NULL,
            service     TEXT NOT NULL,
            amount      REAL NOT NULL,
            currency    TEXT DEFAULT 'RUB',
            description TEXT,
            payload     TEXT,
            status      TEXT DEFAULT 'pending',
            created_at  TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at  TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(user_id) REFERENCES users(user_id)
        );

        CREATE TABLE IF NOT EXISTS mini_app_sessions (
            session_id    TEXT PRIMARY KEY,
            user_id       INTEGER NOT NULL,
            auth_token    TEXT UNIQUE,
            created_at    TEXT DEFAULT CURRENT_TIMESTAMP,
            expires_at    TEXT NOT NULL,
            last_activity TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(user_id) REFERENCES users(user_id)
        );
    """)

    # Машинки по умолчанию
    machines = [
        ("#1 Стиральная", 1),
        ("#2 Стиральная", 1),
        ("#3 Стиральная", 1),
        ("#4 Стиральная", 1),
        ("#5 Стиральная", 1),
        ("#6 Сушилка", 1),
    ]
    cur.executemany(
        "INSERT OR IGNORE INTO washing_machines (name, is_working) VALUES (?, ?)",
        machines,
    )

    conn.commit()
    conn.close()


# ── Users ──────────────────────────────────────────────────────────────────

def is_registered(user_id: int) -> Optional[User]:
    conn = get_connection()
    row = conn.execute(
        "SELECT user_id, name, surname, wallet, email FROM users WHERE user_id = ?",
        (user_id,),
    ).fetchone()
    conn.close()
    if row:
        return User(row["user_id"], row["name"], row["surname"], row["wallet"] or 0, row["email"])
    return None


def add_user(user: User):
    conn = get_connection()
    conn.execute(
        "INSERT OR REPLACE INTO users (user_id, name, surname, wallet) VALUES (?, ?, ?, 0)",
        (user.user_id, user.name, user.surname),
    )
    conn.commit()
    conn.close()


def get_user_by_email(email: str) -> Optional[User]:
    conn = get_connection()
    row = conn.execute(
        "SELECT user_id, name, surname, wallet, email FROM users WHERE email = ?",
        (email,),
    ).fetchone()
    conn.close()
    if row:
        return User(row["user_id"], row["name"], row["surname"], row["wallet"] or 0, row["email"])
    return None


def update_user_email(user_id: int, email: str) -> bool:
    try:
        conn = get_connection()
        conn.execute("UPDATE users SET email = ? WHERE user_id = ?", (email, user_id))
        conn.commit()
        conn.close()
        return True
    except Exception:
        return False


# ── Registration clicks ────────────────────────────────────────────────────

def registration_clicked(user_id: int) -> bool:
    conn = get_connection()
    row = conn.execute(
        "SELECT 1 FROM registration_clicks WHERE user_id = ?", (user_id,)
    ).fetchone()
    conn.close()
    return row is not None


def add_registration_click(user_id: int):
    conn = get_connection()
    conn.execute(
        "INSERT OR IGNORE INTO registration_clicks (user_id) VALUES (?)", (user_id,)
    )
    conn.commit()
    conn.close()


def set_registration_click_status(user_id: int):
    conn = get_connection()
    conn.execute("DELETE FROM registration_clicks WHERE user_id = ?", (user_id,))
    conn.commit()
    conn.close()


# ── Machines ───────────────────────────────────────────────────────────────

def get_machine_names() -> list[str]:
    conn = get_connection()
    rows = conn.execute("SELECT name FROM washing_machines ORDER BY name").fetchall()
    conn.close()
    return [r["name"] for r in rows]


def get_machine_status(machine_name: str) -> bool:
    conn = get_connection()
    row = conn.execute(
        "SELECT is_working FROM washing_machines WHERE name = ?", (machine_name,)
    ).fetchone()
    conn.close()
    return bool(row["is_working"]) if row else False


def change_machine_status(machine_name: str):
    conn = get_connection()
    conn.execute(
        "UPDATE washing_machines SET is_working = NOT is_working WHERE name = ?",
        (machine_name,),
    )
    conn.commit()
    conn.close()


# ── Wallet ─────────────────────────────────────────────────────────────────

def get_wallet_balance(user_id: int) -> int:
    conn = get_connection()
    row = conn.execute(
        "SELECT wallet FROM users WHERE user_id = ?", (user_id,)
    ).fetchone()
    conn.close()
    return int(round(float(row["wallet"] or 0))) if row else 0


def debit_wallet(user_id: int, amount: int, reason: str, reference: str = None) -> bool:
    conn = get_connection()
    row = conn.execute("SELECT wallet FROM users WHERE user_id = ?", (user_id,)).fetchone()
    if not row or float(row["wallet"] or 0) < amount:
        conn.close()
        return False
    new_bal = float(row["wallet"]) - amount
    conn.execute("UPDATE users SET wallet = ? WHERE user_id = ?", (new_bal, user_id))
    conn.execute(
        "INSERT INTO wallet_transactions (user_id, amount, direction, reason, reference) VALUES (?,?,?,?,?)",
        (user_id, amount, "debit", reason, reference),
    )
    conn.commit()
    conn.close()
    return True


def credit_wallet(user_id: int, amount: int, reason: str, reference: str = None) -> int:
    conn = get_connection()
    row = conn.execute("SELECT wallet FROM users WHERE user_id = ?", (user_id,)).fetchone()
    current = float(row["wallet"] or 0) if row else 0
    new_bal = current + amount
    conn.execute("UPDATE users SET wallet = ? WHERE user_id = ?", (new_bal, user_id))
    conn.execute(
        "INSERT INTO wallet_transactions (user_id, amount, direction, reason, reference) VALUES (?,?,?,?,?)",
        (user_id, amount, "credit", reason, reference),
    )
    conn.commit()
    conn.close()
    return int(round(new_bal))


# ── Payments ───────────────────────────────────────────────────────────────

def create_payment_record(payment_id, user_id, service, amount, currency, description, payload, status):
    conn = get_connection()
    conn.execute(
        """INSERT OR REPLACE INTO payments
           (payment_id, user_id, service, amount, currency, description, payload, status)
           VALUES (?,?,?,?,?,?,?,?)""",
        (payment_id, user_id, service, amount, currency, description, payload, status),
    )
    conn.commit()
    conn.close()


def get_payment_record(payment_id: str) -> Optional[dict]:
    conn = get_connection()
    row = conn.execute(
        "SELECT * FROM payments WHERE payment_id = ?", (payment_id,)
    ).fetchone()
    conn.close()
    return dict(row) if row else None


def update_payment_status(payment_id: str, status: str):
    conn = get_connection()
    conn.execute(
        "UPDATE payments SET status = ?, updated_at = CURRENT_TIMESTAMP WHERE payment_id = ?",
        (status, payment_id),
    )
    conn.commit()
    conn.close()


# ── Mini App sessions ──────────────────────────────────────────────────────

def create_mini_app_session(user_id: int, device_info: str = "") -> str:
    import secrets
    from datetime import datetime, timedelta
    from config import JWT_EXPIRATION_DAYS

    token = secrets.token_urlsafe(32)
    expires = (datetime.utcnow() + timedelta(days=JWT_EXPIRATION_DAYS)).isoformat()
    conn = get_connection()
    conn.execute(
        """INSERT INTO mini_app_sessions (session_id, user_id, auth_token, expires_at)
           VALUES (?, ?, ?, ?)""",
        (secrets.token_hex(16), user_id, token, expires),
    )
    conn.commit()
    conn.close()
    return token


def validate_session(token: str) -> Optional[int]:
    from datetime import datetime

    conn = get_connection()
    row = conn.execute(
        """SELECT user_id, expires_at FROM mini_app_sessions
           WHERE auth_token = ? AND expires_at > datetime('now')""",
        (token,),
    ).fetchone()
    if row:
        conn.execute(
            "UPDATE mini_app_sessions SET last_activity = CURRENT_TIMESTAMP WHERE auth_token = ?",
            (token,),
        )
        conn.commit()
    conn.close()
    return row["user_id"] if row else None

def admin_add_money(user_id: int, amount: int) -> bool:
    """Добавить деньги пользователю (для админа)"""
    try:
        conn = get_connection()
        row = conn.execute("SELECT wallet FROM users WHERE user_id = ?", (user_id,)).fetchone()
        if not row:
            conn.close()
            return False
        
        new_bal = float(row["wallet"] or 0) + amount
        conn.execute("UPDATE users SET wallet = ? WHERE user_id = ?", (new_bal, user_id))
        conn.execute(
            "INSERT INTO wallet_transactions (user_id, amount, direction, reason) VALUES (?,?,?,?)",
            (user_id, amount, "credit", "admin_add"),
        )
        conn.commit()
        conn.close()
        return True
    except Exception:
        return False
