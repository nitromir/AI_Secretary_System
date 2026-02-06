"""amoCRM config and sync log repository."""

import json
import logging
from datetime import datetime
from typing import Any, List, Optional

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from db.models import AmoCRMConfig, AmoCRMSyncLog
from db.repositories.base import BaseRepository


logger = logging.getLogger(__name__)


class AmoCRMConfigRepository(BaseRepository[AmoCRMConfig]):
    """Repository for amoCRM singleton config."""

    def __init__(self, session: AsyncSession):
        super().__init__(session, AmoCRMConfig)

    async def get_config(self) -> Optional[dict]:
        """Get the singleton config row (id=1), masked secrets."""
        config = await self.session.get(AmoCRMConfig, 1)
        return config.to_dict() if config else None

    async def get_config_with_secrets(self) -> Optional[AmoCRMConfig]:
        """Get raw model for internal use (tokens, secrets)."""
        return await self.session.get(AmoCRMConfig, 1)

    async def save_config(self, **kwargs: Any) -> dict:
        """Create or update the singleton config."""
        config = await self.session.get(AmoCRMConfig, 1)
        if not config:
            config = AmoCRMConfig(id=1)
            self.session.add(config)

        simple_fields = [
            "subdomain",
            "client_id",
            "client_secret",
            "redirect_uri",
            "access_token",
            "refresh_token",
            "token_expires_at",
            "sync_contacts",
            "sync_leads",
            "sync_tasks",
            "auto_create_lead",
            "lead_pipeline_id",
            "lead_status_id",
            "webhook_url",
            "webhook_secret",
            "last_sync_at",
            "contacts_count",
            "leads_count",
        ]
        for field in simple_fields:
            if field in kwargs:
                setattr(config, field, kwargs[field])

        if "account_info" in kwargs:
            config.set_account_info(kwargs["account_info"])

        config.updated = datetime.utcnow()
        await self.session.commit()
        await self.session.refresh(config)
        return config.to_dict()

    async def clear_tokens(self) -> dict:
        """Clear OAuth tokens (disconnect)."""
        config = await self.session.get(AmoCRMConfig, 1)
        if config:
            config.access_token = None
            config.refresh_token = None
            config.token_expires_at = None
            config.account_info = None
            config.contacts_count = 0
            config.leads_count = 0
            config.last_sync_at = None
            config.updated = datetime.utcnow()
            await self.session.commit()
            await self.session.refresh(config)
            return config.to_dict()
        return {}


class AmoCRMSyncLogRepository(BaseRepository[AmoCRMSyncLog]):
    """Repository for amoCRM sync event log."""

    def __init__(self, session: AsyncSession):
        super().__init__(session, AmoCRMSyncLog)

    async def log_sync(
        self,
        direction: str,
        entity_type: str,
        action: str,
        entity_id: Optional[int] = None,
        details: Optional[dict] = None,
        status: str = "success",
        error_message: Optional[str] = None,
    ) -> dict:
        entry = AmoCRMSyncLog(
            direction=direction,
            entity_type=entity_type,
            entity_id=entity_id,
            action=action,
            details=json.dumps(details, ensure_ascii=False) if details else None,
            status=status,
            error_message=error_message,
        )
        self.session.add(entry)
        await self.session.commit()
        await self.session.refresh(entry)
        return entry.to_dict()

    async def get_recent(self, limit: int = 50) -> List[dict]:
        result = await self.session.execute(
            select(AmoCRMSyncLog).order_by(desc(AmoCRMSyncLog.created)).limit(limit)
        )
        return [e.to_dict() for e in result.scalars().all()]

    async def get_by_entity(self, entity_type: str, entity_id: int) -> List[dict]:
        result = await self.session.execute(
            select(AmoCRMSyncLog)
            .where(
                AmoCRMSyncLog.entity_type == entity_type,
                AmoCRMSyncLog.entity_id == entity_id,
            )
            .order_by(desc(AmoCRMSyncLog.created))
            .limit(20)
        )
        return [e.to_dict() for e in result.scalars().all()]
