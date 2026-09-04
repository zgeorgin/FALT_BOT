from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional

import aiohttp

from config import YOOKASSA_SHOP_ID, YOOKASSA_SECRET_KEY


API_BASE_URL = "https://api.yookassa.ru/v3"


class PaymentConfigError(RuntimeError):
    pass


class PaymentProviderError(RuntimeError):
    pass


@dataclass(frozen=True)
class PaymentCreateResult:
    payment_id: str
    confirmation_url: str
    status: str


@dataclass(frozen=True)
class PaymentInfo:
    payment_id: str
    status: str


class YooKassaProvider:
    def __init__(self, shop_id: str, secret_key: str) -> None:
        self._auth = aiohttp.BasicAuth(shop_id, secret_key)

    async def create_payment(
        self,
        *,
        amount_rub: str,
        description: str,
        return_url: str,
        metadata: Dict[str, Any],
        idempotence_key: str,
    ) -> PaymentCreateResult:
        payload = {
            "amount": {"value": amount_rub, "currency": "RUB"},
            "capture": True,
            "confirmation": {"type": "redirect", "return_url": return_url},
            "description": description,
            "metadata": metadata,
        }
        headers = {"Idempotence-Key": idempotence_key}

        try:
            async with aiohttp.ClientSession(auth=self._auth) as session:
                async with session.post(
                    f"{API_BASE_URL}/payments", json=payload, headers=headers
                ) as resp:
                    data = await resp.json()
                    if resp.status not in (200, 201):
                        raise PaymentProviderError(f"YooKassa error {resp.status}: {data}")
        except aiohttp.ClientError as exc:
            raise PaymentProviderError(f"YooKassa request failed: {exc}") from exc

        confirmation = data.get("confirmation") or {}
        confirmation_url = confirmation.get("confirmation_url")
        if not confirmation_url:
            raise PaymentProviderError("YooKassa confirmation_url is missing")

        return PaymentCreateResult(
            payment_id=data["id"],
            confirmation_url=confirmation_url,
            status=data.get("status", "unknown"),
        )

    async def get_payment(self, payment_id: str) -> PaymentInfo:
        try:
            async with aiohttp.ClientSession(auth=self._auth) as session:
                async with session.get(f"{API_BASE_URL}/payments/{payment_id}") as resp:
                    data = await resp.json()
                    if resp.status != 200:
                        raise PaymentProviderError(f"YooKassa error {resp.status}: {data}")
        except aiohttp.ClientError as exc:
            raise PaymentProviderError(f"YooKassa request failed: {exc}") from exc

        return PaymentInfo(payment_id=data["id"], status=data.get("status", "unknown"))


_provider: Optional[YooKassaProvider] = None


def get_payment_provider() -> YooKassaProvider:
    global _provider
    if _provider is not None:
        return _provider

    if not YOOKASSA_SHOP_ID or not YOOKASSA_SECRET_KEY:
        raise PaymentConfigError("Missing YooKassa credentials")
    _provider = YooKassaProvider(YOOKASSA_SHOP_ID, YOOKASSA_SECRET_KEY)
    return _provider
