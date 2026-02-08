# app/routers/amocrm.py
"""amoCRM integration router — OAuth flow, contacts, leads, pipelines, sync."""

import logging
import os
from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import RedirectResponse
from pydantic import BaseModel

from app.services.amocrm_service import (
    AmoCRMAPIError,
    add_note_to_lead,
    build_auth_url,
    create_contact,
    create_lead,
    exchange_code_for_token,
    get_account_info,
    get_contacts,
    get_leads,
    get_pipelines,
    refresh_access_token,
)
from auth_manager import User, get_current_user
from db.integration import async_amocrm_manager, async_audit_logger


logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin/crm", tags=["crm"])
webhook_router = APIRouter(tags=["amocrm-webhook"])


# ============== Helpers ==============


async def _get_valid_token() -> dict:
    """Get config with a valid access token; auto-refresh if expired.

    Returns full config dict with fresh tokens.
    Raises HTTPException if not connected or refresh fails.
    """
    config = await async_amocrm_manager.get_config_with_secrets()
    if not config or not config.get("access_token"):
        raise HTTPException(status_code=400, detail="amoCRM not connected")

    subdomain = config.get("subdomain", "")

    # Check if token expired
    expires_at = config.get("token_expires_at")
    token_expired = True
    if expires_at:
        if isinstance(expires_at, str):
            try:
                expires_at = datetime.fromisoformat(expires_at)
            except ValueError:
                expires_at = None
        if expires_at:
            # Refresh 5 minutes before expiry
            token_expired = datetime.utcnow() >= expires_at - timedelta(minutes=5)

    if token_expired:
        refresh_token = config.get("refresh_token")
        if not refresh_token:
            raise HTTPException(status_code=400, detail="No refresh token, re-authorize")

        try:
            tokens = await refresh_access_token(
                subdomain=subdomain,
                client_id=config.get("client_id", ""),
                client_secret=config.get("client_secret", ""),
                refresh_token=refresh_token,
                redirect_uri=config.get("redirect_uri", ""),
            )
        except AmoCRMAPIError as e:
            logger.error(f"Token refresh failed: {e}")
            raise HTTPException(status_code=401, detail="Token refresh failed, re-authorize")

        expires_in = tokens.get("expires_in", 86400)
        new_expires = datetime.utcnow() + timedelta(seconds=expires_in)

        await async_amocrm_manager.save_config(
            access_token=tokens["access_token"],
            refresh_token=tokens["refresh_token"],
            token_expires_at=new_expires,
        )

        config["access_token"] = tokens["access_token"]
        config["refresh_token"] = tokens["refresh_token"]
        config["token_expires_at"] = new_expires.isoformat()

    return config


# ============== Pydantic Models ==============


class AmoCRMConfigRequest(BaseModel):
    subdomain: Optional[str] = None
    client_id: Optional[str] = None
    client_secret: Optional[str] = None
    redirect_uri: Optional[str] = None
    sync_contacts: Optional[bool] = None
    sync_leads: Optional[bool] = None
    sync_tasks: Optional[bool] = None
    auto_create_lead: Optional[bool] = None
    lead_pipeline_id: Optional[int] = None
    lead_status_id: Optional[int] = None


class CreateContactRequest(BaseModel):
    name: str
    custom_fields: Optional[list] = None


class CreateLeadRequest(BaseModel):
    name: str
    pipeline_id: Optional[int] = None
    status_id: Optional[int] = None
    contact_id: Optional[int] = None


class AddNoteRequest(BaseModel):
    text: str


# ============== Status & Config ==============


@router.get("/status")
async def crm_status(user: User = Depends(get_current_user)):
    """Quick status: connected? token expired? last sync."""
    config = await async_amocrm_manager.get_config()
    if not config:
        return {
            "connected": False,
            "has_credentials": False,
            "last_sync": None,
        }

    return {
        "connected": config.get("is_connected", False),
        "has_credentials": bool(config.get("client_id")),
        "subdomain": config.get("subdomain"),
        "account_info": config.get("account_info"),
        "contacts_count": config.get("contacts_count", 0),
        "leads_count": config.get("leads_count", 0),
        "last_sync": config.get("last_sync_at"),
    }


@router.get("/config")
async def crm_get_config(user: User = Depends(get_current_user)):
    """Get amoCRM config (secrets masked)."""
    config = await async_amocrm_manager.get_config()
    return {"config": config or {}}


@router.post("/config")
async def crm_save_config(
    request: AmoCRMConfigRequest,
    user: User = Depends(get_current_user),
):
    """Save OAuth credentials and sync settings."""
    kwargs = {k: v for k, v in request.model_dump().items() if v is not None}
    config = await async_amocrm_manager.save_config(**kwargs)

    await async_audit_logger.log(
        action="update",
        resource="amocrm_config",
        user_id=user.username,
        details={"fields": list(kwargs.keys())},
    )
    return {"status": "ok", "config": config}


# ============== OAuth Flow ==============


@router.get("/auth-url")
async def crm_auth_url(request: Request, user: User = Depends(get_current_user)):
    """Build OAuth authorization URL for amoCRM."""
    config = await async_amocrm_manager.get_config_with_secrets()
    if not config or not config.get("client_id"):
        raise HTTPException(status_code=400, detail="Client ID not configured")

    subdomain = config.get("subdomain", "")
    if not subdomain:
        raise HTTPException(status_code=400, detail="Subdomain not configured")

    # Build redirect_uri: prefer saved, otherwise auto-detect
    redirect_uri = config.get("redirect_uri")
    if not redirect_uri:
        port = os.getenv("ORCHESTRATOR_PORT", "8002")
        redirect_uri = f"http://localhost:{port}/admin/crm/oauth-redirect"

    url = build_auth_url(
        subdomain=subdomain,
        client_id=config["client_id"],
        redirect_uri=redirect_uri,
    )
    return {"auth_url": url, "redirect_uri": redirect_uri}


@router.get("/oauth-redirect")
async def crm_oauth_redirect(
    code: Optional[str] = None,
    error: Optional[str] = None,
    referer: Optional[str] = None,
):
    """Server-side OAuth callback. amoCRM redirects here with ?code=...

    Exchanges code for tokens, saves, then redirects browser to admin panel.
    No JWT required — this is called by amoCRM redirect, not by the admin panel.
    """
    if error:
        logger.error(f"amoCRM OAuth error: {error}")
        return RedirectResponse(url="/admin/#/crm?error=oauth_denied")

    if not code:
        return RedirectResponse(url="/admin/#/crm?error=no_code")

    config = await async_amocrm_manager.get_config_with_secrets()
    if not config:
        return RedirectResponse(url="/admin/#/crm?error=no_config")

    subdomain = config.get("subdomain", "")
    client_id = config.get("client_id", "")
    client_secret = config.get("client_secret", "")
    redirect_uri = config.get("redirect_uri", "")
    if not redirect_uri:
        port = os.getenv("ORCHESTRATOR_PORT", "8002")
        redirect_uri = f"http://localhost:{port}/admin/crm/oauth-redirect"

    try:
        tokens = await exchange_code_for_token(
            subdomain=subdomain,
            client_id=client_id,
            client_secret=client_secret,
            code=code,
            redirect_uri=redirect_uri,
        )
    except AmoCRMAPIError as e:
        logger.error(f"amoCRM token exchange failed: {e}")
        return RedirectResponse(url="/admin/#/crm?error=token_exchange_failed")

    # Save tokens
    expires_in = tokens.get("expires_in", 86400)
    expires_at = datetime.utcnow() + timedelta(seconds=expires_in)

    # Try to fetch account info
    account_info = {}
    try:
        account_info = await get_account_info(subdomain, tokens["access_token"])
    except Exception as e:
        logger.warning(f"Could not fetch account info: {e}")

    await async_amocrm_manager.save_config(
        access_token=tokens["access_token"],
        refresh_token=tokens["refresh_token"],
        token_expires_at=expires_at,
        redirect_uri=redirect_uri,
        account_info=account_info,
    )

    await async_amocrm_manager.log_sync(
        direction="incoming",
        entity_type="auth",
        action="connect",
        details={"account": account_info.get("name", "")},
    )

    return RedirectResponse(url="/admin/#/crm?connected=true")


@router.post("/disconnect")
async def crm_disconnect(user: User = Depends(get_current_user)):
    """Clear tokens — disconnect from amoCRM."""
    await async_amocrm_manager.clear_tokens()

    await async_audit_logger.log(
        action="delete",
        resource="amocrm_config",
        resource_id="tokens",
        user_id=user.username,
    )

    await async_amocrm_manager.log_sync(
        direction="outgoing",
        entity_type="auth",
        action="disconnect",
    )

    return {"status": "disconnected"}


@router.post("/test")
async def crm_test_connection(user: User = Depends(get_current_user)):
    """Test connection by fetching account info."""
    config = await _get_valid_token()
    try:
        account = await get_account_info(config["subdomain"], config["access_token"])
        return {"status": "ok", "account": account}
    except AmoCRMAPIError as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail)


@router.post("/refresh-token")
async def crm_force_refresh_token(user: User = Depends(get_current_user)):
    """Force token refresh."""
    config = await async_amocrm_manager.get_config_with_secrets()
    if not config or not config.get("refresh_token"):
        raise HTTPException(status_code=400, detail="No refresh token available")

    try:
        tokens = await refresh_access_token(
            subdomain=config.get("subdomain", ""),
            client_id=config.get("client_id", ""),
            client_secret=config.get("client_secret", ""),
            refresh_token=config["refresh_token"],
            redirect_uri=config.get("redirect_uri", ""),
        )
    except AmoCRMAPIError as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail)

    expires_in = tokens.get("expires_in", 86400)
    expires_at = datetime.utcnow() + timedelta(seconds=expires_in)

    await async_amocrm_manager.save_config(
        access_token=tokens["access_token"],
        refresh_token=tokens["refresh_token"],
        token_expires_at=expires_at,
    )
    return {"status": "ok", "expires_at": expires_at.isoformat()}


# ============== Contacts ==============


@router.get("/contacts")
async def crm_get_contacts(
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=250),
    query: Optional[str] = None,
    user: User = Depends(get_current_user),
):
    """List contacts from amoCRM (proxied)."""
    config = await _get_valid_token()
    try:
        data = await get_contacts(config["subdomain"], config["access_token"], page, limit, query)
        return data
    except AmoCRMAPIError as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail)


@router.post("/contacts")
async def crm_create_contact(
    request: CreateContactRequest,
    user: User = Depends(get_current_user),
):
    """Create a contact in amoCRM."""
    config = await _get_valid_token()
    try:
        result = await create_contact(
            config["subdomain"],
            config["access_token"],
            name=request.name,
            custom_fields=request.custom_fields,
        )

        await async_amocrm_manager.log_sync(
            direction="outgoing",
            entity_type="contact",
            action="create",
            details={"name": request.name},
        )

        return result
    except AmoCRMAPIError as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail)


# ============== Leads ==============


@router.get("/leads")
async def crm_get_leads(
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=250),
    query: Optional[str] = None,
    user: User = Depends(get_current_user),
):
    """List leads from amoCRM (proxied)."""
    config = await _get_valid_token()
    try:
        data = await get_leads(config["subdomain"], config["access_token"], page, limit, query)
        return data
    except AmoCRMAPIError as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail)


@router.post("/leads")
async def crm_create_lead(
    request: CreateLeadRequest,
    user: User = Depends(get_current_user),
):
    """Create a lead in amoCRM."""
    config = await _get_valid_token()
    try:
        result = await create_lead(
            config["subdomain"],
            config["access_token"],
            name=request.name,
            pipeline_id=request.pipeline_id,
            status_id=request.status_id,
            contact_id=request.contact_id,
        )

        await async_amocrm_manager.log_sync(
            direction="outgoing",
            entity_type="lead",
            action="create",
            details={"name": request.name},
        )

        return result
    except AmoCRMAPIError as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail)


@router.post("/leads/{lead_id}/notes")
async def crm_add_note_to_lead(
    lead_id: int,
    request: AddNoteRequest,
    user: User = Depends(get_current_user),
):
    """Add a note to a lead."""
    config = await _get_valid_token()
    try:
        result = await add_note_to_lead(
            config["subdomain"],
            config["access_token"],
            lead_id=lead_id,
            text=request.text,
        )
        return result
    except AmoCRMAPIError as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail)


# ============== Pipelines ==============


@router.get("/pipelines")
async def crm_get_pipelines(user: User = Depends(get_current_user)):
    """List pipelines with their statuses."""
    config = await _get_valid_token()
    try:
        data = await get_pipelines(config["subdomain"], config["access_token"])
        return data
    except AmoCRMAPIError as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail)


# ============== Sync ==============


@router.post("/sync")
async def crm_sync(user: User = Depends(get_current_user)):
    """Manual sync — fetch counts from amoCRM and update local stats."""
    config = await _get_valid_token()
    subdomain = config["subdomain"]
    access_token = config["access_token"]

    contacts_count = 0
    leads_count = 0

    try:
        contacts_full = await get_contacts(subdomain, access_token, page=1, limit=250)
        contacts_list = (contacts_full or {}).get("_embedded", {}).get("contacts", [])
        contacts_count = len(contacts_list)
    except AmoCRMAPIError:
        pass

    try:
        leads_full = await get_leads(subdomain, access_token, page=1, limit=250)
        leads_list = (leads_full or {}).get("_embedded", {}).get("leads", [])
        leads_count = len(leads_list)
    except AmoCRMAPIError:
        pass

    await async_amocrm_manager.save_config(
        contacts_count=contacts_count,
        leads_count=leads_count,
        last_sync_at=datetime.utcnow(),
    )

    await async_amocrm_manager.log_sync(
        direction="incoming",
        entity_type="sync",
        action="sync",
        details={"contacts": contacts_count, "leads": leads_count},
    )

    return {
        "status": "ok",
        "contacts_count": contacts_count,
        "leads_count": leads_count,
        "synced_at": datetime.utcnow().isoformat(),
    }


@router.get("/sync-log")
async def crm_sync_log(
    limit: int = Query(50, ge=1, le=200),
    user: User = Depends(get_current_user),
):
    """Get sync event log."""
    logs = await async_amocrm_manager.get_sync_logs(limit)
    return {"logs": logs}


# ============== Webhook (public) ==============


@webhook_router.post("/webhooks/amocrm")
async def amocrm_webhook(request: Request):
    """Handle incoming amoCRM webhook.

    amoCRM sends POST with form-encoded data for events like:
    contacts[add], contacts[update], leads[add], leads[status], etc.
    """
    try:
        content_type = request.headers.get("content-type", "")

        if "application/json" in content_type:
            data = await request.json()
        else:
            # Form-encoded
            form = await request.form()
            data = dict(form)

        logger.info(
            f"amoCRM webhook received: {list(data.keys()) if isinstance(data, dict) else 'raw'}"
        )

        await async_amocrm_manager.log_sync(
            direction="incoming",
            entity_type="webhook",
            action="receive",
            details=data if isinstance(data, dict) else {"raw": str(data)[:500]},
        )

        return {"status": "ok"}
    except Exception as e:
        logger.error(f"amoCRM webhook error: {e}")
        return {"status": "error", "detail": str(e)}
