"""Alert Evaluator.

Evaluates escalation events against alert rules, applies cooldown/rate-limiting,
builds messages, and dispatches via AlertDelivery.
"""

import json
import logging
from datetime import datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.alert_history import AlertHistory
from app.models.alert_rule import AlertRule
from app.schemas.intelligence import AlertConfigSchema
from app.services.alert_delivery import AlertDelivery
from app.services.escalation_engine import EscalationEvent, LEVELS

logger = logging.getLogger(__name__)


class AlertEvaluator:
    """Evaluates escalation events and dispatches alerts."""

    def __init__(self):
        self._delivery = AlertDelivery()

    async def evaluate(
        self,
        db: AsyncSession,
        events: list[EscalationEvent],
        config: AlertConfigSchema,
    ) -> list[AlertHistory]:
        """Evaluate events against rules and send alerts."""
        if not config.alerts_enabled:
            return []

        # Only process upward escalations
        upgrade_events = [e for e in events if e.is_upgrade]
        if not upgrade_events:
            return []

        # Check quiet hours
        if self._is_quiet_hours(config):
            logger.info("Alert suppressed: quiet hours active")
            return []

        # Check global rate limit
        global_count = await self._count_recent_alerts(db, minutes=60)
        if global_count >= config.max_alerts_per_hour:
            logger.warning(
                f"Global rate limit reached: {global_count}/{config.max_alerts_per_hour} alerts/hour"
            )
            return []

        # Load active rules
        stmt = select(AlertRule).where(AlertRule.is_enabled == True)
        result = await db.execute(stmt)
        rules = result.scalars().all()

        # If no rules configured, use a default catch-all for elevated+
        if not rules:
            rules = [self._default_rule()]

        sent_alerts: list[AlertHistory] = []

        for event in upgrade_events:
            for rule in rules:
                if not self._matches_rule(event, rule):
                    continue

                # Check per-rule cooldown
                if await self._is_on_cooldown(db, rule, event):
                    continue

                # Check per-rule rate limit
                rule_count = await self._count_rule_alerts(
                    db, rule, minutes=60
                )
                max_per_hour = rule.max_alerts_per_hour if hasattr(rule, "max_alerts_per_hour") else 5
                if rule_count >= max_per_hour:
                    continue

                # Check global cooldown
                if await self._global_cooldown_active(db, config, event):
                    continue

                # Build and send
                title, message = self._build_message(event)
                channels_sent = await self._dispatch(config, event, title, message)

                if channels_sent:
                    alert = AlertHistory(
                        alert_rule_id=rule.id if hasattr(rule, "id") and rule.id else None,
                        escalation_tracker_id=event.tracker_id,
                        title=title,
                        message=message,
                        severity=event.new_level,
                        escalation_level=event.new_level,
                        region=event.region,
                        category=event.category,
                        trigger_signal_count=event.signal_count_1h + event.signal_count_6h,
                        trigger_source_types=json.dumps(event.contributing_source_types),
                        trigger_item_ids="[]",
                        matched_patterns=json.dumps(event.matched_patterns),
                        channels_sent=json.dumps(channels_sent),
                        delivery_status="sent",
                        linked_market_ids=json.dumps(event.linked_market_ids),
                        linked_market_questions=json.dumps(event.linked_market_questions),
                        created_at=datetime.utcnow(),
                    )
                    db.add(alert)
                    sent_alerts.append(alert)

                # One alert per event is enough (first matching rule wins)
                break

        if sent_alerts:
            await db.commit()
            logger.info(f"AlertEvaluator: sent {len(sent_alerts)} alerts")

        return sent_alerts

    def _matches_rule(self, event: EscalationEvent, rule) -> bool:
        """Check if an event matches a rule's conditions."""
        # Minimum escalation level
        min_level = getattr(rule, "min_escalation_level", "elevated")
        if LEVELS.index(event.new_level) < LEVELS.index(min_level):
            return False

        # Minimum priority (use escalation_score as proxy)
        min_priority = getattr(rule, "min_priority_score", 0)
        if event.escalation_score < min_priority:
            return False

        # Minimum signal count
        min_signals = getattr(rule, "min_signal_count", 0)
        total_signals = event.signal_count_1h + event.signal_count_6h
        if total_signals < min_signals:
            return False

        # Minimum unique sources
        min_sources = getattr(rule, "min_unique_sources", 0)
        if event.unique_sources_1h < min_sources:
            return False

        # Region filter
        rule_regions = self._parse_json_list(getattr(rule, "regions", "[]"))
        if rule_regions and event.region not in rule_regions:
            return False

        # Category filter
        rule_categories = self._parse_json_list(getattr(rule, "categories", "[]"))
        if rule_categories and event.category not in rule_categories:
            return False

        # Required patterns
        required = self._parse_json_list(getattr(rule, "required_patterns", "[]"))
        if required:
            if not any(p in event.matched_patterns for p in required):
                return False

        return True

    async def _is_on_cooldown(
        self, db: AsyncSession, rule, event: EscalationEvent
    ) -> bool:
        """Check if this rule+region combo is in cooldown."""
        cooldown_minutes = getattr(rule, "cooldown_minutes", 30)
        cutoff = datetime.utcnow() - timedelta(minutes=cooldown_minutes)
        rule_id = getattr(rule, "id", None)

        stmt = select(func.count(AlertHistory.id)).where(
            AlertHistory.created_at >= cutoff,
            AlertHistory.region == event.region,
        )
        if rule_id:
            stmt = stmt.where(AlertHistory.alert_rule_id == rule_id)

        result = await db.execute(stmt)
        count = result.scalar() or 0
        return count > 0

    async def _global_cooldown_active(
        self, db: AsyncSession, config: AlertConfigSchema, event: EscalationEvent
    ) -> bool:
        """Check global cooldown for same region."""
        cutoff = datetime.utcnow() - timedelta(minutes=config.global_cooldown_minutes)
        stmt = select(func.count(AlertHistory.id)).where(
            AlertHistory.created_at >= cutoff,
            AlertHistory.region == event.region,
        )
        result = await db.execute(stmt)
        count = result.scalar() or 0
        return count > 0

    async def _count_recent_alerts(self, db: AsyncSession, minutes: int) -> int:
        cutoff = datetime.utcnow() - timedelta(minutes=minutes)
        stmt = select(func.count(AlertHistory.id)).where(
            AlertHistory.created_at >= cutoff
        )
        result = await db.execute(stmt)
        return result.scalar() or 0

    async def _count_rule_alerts(
        self, db: AsyncSession, rule, minutes: int
    ) -> int:
        rule_id = getattr(rule, "id", None)
        if not rule_id:
            return 0
        cutoff = datetime.utcnow() - timedelta(minutes=minutes)
        stmt = select(func.count(AlertHistory.id)).where(
            AlertHistory.created_at >= cutoff,
            AlertHistory.alert_rule_id == rule_id,
        )
        result = await db.execute(stmt)
        return result.scalar() or 0

    def _is_quiet_hours(self, config: AlertConfigSchema) -> bool:
        if config.quiet_hours_start < 0 or config.quiet_hours_end < 0:
            return False
        current_hour = datetime.utcnow().hour
        start = config.quiet_hours_start
        end = config.quiet_hours_end
        if start <= end:
            return start <= current_hour < end
        else:
            return current_hour >= start or current_hour < end

    def _build_message(self, event: EscalationEvent) -> tuple[str, str]:
        """Build alert title and message body."""
        region_label = event.region.replace("_", " ").title()
        level_upper = event.new_level.upper()

        title = f"{level_upper}: {event.tracker_name}"

        parts = [
            f"**{region_label}** — Niveau d'escalade passe de "
            f"`{event.old_level}` a `{event.new_level}` "
            f"(score: {event.escalation_score:.0f}/100).",
        ]

        if event.signal_count_1h > 0:
            parts.append(
                f"{event.signal_count_1h} signaux dans la derniere heure, "
                f"{event.unique_sources_1h} sources independantes."
            )

        if event.matched_patterns:
            patterns_str = ", ".join(event.matched_patterns[:3])
            parts.append(f"Patterns precurseurs detectes: {patterns_str}")

        if event.countries:
            parts.append(f"Pays concernes: {', '.join(event.countries[:5])}")

        message = "\n\n".join(parts)
        return title, message

    async def _dispatch(
        self,
        config: AlertConfigSchema,
        event: EscalationEvent,
        title: str,
        message: str,
    ) -> list[str]:
        """Send to all configured channels."""
        channels_sent = []

        if config.discord_enabled and config.discord_webhook_url:
            ok = await self._delivery.send_discord(
                config.discord_webhook_url, event, title, message
            )
            if ok:
                channels_sent.append("discord")

        if config.webhook_enabled and config.webhook_url:
            ok = await self._delivery.send_webhook(
                config.webhook_url,
                config.webhook_secret,
                event,
                title,
                message,
            )
            if ok:
                channels_sent.append("webhook")

        return channels_sent

    def _parse_json_list(self, value) -> list[str]:
        if isinstance(value, list):
            return value
        if isinstance(value, str):
            try:
                parsed = json.loads(value)
                return parsed if isinstance(parsed, list) else []
            except (json.JSONDecodeError, TypeError):
                return []
        return []

    def _default_rule(self):
        """Return a default catch-all rule for elevated+ events."""

        class _DefaultRule:
            id = None
            min_escalation_level = "elevated"
            min_priority_score = 0
            min_signal_count = 3
            min_unique_sources = 2
            signal_window_minutes = 120
            categories = "[]"
            regions = "[]"
            required_patterns = "[]"
            cooldown_minutes = 30
            max_alerts_per_hour = 5

        return _DefaultRule()
