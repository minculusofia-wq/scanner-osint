import json
import logging
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.osint_config import OSINTConfigRecord
from app.schemas.intelligence import OSINTConfig

logger = logging.getLogger(__name__)


class OSINTConfigService:
    """Singleton JSON config in SQLite (same pattern as risk_settings)."""

    async def get_config(self, db: AsyncSession) -> OSINTConfig:
        stmt = select(OSINTConfigRecord).where(OSINTConfigRecord.id == 1)
        result = await db.execute(stmt)
        record = result.scalar_one_or_none()
        if not record:
            return OSINTConfig()
        try:
            data = json.loads(record.settings_json)
            return OSINTConfig(**data)
        except Exception:
            logger.warning("Failed to parse OSINT config, returning defaults")
            return OSINTConfig()

    async def update_config(self, db: AsyncSession, config: OSINTConfig) -> OSINTConfig:
        stmt = select(OSINTConfigRecord).where(OSINTConfigRecord.id == 1)
        result = await db.execute(stmt)
        record = result.scalar_one_or_none()

        json_str = json.dumps(config.model_dump(), default=str)

        if record:
            record.settings_json = json_str
            record.updated_at = datetime.utcnow()
        else:
            record = OSINTConfigRecord(id=1, settings_json=json_str)
            db.add(record)

        await db.commit()
        return config
