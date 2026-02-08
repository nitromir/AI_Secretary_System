# app/services/amocrm_service.py
"""amoCRM v4 API client — pure async functions (no DB access).

OAuth 2.0 flow:
1. Admin enters subdomain + client_id + client_secret in UI
2. Admin clicks "Connect" → redirect to amoCRM consent page
3. amoCRM redirects back with auth code → exchange for access_token + refresh_token
4. Tokens auto-refresh on 401 via router helper `_ensure_valid_token()`

API reference: https://www.amocrm.ru/developers/content/crm_platform/platform-abilities
"""

import asyncio
import logging
import os
from typing import Any, Optional

import httpx


logger = logging.getLogger(__name__)

AMOCRM_API_VERSION = "v4"
MAX_429_RETRIES = 3
RETRY_DELAY_SECONDS = 1.5

# Optional HTTP CONNECT proxy for Docker environments where amoCRM is unreachable.
# Set AMOCRM_PROXY=http://host.docker.internal:8899 in docker-compose.yml.
AMOCRM_PROXY = os.getenv("AMOCRM_PROXY") or None


def _http_client(timeout: float = 30.0) -> httpx.AsyncClient:
    """Create httpx client with optional proxy for amoCRM requests."""
    kwargs: dict[str, Any] = {"timeout": timeout}
    if AMOCRM_PROXY:
        kwargs["proxy"] = AMOCRM_PROXY
    return httpx.AsyncClient(**kwargs)


# ============== Exceptions ==============


class AmoCRMAPIError(Exception):
    """Generic amoCRM API error."""

    def __init__(self, status_code: int, detail: str):
        self.status_code = status_code
        self.detail = detail
        super().__init__(f"amoCRM API error {status_code}: {detail}")


class AmoCRMTokenExpired(AmoCRMAPIError):
    """Access token is expired or invalid (401)."""

    def __init__(self, detail: str = "Token expired"):
        super().__init__(status_code=401, detail=detail)


# ============== OAuth ==============


def build_auth_url(
    subdomain: str,
    client_id: str,
    redirect_uri: str,
) -> str:
    """Build amoCRM OAuth 2.0 authorization URL."""
    from urllib.parse import urlencode

    params = {
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "response_type": "code",
    }
    return f"https://{subdomain}.amocrm.ru/oauth?{urlencode(params)}"


async def exchange_code_for_token(
    subdomain: str,
    client_id: str,
    client_secret: str,
    code: str,
    redirect_uri: str,
) -> dict:
    """Exchange authorization code for access + refresh tokens.

    Returns dict with access_token, refresh_token, expires_in on success.
    Raises AmoCRMAPIError on failure.
    """
    url = f"https://{subdomain}.amocrm.ru/oauth2/access_token"
    payload = {
        "client_id": client_id,
        "client_secret": client_secret,
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": redirect_uri,
    }

    async with _http_client() as client:
        resp = await client.post(url, json=payload)
        if resp.status_code == 200:
            data = resp.json()
            logger.info("amoCRM tokens obtained successfully")
            return data
        logger.error(f"amoCRM token exchange failed: {resp.status_code} {resp.text}")
        raise AmoCRMAPIError(resp.status_code, resp.text)


async def refresh_access_token(
    subdomain: str,
    client_id: str,
    client_secret: str,
    refresh_token: str,
    redirect_uri: str,
) -> dict:
    """Refresh access token using refresh_token.

    Returns dict with new access_token, refresh_token, expires_in.
    Raises AmoCRMAPIError on failure.
    """
    url = f"https://{subdomain}.amocrm.ru/oauth2/access_token"
    payload = {
        "client_id": client_id,
        "client_secret": client_secret,
        "grant_type": "refresh_token",
        "refresh_token": refresh_token,
        "redirect_uri": redirect_uri,
    }

    async with _http_client() as client:
        resp = await client.post(url, json=payload)
        if resp.status_code == 200:
            data = resp.json()
            logger.info("amoCRM tokens refreshed successfully")
            return data
        logger.error(f"amoCRM token refresh failed: {resp.status_code} {resp.text}")
        raise AmoCRMAPIError(resp.status_code, resp.text)


# ============== Generic API request ==============


async def _api_request(
    subdomain: str,
    access_token: str,
    method: str,
    path: str,
    params: Optional[dict] = None,
    json_data: Optional[Any] = None,
) -> Any:
    """Make a request to amoCRM v4 API with 429 retry.

    Raises AmoCRMTokenExpired on 401, AmoCRMAPIError on other errors.
    Returns parsed JSON response (or None for 204).
    """
    url = f"https://{subdomain}.amocrm.ru/api/{AMOCRM_API_VERSION}/{path}"
    headers = {"Authorization": f"Bearer {access_token}"}

    for attempt in range(MAX_429_RETRIES + 1):
        async with _http_client() as client:
            resp = await client.request(
                method,
                url,
                headers=headers,
                params=params,
                json=json_data,
            )

        if resp.status_code == 204:
            return None

        if resp.status_code == 401:
            raise AmoCRMTokenExpired()

        if resp.status_code == 429:
            if attempt < MAX_429_RETRIES:
                delay = RETRY_DELAY_SECONDS * (attempt + 1)
                logger.warning(f"amoCRM rate limit hit, retrying in {delay}s...")
                await asyncio.sleep(delay)
                continue
            raise AmoCRMAPIError(429, "Rate limit exceeded after retries")

        if resp.status_code >= 400:
            raise AmoCRMAPIError(resp.status_code, resp.text)

        return resp.json()

    raise AmoCRMAPIError(429, "Rate limit exceeded after retries")


# ============== Account ==============


async def get_account_info(subdomain: str, access_token: str) -> dict:
    """Get amoCRM account info (name, subdomain, current_user, etc.)."""
    return await _api_request(subdomain, access_token, "GET", "account")


# ============== Contacts ==============


async def get_contacts(
    subdomain: str,
    access_token: str,
    page: int = 1,
    limit: int = 50,
    query: Optional[str] = None,
) -> dict:
    """Get contacts list. Returns _embedded.contacts array."""
    params: dict[str, Any] = {"page": page, "limit": limit}
    if query:
        params["query"] = query
    return await _api_request(subdomain, access_token, "GET", "contacts", params=params)


async def create_contact(
    subdomain: str,
    access_token: str,
    name: str,
    custom_fields: Optional[list] = None,
) -> dict:
    """Create a new contact."""
    contact: dict[str, Any] = {"name": name}
    if custom_fields:
        contact["custom_fields_values"] = custom_fields
    return await _api_request(subdomain, access_token, "POST", "contacts", json_data=[contact])


# ============== Leads ==============


async def get_leads(
    subdomain: str,
    access_token: str,
    page: int = 1,
    limit: int = 50,
    query: Optional[str] = None,
) -> dict:
    """Get leads list. Returns _embedded.leads array."""
    params: dict[str, Any] = {"page": page, "limit": limit}
    if query:
        params["query"] = query
    return await _api_request(subdomain, access_token, "GET", "leads", params=params)


async def create_lead(
    subdomain: str,
    access_token: str,
    name: str,
    pipeline_id: Optional[int] = None,
    status_id: Optional[int] = None,
    contact_id: Optional[int] = None,
) -> dict:
    """Create a new lead, optionally linked to a contact."""
    lead: dict[str, Any] = {"name": name}
    if pipeline_id:
        lead["pipeline_id"] = pipeline_id
    if status_id:
        lead["status_id"] = status_id
    if contact_id:
        lead["_embedded"] = {"contacts": [{"id": contact_id}]}
    return await _api_request(subdomain, access_token, "POST", "leads", json_data=[lead])


async def add_note_to_lead(
    subdomain: str,
    access_token: str,
    lead_id: int,
    text: str,
) -> dict:
    """Add a text note to a lead."""
    note = {
        "note_type": "common",
        "params": {"text": text},
    }
    return await _api_request(
        subdomain,
        access_token,
        "POST",
        f"leads/{lead_id}/notes",
        json_data=[note],
    )


# ============== Pipelines ==============


async def get_pipelines(subdomain: str, access_token: str) -> dict:
    """Get sales pipelines with their statuses."""
    return await _api_request(subdomain, access_token, "GET", "leads/pipelines")
