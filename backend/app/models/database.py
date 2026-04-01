import logging

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.config import settings

logger = logging.getLogger(__name__)

engine = create_async_engine(settings.DATABASE_URL, echo=False)
async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


async def init_db():
    from app.models.intelligence_item import IntelligenceItem  # noqa: F401
    from app.models.intelligence_brief import IntelligenceBrief  # noqa: F401
    from app.models.osint_config import OSINTConfigRecord  # noqa: F401
    from app.models.escalation_tracker import EscalationTracker  # noqa: F401
    from app.models.alert_rule import AlertRule  # noqa: F401
    from app.models.alert_history import AlertHistory  # noqa: F401
    from app.models.alert_config import AlertConfigRecord  # noqa: F401

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

        # Migrate: add key_headlines column if missing
        try:
            await conn.execute(
                text("ALTER TABLE escalation_trackers ADD COLUMN key_headlines TEXT DEFAULT '[]'")
            )
        except Exception as e:
            logger.debug("Migration key_headlines: %s", e)

        # Migrate: add AI analysis columns to intelligence_briefs
        for col in ["ai_title", "ai_situation", "ai_analysis", "ai_trading_signal", "ai_risk_factors"]:
            try:
                await conn.execute(
                    text(f"ALTER TABLE intelligence_briefs ADD COLUMN {col} TEXT DEFAULT ''")
                )
            except Exception as e:
                logger.debug("Migration %s: %s", col, e)
        try:
            await conn.execute(
                text("ALTER TABLE intelligence_briefs ADD COLUMN ai_confidence INTEGER DEFAULT 0")
            )
        except Exception as e:
            logger.debug("Migration ai_confidence: %s", e)

        try:
            await conn.execute(
                text("ALTER TABLE intelligence_briefs ADD COLUMN graph_data TEXT DEFAULT '{}'")
            )
        except Exception as e:
            logger.debug("Migration graph_data: %s", e)

        # Migrate: add linked_market_slugs
        for table in ["intelligence_items", "intelligence_briefs"]:
            try:
                await conn.execute(
                    text(f"ALTER TABLE {table} ADD COLUMN linked_market_slugs TEXT DEFAULT '[]'")
                )
            except Exception as e:
                logger.debug("Migration linked_market_slugs on %s: %s", table, e)


async def get_db():
    async with async_session() as session:
        yield session
