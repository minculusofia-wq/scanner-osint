"""Alert Delivery — Discord webhook embeds.

Sends color-coded alerts with rich context: signals, sources, patterns, markets.
"""

import hashlib
import hmac
import json
import logging
from datetime import datetime

import httpx

from app.schemas.intelligence import AlertConfigSchema
from app.services.escalation_engine import EscalationEvent

logger = logging.getLogger(__name__)

# Discord embed color by severity
LEVEL_COLORS = {
    "stable": 0x2ECC71,       # green
    "concerning": 0xF1C40F,   # yellow
    "elevated": 0xE67E22,     # orange
    "critical": 0xE74C3C,     # red
    "crisis": 0x8B0000,       # dark red
}

LEVEL_EMOJI = {
    "stable": "",
    "concerning": "",
    "elevated": "",
    "critical": "",
    "crisis": "",
}


class AlertDelivery:
    """Dispatches alerts to configured channels."""

    async def send_discord(
        self,
        webhook_url: str,
        event: EscalationEvent,
        title: str,
        message: str,
    ) -> bool:
        if not webhook_url:
            logger.warning("Discord webhook URL not configured")
            return False

        emoji = LEVEL_EMOJI.get(event.new_level, "")
        color = LEVEL_COLORS.get(event.new_level, 0x95A5A6)

        # Build fields
        fields = []

        fields.append({
            "name": "Transition",
            "value": f"`{event.old_level.upper()}` → `{event.new_level.upper()}`",
            "inline": True,
        })
        fields.append({
            "name": "Score",
            "value": f"**{event.escalation_score:.0f}**/100",
            "inline": True,
        })
        fields.append({
            "name": "Région",
            "value": event.region.replace("_", " ").title(),
            "inline": True,
        })

        if event.signal_count_1h > 0 or event.signal_count_6h > 0:
            fields.append({
                "name": "Signaux",
                "value": (
                    f"1h: **{event.signal_count_1h}** | "
                    f"6h: **{event.signal_count_6h}** | "
                    f"24h: **{event.signal_count_24h}**"
                ),
                "inline": False,
            })

        if event.unique_sources_1h > 0:
            fields.append({
                "name": "Sources (1h)",
                "value": f"**{event.unique_sources_1h}** sources uniques",
                "inline": True,
            })

        if event.contributing_source_types:
            sources_str = ", ".join(
                s.replace("_", " ").title()
                for s in event.contributing_source_types[:8]
            )
            fields.append({
                "name": "Types de sources",
                "value": sources_str,
                "inline": False,
            })

        if event.matched_patterns:
            patterns_str = "\n".join(
                f"• `{p}`" for p in event.matched_patterns[:5]
            )
            fields.append({
                "name": "Patterns précurseurs",
                "value": patterns_str,
                "inline": False,
            })

        if event.countries:
            fields.append({
                "name": "Pays",
                "value": ", ".join(event.countries[:8]),
                "inline": True,
            })

        if event.keywords:
            kw_str = ", ".join(event.keywords[:10])
            fields.append({
                "name": "Mots-clés",
                "value": kw_str,
                "inline": False,
            })

        if event.linked_market_questions:
            markets_str = "\n".join(
                f"• {q}" for q in event.linked_market_questions[:5]
            )
            fields.append({
                "name": "Marchés Polymarket liés",
                "value": markets_str,
                "inline": False,
            })

        embed = {
            "title": f"{emoji} {title}",
            "description": message,
            "color": color,
            "fields": fields,
            "footer": {"text": "Scanner OSINT — Système d'Alerte Précoce"},
            "timestamp": datetime.utcnow().isoformat(),
        }

        payload = {
            "username": "Scanner OSINT",
            "embeds": [embed],
        }

        try:
            async with httpx.AsyncClient(timeout=15) as client:
                resp = await client.post(webhook_url, json=payload)
            if resp.status_code in (200, 204):
                logger.info(f"Discord alert sent: {title}")
                return True
            else:
                logger.error(
                    f"Discord webhook failed: {resp.status_code} {resp.text}"
                )
                return False
        except Exception as e:
            logger.error(f"Discord delivery error: {e}")
            return False

    async def send_webhook(
        self,
        webhook_url: str,
        webhook_secret: str,
        event: EscalationEvent,
        title: str,
        message: str,
    ) -> bool:
        """Send a generic webhook POST with HMAC signature."""
        if not webhook_url:
            return False

        payload = {
            "title": title,
            "message": message,
            "severity": event.new_level,
            "region": event.region,
            "category": event.category,
            "escalation_score": event.escalation_score,
            "old_level": event.old_level,
            "new_level": event.new_level,
            "signal_count_1h": event.signal_count_1h,
            "signal_count_6h": event.signal_count_6h,
            "unique_sources_1h": event.unique_sources_1h,
            "matched_patterns": event.matched_patterns,
            "contributing_source_types": event.contributing_source_types,
            "countries": event.countries,
            "keywords": event.keywords,
            "timestamp": datetime.utcnow().isoformat(),
        }

        body = json.dumps(payload)
        headers = {"Content-Type": "application/json"}

        if webhook_secret:
            signature = hmac.HMAC(
                webhook_secret.encode(), body.encode(), hashlib.sha256
            ).hexdigest()
            headers["X-Signature-256"] = f"sha256={signature}"

        try:
            async with httpx.AsyncClient(timeout=15) as client:
                resp = await client.post(
                    webhook_url, content=body, headers=headers
                )
            if resp.status_code < 300:
                logger.info(f"Webhook alert sent: {title}")
                return True
            else:
                logger.error(f"Webhook failed: {resp.status_code}")
                return False
        except Exception as e:
            logger.error(f"Webhook delivery error: {e}")
            return False

    async def send_test_alert(self, config: AlertConfigSchema) -> dict:
        """Send a test alert to configured channels."""
        test_event = EscalationEvent(
            tracker_id=0,
            tracker_name="Test Alert",
            region="global",
            category="test",
            old_level="stable",
            new_level="elevated",
            escalation_score=55.0,
            signal_count_1h=5,
            signal_count_6h=12,
            signal_count_24h=25,
            unique_sources_1h=4,
            avg_sentiment_1h=-0.45,
            matched_patterns=["test_pattern"],
            contributing_source_types=["gdelt", "newsdata", "reddit"],
            countries=["Test Country"],
            keywords=["test", "alert", "verification"],
            linked_market_ids=[],
            linked_market_questions=[],
            is_upgrade=True,
        )

        results = {}

        if config.discord_enabled and config.discord_webhook_url:
            results["discord"] = await self.send_discord(
                config.discord_webhook_url,
                test_event,
                "TEST — Système d'Alerte Précoce",
                "Ceci est une alerte de test. Si vous recevez ce message, "
                "la connexion Discord est fonctionnelle.",
            )

        if config.webhook_enabled and config.webhook_url:
            results["webhook"] = await self.send_webhook(
                config.webhook_url,
                config.webhook_secret,
                test_event,
                "TEST — Système d'Alerte Précoce",
                "Alerte de test — connexion webhook vérifiée.",
            )

        return results
