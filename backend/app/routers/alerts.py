"""Alert & Early Warning API routes."""

import json

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.alert_history import AlertHistory
from app.models.alert_rule import AlertRule
from app.models.escalation_tracker import EscalationTracker
from app.models.database import get_db
from app.schemas.intelligence import (
    AlertConfigSchema,
    AlertHistoryResponse,
    AlertRuleSchema,
    EscalationTrackerResponse,
)
from app.services.alert_config_service import AlertConfigService
from app.services.alert_delivery import AlertDelivery
from app.services.precursor_patterns import ALL_PATTERNS

router = APIRouter()

_config_service = AlertConfigService()
_delivery = AlertDelivery()


# --- Escalation Trackers ---

@router.get("/escalations")
async def list_escalations(
    active_only: bool = True,
    db: AsyncSession = Depends(get_db),
):
    """Get escalation trackers."""
    stmt = select(EscalationTracker).order_by(
        EscalationTracker.escalation_score.desc()
    )
    if active_only:
        stmt = stmt.where(EscalationTracker.is_active == True)

    result = await db.execute(stmt)
    trackers = result.scalars().all()

    return [_tracker_to_dict(t) for t in trackers]


# --- Alert History ---

@router.get("/history")
async def list_alert_history(
    limit: int = Query(50, le=200),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    """Get alert history (paginated, most recent first)."""
    stmt = (
        select(AlertHistory)
        .order_by(AlertHistory.created_at.desc())
        .offset(offset)
        .limit(limit)
    )
    result = await db.execute(stmt)
    alerts = result.scalars().all()

    count_stmt = select(func.count(AlertHistory.id))
    count_result = await db.execute(count_stmt)
    total = count_result.scalar() or 0

    return {
        "items": [_alert_to_dict(a) for a in alerts],
        "total": total,
    }


# --- Alert Rules CRUD ---

@router.get("/rules")
async def list_rules(db: AsyncSession = Depends(get_db)):
    stmt = select(AlertRule).order_by(AlertRule.created_at.desc())
    result = await db.execute(stmt)
    rules = result.scalars().all()
    return [_rule_to_dict(r) for r in rules]


@router.post("/rules")
async def create_rule(
    data: AlertRuleSchema,
    db: AsyncSession = Depends(get_db),
):
    rule = AlertRule(
        name=data.name,
        description=data.description,
        is_enabled=data.is_enabled,
        min_escalation_level=data.min_escalation_level,
        min_priority_score=data.min_priority_score,
        min_signal_count=data.min_signal_count,
        min_unique_sources=data.min_unique_sources,
        signal_window_minutes=data.signal_window_minutes,
        categories=json.dumps(data.categories),
        regions=json.dumps(data.regions),
        required_patterns=json.dumps(data.required_patterns),
        delivery_channels=json.dumps(data.delivery_channels),
        cooldown_minutes=data.cooldown_minutes,
        max_alerts_per_hour=data.max_alerts_per_hour,
    )
    db.add(rule)
    await db.commit()
    await db.refresh(rule)
    return _rule_to_dict(rule)


@router.put("/rules/{rule_id}")
async def update_rule(
    rule_id: int,
    data: AlertRuleSchema,
    db: AsyncSession = Depends(get_db),
):
    stmt = select(AlertRule).where(AlertRule.id == rule_id)
    result = await db.execute(stmt)
    rule = result.scalar_one_or_none()
    if not rule:
        raise HTTPException(404, "Rule not found")

    rule.name = data.name
    rule.description = data.description
    rule.is_enabled = data.is_enabled
    rule.min_escalation_level = data.min_escalation_level
    rule.min_priority_score = data.min_priority_score
    rule.min_signal_count = data.min_signal_count
    rule.min_unique_sources = data.min_unique_sources
    rule.signal_window_minutes = data.signal_window_minutes
    rule.categories = json.dumps(data.categories)
    rule.regions = json.dumps(data.regions)
    rule.required_patterns = json.dumps(data.required_patterns)
    rule.delivery_channels = json.dumps(data.delivery_channels)
    rule.cooldown_minutes = data.cooldown_minutes
    rule.max_alerts_per_hour = data.max_alerts_per_hour

    from datetime import datetime
    rule.updated_at = datetime.utcnow()

    await db.commit()
    return _rule_to_dict(rule)


@router.delete("/rules/{rule_id}")
async def delete_rule(
    rule_id: int,
    db: AsyncSession = Depends(get_db),
):
    stmt = select(AlertRule).where(AlertRule.id == rule_id)
    result = await db.execute(stmt)
    rule = result.scalar_one_or_none()
    if not rule:
        raise HTTPException(404, "Rule not found")

    await db.delete(rule)
    await db.commit()
    return {"status": "deleted"}


# --- Alert Config ---

@router.get("/config")
async def get_alert_config(db: AsyncSession = Depends(get_db)):
    config = await _config_service.get_config(db)
    return config.model_dump()


@router.put("/config")
async def update_alert_config(
    data: dict,
    db: AsyncSession = Depends(get_db),
):
    current = await _config_service.get_config(db)
    updated_data = current.model_dump()
    updated_data.update(data)
    new_config = AlertConfigSchema(**updated_data)
    result = await _config_service.update_config(db, new_config)
    return result.model_dump()


# --- Test Alert ---

@router.post("/test")
async def send_test_alert(db: AsyncSession = Depends(get_db)):
    """Send a test alert to configured channels."""
    config = await _config_service.get_config(db)
    if not config.alerts_enabled:
        raise HTTPException(400, "Alerts are disabled. Enable them first.")

    results = await _delivery.send_test_alert(config)
    if not any(results.values()):
        raise HTTPException(500, "Failed to send test alert to any channel")

    return {"status": "sent", "channels": results}


# --- Precursor Patterns ---

@router.get("/patterns")
async def list_patterns():
    """List all available precursor patterns."""
    return [
        {
            "id": p.name,
            "name": p.name,
            "category": p.category,
            "severity": p.severity,
            "description": p.description,
            "required_sources": p.required_sources,
            "min_source_match": p.min_source_match,
            "keywords": p.keywords[:20],
            "min_keyword_match": p.min_keyword_match,
        }
        for p in ALL_PATTERNS
    ]


# --- Helpers ---

def _tracker_to_dict(t: EscalationTracker) -> dict:
    return {
        "id": t.id,
        "name": t.name,
        "category": t.category,
        "region": t.region,
        "countries": _safe_json(t.countries),
        "escalation_level": t.escalation_level,
        "escalation_score": t.escalation_score,
        "previous_level": t.previous_level,
        "level_changed_at": t.level_changed_at.isoformat() if t.level_changed_at else None,
        "signal_count_1h": t.signal_count_1h,
        "signal_count_6h": t.signal_count_6h,
        "signal_count_24h": t.signal_count_24h,
        "unique_sources_1h": t.unique_sources_1h,
        "avg_sentiment_1h": t.avg_sentiment_1h,
        "matched_patterns": _safe_json(t.matched_patterns),
        "contributing_source_types": _safe_json(t.contributing_source_types),
        "key_headlines": _safe_json(t.key_headlines),
        "linked_markets": [
            {"condition_id": mid, "question": mq}
            for mid, mq in zip(
                _safe_json(t.linked_market_ids),
                _safe_json(t.linked_market_questions),
            )
        ],
        "is_active": t.is_active,
        "created_at": t.created_at.isoformat() if t.created_at else None,
        "updated_at": t.updated_at.isoformat() if t.updated_at else None,
    }


def _alert_to_dict(a: AlertHistory) -> dict:
    return {
        "id": a.id,
        "title": a.title,
        "message": a.message,
        "severity": a.severity,
        "escalation_level": a.escalation_level,
        "region": a.region,
        "category": a.category,
        "trigger_signal_count": a.trigger_signal_count,
        "trigger_source_types": _safe_json(a.trigger_source_types),
        "matched_patterns": _safe_json(a.matched_patterns),
        "channels_sent": _safe_json(a.channels_sent),
        "delivery_status": a.delivery_status,
        "linked_markets": [
            {"condition_id": mid, "question": mq}
            for mid, mq in zip(
                _safe_json(a.linked_market_ids),
                _safe_json(a.linked_market_questions),
            )
        ],
        "created_at": a.created_at.isoformat() if a.created_at else None,
    }


def _rule_to_dict(r: AlertRule) -> dict:
    return {
        "id": r.id,
        "name": r.name,
        "description": r.description,
        "is_enabled": r.is_enabled,
        "min_escalation_level": r.min_escalation_level,
        "min_priority_score": r.min_priority_score,
        "min_signal_count": r.min_signal_count,
        "min_unique_sources": r.min_unique_sources,
        "signal_window_minutes": r.signal_window_minutes,
        "categories": _safe_json(r.categories),
        "regions": _safe_json(r.regions),
        "required_patterns": _safe_json(r.required_patterns),
        "delivery_channels": _safe_json(r.delivery_channels),
        "cooldown_minutes": r.cooldown_minutes,
        "max_alerts_per_hour": r.max_alerts_per_hour,
    }


def _safe_json(value) -> list:
    if isinstance(value, list):
        return value
    if isinstance(value, str):
        try:
            return json.loads(value)
        except (json.JSONDecodeError, TypeError):
            return []
    return []
