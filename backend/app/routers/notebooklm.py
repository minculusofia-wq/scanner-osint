from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List

from app.models.database import get_db
from app.models.intelligence_brief import IntelligenceBrief
from app.services.notebooklm_service import NotebookLMService

router = APIRouter()
_notebook_service = NotebookLMService()

@router.get("/status")
async def notebook_status():
    """Check if the user is authenticated with G-NotebookLM."""
    is_authed = _notebook_service.check_auth()
    return {
        "is_ready": is_authed,
        "message": "Opérationnel" if is_authed else "Veuillez lancer 'notebooklm login' une fois dans votre terminal Mac."
    }

@router.post("/generate-deep-dive")
async def generate_podcast(
    limit: int = Query(20, description="Max alpha items to include"),
    db: AsyncSession = Depends(get_db)
):
    """Sync latest alpha briefs and trigger a NotebookLM Audio Overview."""
    # 1. Fetch latest high-confidence alpha briefs
    stmt = (
        select(IntelligenceBrief)
        .where(IntelligenceBrief.is_actionable == True)
        .order_by(IntelligenceBrief.created_at.desc())
        .limit(limit)
    )
    res = await db.execute(stmt)
    briefs = res.scalars().all()
    
    if not briefs:
        raise HTTPException(status_code=400, detail="Aucun signal Alpha récent à analyser pour le podcast.")
        
    brief_dicts = [
        {
            "id": b.id,
            "title": b.title,
            "ai_title": b.ai_title,
            "region": b.region,
            "ai_situation": b.ai_situation,
            "ai_analysis": b.ai_analysis,
            "ai_trading_signal": b.ai_trading_signal,
        }
        for b in briefs
    ]
    
    # 2. Sync to NotebookLM
    try:
        nb_id = await _notebook_service.sync_alpha_signals(brief_dicts)
        
        # 3. Trigger Podcast (Audio Overview)
        # We return the notebook URL so the user can see/hear it in the web interface
        url = f"https://notebooklm.google.com/notebook/{nb_id}"
        
        return {
            "success": True,
            "notebook_url": url,
            "message": "Intelligence Alpha synchronisée avec succès. Découvrez votre podcast Deep Dive sur NotebookLM."
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
