# app/services/yoomoney_service.py
"""YooMoney OAuth2 payment integration.

Flow:
1. Admin enters client_id + client_secret in UI
2. Admin clicks "Authorize" → redirected to YooMoney consent page
3. YooMoney redirects back with auth code → exchange for access_token
4. Bot generates quickpay payment links for users
5. YooMoney sends HTTP notification to webhook after payment
"""

import hashlib
import logging
from typing import Optional
from urllib.parse import urlencode

import httpx


logger = logging.getLogger(__name__)

YOOMONEY_AUTH_URL = "https://yoomoney.ru/oauth/authorize"
YOOMONEY_TOKEN_URL = "https://yoomoney.ru/oauth/token"
YOOMONEY_API_URL = "https://yoomoney.ru/api"
YOOMONEY_QUICKPAY_URL = "https://yoomoney.ru/quickpay/confirm.xml"

# Permissions needed for payment acceptance
DEFAULT_SCOPE = "account-info operation-history payment-p2p"


def build_auth_url(
    client_id: str,
    redirect_uri: str,
    scope: str = DEFAULT_SCOPE,
    instance_name: Optional[str] = None,
) -> str:
    """Build YooMoney OAuth2 authorization URL."""
    params = {
        "client_id": client_id,
        "response_type": "code",
        "redirect_uri": redirect_uri,
        "scope": scope,
    }
    if instance_name:
        params["instance_name"] = instance_name
    return f"{YOOMONEY_AUTH_URL}?{urlencode(params)}"


async def exchange_code_for_token(
    code: str,
    client_id: str,
    redirect_uri: str,
    client_secret: Optional[str] = None,
) -> dict:
    """Exchange authorization code for access token.

    Returns dict with 'access_token' on success, or 'error' on failure.
    """
    data = {
        "code": code,
        "client_id": client_id,
        "grant_type": "authorization_code",
        "redirect_uri": redirect_uri,
    }
    if client_secret:
        data["client_secret"] = client_secret

    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.post(
            YOOMONEY_TOKEN_URL,
            data=data,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        result = resp.json()
        if "access_token" in result:
            logger.info("YooMoney access token obtained successfully")
        else:
            logger.error(f"YooMoney token exchange failed: {result}")
        return result


async def get_account_info(access_token: str) -> Optional[dict]:
    """Get YooMoney wallet account info (wallet_id, balance, etc.)."""
    async with httpx.AsyncClient(timeout=15.0) as client:
        resp = await client.post(
            f"{YOOMONEY_API_URL}/account-info",
            headers={"Authorization": f"Bearer {access_token}"},
        )
        if resp.status_code == 200:
            return resp.json()
        logger.error(f"YooMoney account-info failed: {resp.status_code} {resp.text}")
        return None


def build_quickpay_url(
    wallet_id: str,
    amount: float,
    label: str,
    target: str = "Оплата услуги AI Secretary",
    success_url: Optional[str] = None,
) -> str:
    """Build YooMoney quickpay payment URL.

    Args:
        wallet_id: YooMoney wallet number (receiver).
        amount: Payment amount in RUB.
        label: Unique payment label for tracking.
        target: Payment description shown to payer.
        success_url: URL to redirect after successful payment.
    """
    params = {
        "receiver": wallet_id,
        "quickpay-form": "button",
        "paymentType": "AC",  # Bank card by default
        "sum": f"{amount:.2f}",
        "label": label,
        "targets": target,
        "successURL": success_url or "",
    }
    return f"{YOOMONEY_QUICKPAY_URL}?{urlencode(params)}"


def verify_notification(
    notification_secret: str,
    data: dict,
) -> bool:
    """Verify YooMoney HTTP notification signature.

    YooMoney sends POST with form data. SHA-1 hash is computed from:
    notification_type&operation_id&amount&currency&datetime&sender&codepro&notification_secret&label
    """
    check_string = "&".join(
        [
            str(data.get("notification_type", "")),
            str(data.get("operation_id", "")),
            str(data.get("amount", "")),
            str(data.get("currency", "")),
            str(data.get("datetime", "")),
            str(data.get("sender", "")),
            str(data.get("codepro", "")),
            notification_secret,
            str(data.get("label", "")),
        ]
    )
    computed_hash = hashlib.sha1(check_string.encode("utf-8")).hexdigest()
    received_hash = data.get("sha1_hash", "")
    return computed_hash == received_hash


async def get_operation_history(
    access_token: str,
    label: Optional[str] = None,
    records: int = 10,
) -> Optional[dict]:
    """Get operation history, optionally filtered by label."""
    data = {"type": "deposition", "records": records}
    if label:
        data["label"] = label

    async with httpx.AsyncClient(timeout=15.0) as client:
        resp = await client.post(
            f"{YOOMONEY_API_URL}/operation-history",
            headers={"Authorization": f"Bearer {access_token}"},
            data=data,
        )
        if resp.status_code == 200:
            return resp.json()
        logger.error(f"YooMoney operation-history failed: {resp.status_code}")
        return None
