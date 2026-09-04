import sqlite3
from config import DB_PATH as DATABASE_PATH

class User():
    def __init__(self, user_id, name, surname, wallet = 0, label = 0):
        self.name = name
        self.surname = surname
        self.user_id = user_id
        self.wallet = wallet
        self.label = label


class RefundRequest():
    def __init__(
        self,
        request_id,
        user_id,
        problem_text,
        requested_amount,
        approved_amount,
        status,
        admin_comment,
        admin_id,
        created_at,
        updated_at,
        resolved_at,
    ):
        self.request_id = request_id
        self.user_id = user_id
        self.problem_text = problem_text
        self.requested_amount = requested_amount
        self.approved_amount = approved_amount
        self.status = status
        self.admin_comment = admin_comment
        self.admin_id = admin_id
        self.created_at = created_at
        self.updated_at = updated_at
        self.resolved_at = resolved_at


def get_connection():
    return sqlite3.connect(DATABASE_PATH)

def init_db():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.executescript(open("database/init_db.sql", "r", encoding="utf8").read())
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


def _refund_request_from_row(row) -> RefundRequest | None:
    if row is None:
        return None
    return RefundRequest(
        request_id=row[0],
        user_id=row[1],
        problem_text=row[2],
        requested_amount=row[3],
        approved_amount=row[4],
        status=row[5],
        admin_comment=row[6],
        admin_id=row[7],
        created_at=row[8],
        updated_at=row[9],
        resolved_at=row[10],
    )


def create_refund_request(user_id: int, problem_text: str, requested_amount: int) -> int:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO refund_requests (user_id, problem_text, requested_amount, status)
        VALUES (?, ?, ?, 'new')
        """,
        (int(user_id), str(problem_text), int(requested_amount)),
    )
    request_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return request_id


def get_refund_request(request_id: int) -> RefundRequest | None:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM refund_requests WHERE id = ? LIMIT 1", (int(request_id),))
    row = cursor.fetchone()
    conn.close()
    return _refund_request_from_row(row)


def resolve_refund_request(
    request_id: int,
    status: str,
    admin_id: int,
    approved_amount: int | None = None,
    admin_comment: str | None = None,
) -> bool:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        UPDATE refund_requests
        SET
            status = ?,
            approved_amount = ?,
            admin_comment = ?,
            admin_id = ?,
            updated_at = CURRENT_TIMESTAMP,
            resolved_at = CURRENT_TIMESTAMP
        WHERE id = ? AND status = 'new'
        """,
        (status, approved_amount, admin_comment, int(admin_id), int(request_id)),
    )
    is_updated = cursor.rowcount > 0
    conn.commit()
    conn.close()
    return is_updated


def add_refund_log(
    request_id: int,
    action: str,
    actor_id: int | None = None,
    comment: str | None = None,
    amount: int | None = None,
):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO refund_logs (request_id, action, actor_id, comment, amount)
        VALUES (?, ?, ?, ?, ?)
        """,
        (int(request_id), action, actor_id, comment, amount),
    )
    conn.commit()
    conn.close()


def get_machine_names() -> list[str]:
    con = get_connection()
    cur = con.cursor()
    machine_names = cur.execute("SELECT name FROM washing_machines ORDER BY name ASC").fetchall()
    con.close()
    return [i[0] for i in machine_names]


def get_machine_status(machine_name: str) -> bool:
    con = get_connection()
    cur = con.cursor()
    machine_status = cur.execute("SELECT is_working FROM washing_machines WHERE name = ?", (machine_name, )).fetchone()
    con.close()
    return machine_status[0]


def change_machine_status(machine_name: str) -> None:
    con = get_connection()
    cur = con.cursor()
    cur.execute("UPDATE washing_machines SET is_working = not is_working WHERE name = ?", (machine_name, ))
    con.commit()
    con.close()


def get_wallet_balance(user_id: int) -> int:
    con = get_connection()
    cur = con.cursor()
    row = cur.execute("SELECT wallet FROM users WHERE user_id = ?", (user_id,)).fetchone()
    con.close()
    if row is None or row[0] is None:
        return 0
    return int(round(float(row[0])))


def _add_wallet_transaction(user_id: int, amount: int, direction: str, reason: str, reference: str | None) -> None:
    con = get_connection()
    cur = con.cursor()
    cur.execute(
        """
        INSERT INTO wallet_transactions (user_id, amount, direction, reason, reference)
        VALUES (?, ?, ?, ?, ?)
        """,
        (user_id, amount, direction, reason, reference),
    )
    con.commit()
    con.close()


def credit_wallet(user_id: int, amount: int, reason: str, reference: str | None = None) -> int:
    con = get_connection()
    cur = con.cursor()
    cur.execute("SELECT wallet FROM users WHERE user_id = ?", (user_id,))
    row = cur.fetchone()
    if row is None:
        con.close()
        return 0
    current = int(round(float(row[0] or 0)))
    new_balance = current + int(amount)
    cur.execute("UPDATE users SET wallet = ? WHERE user_id = ?", (new_balance, user_id))
    con.commit()
    con.close()
    _add_wallet_transaction(user_id, int(amount), "credit", reason, reference)
    return new_balance


def debit_wallet(user_id: int, amount: int, reason: str, reference: str | None = None) -> bool:
    con = get_connection()
    cur = con.cursor()
    cur.execute("SELECT wallet FROM users WHERE user_id = ?", (user_id,))
    row = cur.fetchone()
    if row is None:
        con.close()
        return False
    current = int(round(float(row[0] or 0)))
    amount = int(amount)
    if current < amount:
        con.close()
        return False
    new_balance = current - amount
    cur.execute("UPDATE users SET wallet = ? WHERE user_id = ?", (new_balance, user_id))
    con.commit()
    con.close()
    _add_wallet_transaction(user_id, amount, "debit", reason, reference)
    return True


def create_payment_record(
    payment_id: str,
    user_id: int,
    service: str,
    amount: float,
    currency: str,
    description: str,
    payload: str,
    status: str,
) -> None:
    con = get_connection()
    cur = con.cursor()
    cur.execute(
        """
        INSERT INTO payments (payment_id, user_id, service, amount, currency, description, payload, status)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (payment_id, user_id, service, amount, currency, description, payload, status),
    )
    con.commit()
    con.close()


def get_payment_record(payment_id: str):
    con = get_connection()
    cur = con.cursor()
    row = cur.execute(
        """
        SELECT payment_id, user_id, service, amount, currency, description, payload, status
        FROM payments
        WHERE payment_id = ?
        """,
        (payment_id,),
    ).fetchone()
    con.close()
    if row is None:
        return None
    return {
        "payment_id": row[0],
        "user_id": row[1],
        "service": row[2],
        "amount": row[3],
        "currency": row[4],
        "description": row[5],
        "payload": row[6],
        "status": row[7],
    }


def update_payment_status(payment_id: str, status: str) -> None:
    con = get_connection()
    cur = con.cursor()
    cur.execute("UPDATE payments SET status = ? WHERE payment_id = ?", (status, payment_id))
    con.commit()
    con.close()
def add_registration_click(user_id: int):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO registration (user_id, is_registered) VALUES (?, ?)",
                   (user_id, True, ))
    conn.commit()
    conn.close()


def registration_clicked(user_id: int) -> bool:
    conn = get_connection()
    cursor = conn.cursor()
    user = cursor.execute("SELECT * FROM registration WHERE user_id == ?", (user_id,)).fetchone()
    if not user or not user[1]:
        return False
    return True


def set_registration_click_status(user_id: int):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE registration SET is_registered = NOT(SELECT is_registered FROM registration WHERE user_id == ?) WHERE user_id == ?", (user_id, user_id))
    conn.commit()
    conn.close()
