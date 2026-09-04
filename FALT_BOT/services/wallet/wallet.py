import json
from dataclasses import dataclass
from uuid import uuid4

from config import YOOKASSA_RETURN_URL
from database.db import (
    create_payment_record,
    credit_wallet,
    debit_wallet,
    get_payment_record,
    get_wallet_balance,
    update_payment_status,
)
from services.payments.client import PaymentConfigError, PaymentProviderError, get_payment_provider


@dataclass(frozen=True)
class TopUpResult:
    payment_id: str
    confirmation_url: str
    status: str


@dataclass(frozen=True)
class CheckResult:
    status: str
    balance: int | None


def get_balance(user_id: int) -> int:
    return get_wallet_balance(user_id)


def debit_balance(user_id: int, amount_rub: int, reason: str, reference: str | None = None) -> bool:
    return debit_wallet(user_id, int(amount_rub), reason, reference)


def credit_balance(user_id: int, amount_rub: int, reason: str, reference: str | None = None) -> int:
    return credit_wallet(user_id, int(amount_rub), reason, reference)


async def create_topup(user_id: int, amount_rub: int) -> TopUpResult:
    provider = get_payment_provider()
    description = f"Пополнение кошелька на {amount_rub} ₽"
    payment = await provider.create_payment(
        amount_rub=f"{amount_rub:.2f}",
        description=description,
        return_url=YOOKASSA_RETURN_URL,
        metadata={"service": "wallet_topup", "user_id": str(user_id), "amount": str(amount_rub)},
        idempotence_key=uuid4().hex,
    )
    payload = json.dumps({"amount": amount_rub}, ensure_ascii=False)
    create_payment_record(
        payment.payment_id,
        user_id,
        "wallet_topup",
        amount_rub,
        "RUB",
        description,
        payload,
        payment.status,
    )
    return TopUpResult(payment.payment_id, payment.confirmation_url, payment.status)


async def check_topup(payment_id: str, expected_user_id: int | None = None) -> CheckResult:
    record = get_payment_record(payment_id)
    if record is None:
        return CheckResult("not_found", None)
    if expected_user_id is not None and str(record["user_id"]) != str(expected_user_id):
        return CheckResult("not_owner", None)
    if record["service"] != "wallet_topup":
        return CheckResult("unsupported", None)

    try:
        provider = get_payment_provider()
        info = await provider.get_payment(payment_id)
    except (PaymentConfigError, PaymentProviderError):
        return CheckResult("error", None)

    if info.status == "succeeded":
        if record["status"] != "succeeded":
            update_payment_status(payment_id, "succeeded")
            balance = credit_wallet(record["user_id"], int(round(float(record["amount"]))), "topup", payment_id)
            return CheckResult("succeeded", balance)
        balance = get_wallet_balance(record["user_id"])
        return CheckResult("already_succeeded", balance)

    if info.status == "canceled":
        update_payment_status(payment_id, "canceled")
        return CheckResult("canceled", None)

    update_payment_status(payment_id, info.status)
    return CheckResult("pending", None)
