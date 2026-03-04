"""Alert Config Service.

Singleton JSON config in SQLite — same pattern as osint_config_service.py.
"""

import json
import logging
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.alert_config import AlertConfigRecord
from app.schemas.intelligence import AlertConfigSchema

logger = logging.getLogger(__name__)


class AlertConfigService:

    async def get_config(self, db: AsyncSession) -> AlertConfigSchema:
        stmt = select(AlertConfigRecord).where(AlertConfigRecord.id == 1)
        result = await db.execute(stmt)
        record = result.scalar_one_or_none()
        if not record:
            return AlertConfigSchema()
        try:
            data = json.loads(record.settings_json)
            return AlertConfigSchema(**data)
        except Exception:
            logger.warning("Failed to parse alert config, returning defaults")
            return AlertConfigSchema()

    async def update_config(
        self, db: AsyncSession, config: AlertConfigSchema
    ) -> AlertConfigSchema:
        stmt = select(AlertConfigRecord).where(AlertConfigRecord.id == 1)
        result = await db.execute(stmt)
        record = result.scalar_one_or_none()

        json_str = json.dumps(config.model_dump(), default=str)

        if record:
            record.settings_json = json_str
            record.updated_at = datetime.utcnow()
        else:
            record = AlertConfigRecord(id=1, settings_json=json_str)
            db.add(record)

        await db.commit()
        return config
