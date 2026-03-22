import asyncio
import logging
import time as _time
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.models.database import init_db, async_session
from app.services.osint_config_service import OSINTConfigService
from app.services.osint_service import OSINTService

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

osint_service = OSINTService()
config_service = OSINTConfigService()


async def _collection_loop():
    """Background task: periodically collect OSINT intelligence."""
    while True:
        try:
            async with async_session() as db:
                config = await config_service.get_config(db)

            if not config.enabled:
                await asyncio.sleep(60)
                continue

            interval = max(config.collection_interval_seconds, 60)
            await asyncio.sleep(interval)

            async with async_session() as db:
                config = await config_service.get_config(db)

            if not config.enabled:
                continue

            cycle_start = _time.time()
            async with async_session() as db:
                stats = await osint_service.collect_cycle(db, config)
            duration = _time.time() - cycle_start

            logger.info(
                f"Intelligence cycle: {stats.get('new', 0)} new items, "
                f"{stats.get('briefs_generated', 0)} briefs in {duration:.1f}s"
            )

        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.error(f"Intelligence collection error: {e}", exc_info=True)
            await asyncio.sleep(60)


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    logger.info("Database initialized")

    collection_task = asyncio.create_task(_collection_loop())
    logger.info("Intelligence collection loop started")

    yield

    collection_task.cancel()
    try:
        await collection_task
    except asyncio.CancelledError:
        pass
    logger.info("Intelligence collection loop stopped")


app = FastAPI(
    title="Scanner OSINT",
    description="Outil d'intelligence OSINT pour Polymarket",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:3001"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

from app.routers import intelligence, alerts, notebooklm  # noqa: E402

app.include_router(intelligence.router, prefix="/api/intelligence", tags=["intelligence"])
app.include_router(alerts.router, prefix="/api/alerts", tags=["alerts"])
app.include_router(notebooklm.router, prefix="/api/notebooklm", tags=["notebooklm"])



@app.get("/health")
async def health():
    return {"status": "ok", "service": "scanner-osint"}
