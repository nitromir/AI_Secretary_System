"""
TTS Preset repository for managing voice presets.
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict

from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from db.models import TTSPreset
from db.repositories.base import BaseRepository
from db.redis_client import cache_set, cache_get, cache_delete, CacheKey

# Legacy JSON file path for backward compatibility with voice_clone_service
LEGACY_PRESETS_FILE = Path(__file__).parent.parent.parent / "custom_presets.json"


class PresetRepository(BaseRepository[TTSPreset]):
    """Repository for TTS voice presets."""

    CACHE_TTL = 600  # 10 minutes

    def __init__(self, session: AsyncSession):
        super().__init__(session, TTSPreset)

    def _cache_key(self, name: str = None) -> str:
        if name:
            return f"{CacheKey.TTS_PRESET}:{name}"
        return f"{CacheKey.TTS_PRESET}:all"

    async def _invalidate_cache(self):
        """Invalidate all preset caches."""
        await cache_delete(self._cache_key())

    async def _sync_to_legacy_file(self):
        """
        Write custom presets to legacy JSON file for backward compatibility
        with voice_clone_service that reads from the file directly.
        """
        try:
            custom = await self.get_custom_presets()
            # Remove 'builtin' key from exported data
            clean_presets = {}
            for name, data in custom.items():
                clean_data = {k: v for k, v in data.items() if k != "builtin"}
                clean_presets[name] = clean_data
            LEGACY_PRESETS_FILE.write_text(
                json.dumps(clean_presets, indent=2, ensure_ascii=False),
                encoding='utf-8'
            )
        except Exception as e:
            # Don't fail operations if legacy sync fails
            import logging
            logging.getLogger(__name__).warning(f"Failed to sync presets to legacy file: {e}")

    async def get_all_presets(self, include_builtin: bool = True) -> Dict[str, dict]:
        """
        Get all presets as name->params dict.
        Uses Redis cache for performance.
        """
        # Try cache first
        cached = await cache_get(self._cache_key())
        if cached:
            if not include_builtin:
                return {k: v for k, v in cached.items() if not v.get("builtin", False)}
            return cached

        # Fetch from database
        result = await self.session.execute(select(TTSPreset))
        presets = result.scalars().all()

        preset_dict = {}
        for p in presets:
            preset_dict[p.name] = {
                **p.get_params(),
                "builtin": p.builtin,
            }

        # Cache for 10 minutes
        await cache_set(self._cache_key(), preset_dict, self.CACHE_TTL)

        if not include_builtin:
            return {k: v for k, v in preset_dict.items() if not v.get("builtin", False)}
        return preset_dict

    async def get_custom_presets(self) -> Dict[str, dict]:
        """Get only custom (non-builtin) presets."""
        return await self.get_all_presets(include_builtin=False)

    async def get_by_name(self, name: str) -> Optional[dict]:
        """Get preset by name."""
        result = await self.session.execute(
            select(TTSPreset).where(TTSPreset.name == name)
        )
        preset = result.scalar_one_or_none()
        return preset.to_dict() if preset else None

    async def create_preset(
        self,
        name: str,
        params: dict,
        builtin: bool = False,
    ) -> dict:
        """Create new preset."""
        preset = TTSPreset(
            name=name,
            params=json.dumps(params, ensure_ascii=False),
            builtin=builtin,
            created=datetime.utcnow(),
            updated=datetime.utcnow(),
        )

        self.session.add(preset)
        await self.session.commit()
        await self.session.refresh(preset)
        await self._invalidate_cache()
        await self._sync_to_legacy_file()

        return preset.to_dict()

    async def update_preset(
        self,
        name: str,
        params: dict,
    ) -> Optional[dict]:
        """Update existing preset parameters."""
        result = await self.session.execute(
            select(TTSPreset).where(TTSPreset.name == name)
        )
        preset = result.scalar_one_or_none()

        if not preset:
            return None

        preset.params = json.dumps(params, ensure_ascii=False)
        preset.updated = datetime.utcnow()

        await self.session.commit()
        await self._invalidate_cache()
        await self._sync_to_legacy_file()

        return preset.to_dict()

    async def delete_preset(self, name: str) -> bool:
        """Delete preset by name."""
        result = await self.session.execute(
            delete(TTSPreset)
            .where(TTSPreset.name == name)
            .where(TTSPreset.builtin == False)  # Can't delete builtin
        )
        await self.session.commit()
        await self._invalidate_cache()
        await self._sync_to_legacy_file()
        return result.rowcount > 0

    async def import_from_dict(self, presets: Dict[str, dict]) -> int:
        """
        Import presets from dict format.
        Returns number of imported presets.
        """
        count = 0
        for name, params in presets.items():
            existing = await self.get_by_name(name)
            if existing:
                continue

            preset = TTSPreset(
                name=name,
                params=json.dumps(params, ensure_ascii=False),
                builtin=False,
                created=datetime.utcnow(),
                updated=datetime.utcnow(),
            )
            self.session.add(preset)
            count += 1

        await self.session.commit()
        await self._invalidate_cache()
        return count

    async def export_to_dict(self) -> Dict[str, dict]:
        """Export custom presets to dict format."""
        return await self.get_custom_presets()

    async def get_preset_count(self) -> dict:
        """Get preset counts."""
        from sqlalchemy import func

        total = await self.count()

        result = await self.session.execute(
            select(func.count())
            .select_from(TTSPreset)
            .where(TTSPreset.builtin == True)
        )
        builtin = result.scalar() or 0

        return {
            "total": total,
            "builtin": builtin,
            "custom": total - builtin,
        }
