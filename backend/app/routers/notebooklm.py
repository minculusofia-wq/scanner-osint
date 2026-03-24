"""NotebookLM API routes — Podcast, Mind Map, Data Table exports."""

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import PlainTextResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.database import get_db
from app.models.intelligence_brief import IntelligenceBrief
from app.services.notebooklm_service import NotebookLMService

router = APIRouter()
_notebook_service = NotebookLMService()


async def _fetch_briefs(db: AsyncSession, limit: int) -> list[dict]:
    """Fetch latest actionable briefs as dicts."""
    stmt = (
        select(IntelligenceBrief)
        .where(IntelligenceBrief.is_actionable == True)
        .order_by(IntelligenceBrief.created_at.desc())
        .limit(limit)
    )
    res = await db.execute(stmt)
    briefs = res.scalars().all()

    if not briefs:
        raise HTTPException(400, "Aucun signal Alpha récent à analyser.")

    return [
        {
            "id": b.id,
            "title": b.title,
            "ai_title": b.ai_title,
            "category": b.category,
            "region": b.region,
            "ai_situation": b.ai_situation,
            "ai_analysis": b.ai_analysis,
            "ai_trading_signal": b.ai_trading_signal,
            "ai_confidence": b.ai_confidence,
            "ai_risk_factors": b.ai_risk_factors,
        }
        for b in briefs
    ]


@router.get("/status")
async def notebook_status():
    """Check if the user is authenticated with NotebookLM."""
    is_authed = _notebook_service.check_auth()
    return {
        "is_ready": is_authed,
        "message": "Opérationnel" if is_authed else "Veuillez lancer 'notebooklm login' dans votre terminal.",
    }


@router.post("/generate-deep-dive")
async def generate_podcast(
    limit: int = Query(20, description="Max briefs to include"),
    db: AsyncSession = Depends(get_db),
):
    """Sync alpha briefs and trigger NotebookLM Audio Overview (podcast)."""
    try:
        brief_dicts = await _fetch_briefs(db, limit)
        nb_id = await _notebook_service.sync_alpha_signals(brief_dicts)
        url = await _notebook_service.generate_podcast(nb_id)

        return {
            "success": True,
            "notebook_url": url,
            "message": f"Podcast généré avec {len(brief_dicts)} signaux Alpha.",
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, str(e))


@router.post("/generate-mind-map")
async def generate_mind_map(
    limit: int = Query(20, description="Max briefs to include"),
    db: AsyncSession = Depends(get_db),
):
    """Sync alpha briefs and generate a Mind Map (JSON)."""
    try:
        brief_dicts = await _fetch_briefs(db, limit)
        nb_id = await _notebook_service.sync_alpha_signals(brief_dicts)
        mind_map = await _notebook_service.generate_mind_map(nb_id)

        return {
            "success": True,
            "mind_map": mind_map,
            "message": f"Mind Map générée avec {len(brief_dicts)} signaux.",
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, str(e))


@router.post("/generate-data-table")
async def generate_data_table(
    limit: int = Query(20, description="Max briefs to include"),
    db: AsyncSession = Depends(get_db),
):
    """Sync alpha briefs and generate a structured CSV data table."""
    try:
        brief_dicts = await _fetch_briefs(db, limit)
        nb_id = await _notebook_service.sync_alpha_signals(brief_dicts)
        csv_content = await _notebook_service.generate_data_table(nb_id)

        return PlainTextResponse(
            content=csv_content,
            media_type="text/csv",
            headers={"Content-Disposition": "attachment; filename=alpha_signals.csv"},
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, str(e))
