from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.database import get_db
from app.services.osint_config_service import OSINTConfigService
from app.services.osint_service import OSINTService

router = APIRouter()

_osint_service = OSINTService()
_config_service = OSINTConfigService()


@router.get("/items/")
async def list_items(
    limit: int = Query(50, le=200),
    offset: int = Query(0, ge=0),
    category: str | None = None,
    urgency: str | None = None,
    source: str | None = None,
    include_stale: bool = False,
    db: AsyncSession = Depends(get_db),
):
    """List intelligence items with optional filters."""
    return await _osint_service.get_items(db, limit, offset, category, urgency, source, include_stale)


@router.get("/briefs/")
async def list_briefs(
    limit: int = Query(20, le=100),
    actionable_only: bool = False,
    db: AsyncSession = Depends(get_db),
):
    """List intelligence briefs (rule-based synthesis)."""
    return await _osint_service.get_briefs(db, limit, actionable_only)


@router.post("/briefs/{brief_id}/dismiss")
async def dismiss_brief(
    brief_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Dismiss a brief (hide from dashboard)."""
    ok = await _osint_service.dismiss_brief(db, brief_id)
    if not ok:
        raise HTTPException(404, "Brief not found")
    return {"status": "dismissed"}


@router.post("/collect")
async def trigger_collection(
    db: AsyncSession = Depends(get_db),
):
    """Manually trigger one intelligence collection cycle."""
    config = await _config_service.get_config(db)
    stats = await _osint_service.collect_cycle(db, config)
    return stats


@router.get("/stats")
async def get_stats(
    db: AsyncSession = Depends(get_db),
):
    """Get intelligence dashboard statistics."""
    return await _osint_service.get_stats(db)


@router.get("/config")
async def get_config(
    db: AsyncSession = Depends(get_db),
):
    """Get current OSINT configuration."""
    return (await _config_service.get_config(db)).model_dump()


@router.put("/config")
async def update_config(
    data: dict,
    db: AsyncSession = Depends(get_db),
):
    """Update OSINT configuration."""
    from app.schemas.intelligence import OSINTConfig
    current = await _config_service.get_config(db)
    updated_data = current.model_dump()
    updated_data.update(data)
    new_config = OSINTConfig(**updated_data)
    return (await _config_service.update_config(db, new_config)).model_dump()
