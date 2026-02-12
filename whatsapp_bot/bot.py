"""WhatsApp bot entry point.

Run with:  python -m whatsapp_bot

Starts a FastAPI webhook server that receives messages from WhatsApp Cloud API
and routes them through the LLM pipeline.
"""

import asyncio
import logging
from contextlib import asynccontextmanager
from typing import Any

import uvicorn
from fastapi import BackgroundTasks, FastAPI, Query, Request, Response

from .config import (
    get_wa_instance_id,
    get_whatsapp_settings,
    load_config_from_api,
)
from .handlers.interactive import handle_interactive_reply
from .handlers.messages import handle_text_message
from .services.whatsapp_client import get_whatsapp_client
from .state import get_bot_config, set_bot_config


logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown logic."""
    logger.info("WhatsApp bot starting up")
    # Initialize sales database
    from .sales.database import close_sales_db, get_sales_db

    await get_sales_db()
    yield
    # Cleanup
    await close_sales_db()
    client = get_whatsapp_client()
    await client.close()
    logger.info("WhatsApp bot shut down")


app = FastAPI(title="WhatsApp Bot Webhook", lifespan=lifespan)


@app.get("/webhook")
async def verify_webhook(
    hub_mode: str = Query(alias="hub.mode", default=""),
    hub_verify_token: str = Query(alias="hub.verify_token", default=""),
    hub_challenge: str = Query(alias="hub.challenge", default=""),
) -> Response:
    """Webhook verification endpoint for Meta.

    Meta sends a GET request with hub.mode, hub.verify_token, and hub.challenge.
    We verify the token and return the challenge to confirm the webhook.
    """
    bot_config = get_bot_config()
    settings = get_whatsapp_settings()
    expected_token = bot_config.verify_token if bot_config else settings.verify_token

    if hub_mode == "subscribe" and hub_verify_token == expected_token:
        logger.info("Webhook verified successfully")
        return Response(content=hub_challenge, media_type="text/plain")

    logger.warning("Webhook verification failed: invalid token")
    return Response(content="Forbidden", status_code=403)


@app.post("/webhook")
async def receive_webhook(request: Request, background_tasks: BackgroundTasks) -> dict:
    """Receive incoming messages from WhatsApp Cloud API.

    Returns 200 immediately and processes messages in the background
    to avoid webhook timeout (Meta expects response within 5s).
    """
    body = await request.body()

    # Verify signature
    signature = request.headers.get("X-Hub-Signature-256", "")
    client = get_whatsapp_client()
    if not client.verify_webhook_signature(body, signature):
        logger.warning("Invalid webhook signature")
        return {"status": "error", "message": "Invalid signature"}

    data = await request.json()

    # Extract messages from webhook payload
    for entry in data.get("entry", []):
        for change in entry.get("changes", []):
            value = change.get("value", {})

            # Process incoming messages
            for message in value.get("messages", []):
                background_tasks.add_task(_dispatch_message, message)

            # Log delivery statuses (optional)
            for status in value.get("statuses", []):
                _log_status(status)

    return {"status": "ok"}


@app.get("/health")
async def health() -> dict:
    """Health check endpoint."""
    bot_config = get_bot_config()
    return {
        "status": "ok",
        "service": "whatsapp_bot",
        "instance_id": bot_config.instance_id if bot_config else None,
        "name": bot_config.name if bot_config else "standalone",
    }


async def _dispatch_message(message: dict[str, Any]) -> None:
    """Route an incoming message to the appropriate handler."""
    msg_type = message.get("type", "")
    phone = message.get("from", "")
    message_id = message.get("id", "")

    if not phone:
        return

    logger.info("Incoming %s message from %s", msg_type, phone)

    if msg_type == "text":
        text = message.get("text", {}).get("body", "")
        if text:
            await handle_text_message(phone, text, message_id)

    elif msg_type == "interactive":
        interactive = message.get("interactive", {})
        await handle_interactive_reply(phone, interactive)

    # TODO (WA-12): Handle audio/voice messages
    # elif msg_type == "audio":
    #     await handle_audio_message(phone, message, message_id)

    else:
        logger.debug("Unhandled message type: %s from %s", msg_type, phone)


def _log_status(status: dict[str, Any]) -> None:
    """Log message delivery status updates."""
    recipient = status.get("recipient_id", "?")
    status_value = status.get("status", "?")
    logger.debug("Status update: %s → %s", recipient, status_value)


async def main() -> None:
    """Main entry point — load config and start webhook server."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    # Check for multi-instance mode
    instance_id = get_wa_instance_id()

    if instance_id:
        logger.info(f"Multi-instance mode: loading config for {instance_id}")
        try:
            bot_config = await load_config_from_api(instance_id)
            set_bot_config(bot_config)
            logger.info(f"Loaded config for WhatsApp bot: {bot_config.name}")
            logger.info(f"LLM backend: {bot_config.llm_backend}")
            logger.info(f"Phone Number ID: {bot_config.phone_number_id}")
        except Exception as e:
            logger.error(f"Failed to load config from API: {e}")
            logger.info("Falling back to .env configuration")
    else:
        logger.info("Standalone mode: using .env configuration")

    settings = get_whatsapp_settings()
    bot_config = get_bot_config()
    host = settings.webhook_host
    port = bot_config.webhook_port if bot_config else settings.webhook_port

    logger.info(f"Starting WhatsApp webhook server on {host}:{port}")

    config = uvicorn.Config(
        app,
        host=host,
        port=port,
        log_level="info",
    )
    server = uvicorn.Server(config)
    await server.serve()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass


def run() -> None:
    """Entry point for ``python -m whatsapp_bot``."""
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
