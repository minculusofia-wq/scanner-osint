"""Escalation Engine.

State machine that tracks threat levels per region/category.
Levels: stable → concerning → elevated → critical → crisis

Detects transitions (the trigger for alerts).
"""

import json
import logging
from dataclasses import dataclass
from datetime import datetime, timedelta

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.escalation_tracker import EscalationTracker
from app.services.signal_correlator import CorrelationResult

logger = logging.getLogger(__name__)

LEVELS = ("stable", "concerning", "elevated", "critical", "crisis")
LEVEL_THRESHOLDS = {
    "stable": (0, 20),
    "concerning": (20, 40),
    "elevated": (40, 60),
    "critical": (60, 80),
    "crisis": (80, 100),
}

DECAY_RATE_PER_HOUR = 5.0
AUTO_RESOLVE_HOURS = 12


def _score_to_level(score: float) -> str:
    for level, (low, high) in LEVEL_THRESHOLDS.items():
        if low <= score < high:
            return level
    return "crisis" if score >= 80 else "stable"


@dataclass
class EscalationEvent:
    """Represents a level transition on a tracker."""
    tracker_id: int
    tracker_name: str
    region: str
    category: str
    old_level: str
    new_level: str
    escalation_score: float
    signal_count_1h: int
    signal_count_6h: int
    signal_count_24h: int
    unique_sources_1h: int
    avg_sentiment_1h: float
    matched_patterns: list[str]
    contributing_source_types: list[str]
    countries: list[str]
    keywords: list[str]
    linked_market_ids: list[str]
    linked_market_questions: list[str]
    is_upgrade: bool  # True = escalation up, False = de-escalation


class EscalationEngine:
    """Manages escalation trackers and detects level transitions."""

    async def update_trackers(
        self, db: AsyncSession, correlations: list[CorrelationResult]
    ) -> list[EscalationEvent]:
        now = datetime.utcnow()
        events: list[EscalationEvent] = []

        # Load active trackers
        stmt = select(EscalationTracker).where(EscalationTracker.is_active == True)
        result = await db.execute(stmt)
        active_trackers = {t.region: t for t in result.scalars().all()}

        # Track which regions got updated this cycle
        updated_regions: set[str] = set()

        for corr in correlations:
            region = corr.region
            updated_regions.add(region)

            tracker = active_trackers.get(region)

            if tracker is None:
                # Create new tracker
                tracker = EscalationTracker(
                    name=self._generate_name(corr),
                    category=corr.dominant_category,
                    region=region,
                    countries=json.dumps(corr.countries),
                    keywords=json.dumps(corr.keywords),
                    escalation_level="stable",
                    escalation_score=corr.correlation_score,
                    previous_level="stable",
                    signal_count_1h=corr.signal_count_1h,
                    signal_count_6h=corr.signal_count_6h,
                    signal_count_24h=corr.signal_count_24h,
                    unique_sources_1h=corr.unique_sources_1h,
                    avg_sentiment_1h=corr.avg_sentiment_1h,
                    max_priority_1h=corr.max_priority_1h,
                    contributing_source_types=json.dumps(corr.source_types),
                    matched_patterns=json.dumps(
                        [p.pattern.name for p in corr.pattern_matches]
                    ),
                    key_headlines=json.dumps(
                        self._extract_headlines(corr), ensure_ascii=False
                    ),
                    linked_market_ids="[]",
                    linked_market_questions="[]",
                    is_active=True,
                    created_at=now,
                    updated_at=now,
                )
                db.add(tracker)
                await db.flush()  # get tracker.id
                active_trackers[region] = tracker

            old_level = tracker.escalation_level
            old_score = tracker.escalation_score

            # Update tracker with new correlation data
            # Use max of current score and new correlation score (with some blending)
            # This prevents a single low cycle from dropping the score too fast
            new_score = max(corr.correlation_score, old_score * 0.7 + corr.correlation_score * 0.3)
            new_score = min(100.0, new_score)

            new_level = _score_to_level(new_score)

            # Update fields
            tracker.escalation_score = new_score
            tracker.escalation_level = new_level
            tracker.signal_count_1h = corr.signal_count_1h
            tracker.signal_count_6h = corr.signal_count_6h
            tracker.signal_count_24h = corr.signal_count_24h
            tracker.unique_sources_1h = corr.unique_sources_1h
            tracker.avg_sentiment_1h = corr.avg_sentiment_1h
            tracker.max_priority_1h = corr.max_priority_1h
            tracker.contributing_source_types = json.dumps(corr.source_types)
            tracker.countries = json.dumps(corr.countries)
            tracker.keywords = json.dumps(corr.keywords)
            tracker.key_headlines = json.dumps(
                self._extract_headlines(corr), ensure_ascii=False
            )
            tracker.updated_at = now

            # Merge pattern matches
            existing_patterns = json.loads(tracker.matched_patterns or "[]")
            new_patterns = [p.pattern.name for p in corr.pattern_matches]
            all_patterns = list(set(existing_patterns + new_patterns))
            tracker.matched_patterns = json.dumps(all_patterns)

            # Update name if category changed
            if corr.dominant_category and corr.dominant_category != tracker.category:
                tracker.category = corr.dominant_category
                tracker.name = self._generate_name(corr)

            # Detect level transition
            if new_level != old_level:
                tracker.previous_level = old_level
                tracker.level_changed_at = now

                is_upgrade = LEVELS.index(new_level) > LEVELS.index(old_level)

                event = EscalationEvent(
                    tracker_id=tracker.id,
                    tracker_name=tracker.name,
                    region=region,
                    category=tracker.category,
                    old_level=old_level,
                    new_level=new_level,
                    escalation_score=new_score,
                    signal_count_1h=corr.signal_count_1h,
                    signal_count_6h=corr.signal_count_6h,
                    signal_count_24h=corr.signal_count_24h,
                    unique_sources_1h=corr.unique_sources_1h,
                    avg_sentiment_1h=corr.avg_sentiment_1h,
                    matched_patterns=all_patterns,
                    contributing_source_types=corr.source_types,
                    countries=corr.countries,
                    keywords=corr.keywords,
                    linked_market_ids=json.loads(tracker.linked_market_ids or "[]"),
                    linked_market_questions=json.loads(tracker.linked_market_questions or "[]"),
                    is_upgrade=is_upgrade,
                )
                events.append(event)

                logger.warning(
                    f"ESCALATION {'UP' if is_upgrade else 'DOWN'}: "
                    f"{region} {old_level} -> {new_level} "
                    f"(score={new_score:.0f}, signals_1h={corr.signal_count_1h}, "
                    f"sources={corr.unique_sources_1h}, "
                    f"patterns={all_patterns})"
                )

        # Decay trackers that had no new correlation this cycle
        await self._decay_inactive_trackers(
            db, active_trackers, updated_regions, now, events
        )

        await db.commit()

        if events:
            logger.info(
                f"Escalation Engine: {len(events)} level transitions "
                f"({sum(1 for e in events if e.is_upgrade)} up, "
                f"{sum(1 for e in events if not e.is_upgrade)} down)"
            )

        return events

    async def _decay_inactive_trackers(
        self,
        db: AsyncSession,
        active_trackers: dict[str, EscalationTracker],
        updated_regions: set[str],
        now: datetime,
        events: list[EscalationEvent],
    ):
        """Apply score decay to trackers that received no new signals."""
        for region, tracker in active_trackers.items():
            if region in updated_regions:
                continue

            # Calculate hours since last update
            hours_since_update = (now - tracker.updated_at).total_seconds() / 3600.0
            decay = DECAY_RATE_PER_HOUR * hours_since_update

            old_level = tracker.escalation_level
            old_score = tracker.escalation_score
            new_score = max(0.0, old_score - decay)
            new_level = _score_to_level(new_score)

            tracker.escalation_score = new_score
            tracker.escalation_level = new_level
            tracker.updated_at = now

            # Auto-resolve: if stable for 12h+ with no signals
            if (
                new_level == "stable"
                and tracker.signal_count_1h == 0
                and hours_since_update >= AUTO_RESOLVE_HOURS
            ):
                tracker.is_active = False
                tracker.resolved_at = now
                logger.info(
                    f"Auto-resolved tracker: {tracker.name} ({region}) "
                    f"— stable for {hours_since_update:.1f}h"
                )
                continue

            # Detect de-escalation transition
            if new_level != old_level:
                tracker.previous_level = old_level
                tracker.level_changed_at = now

                events.append(EscalationEvent(
                    tracker_id=tracker.id,
                    tracker_name=tracker.name,
                    region=region,
                    category=tracker.category,
                    old_level=old_level,
                    new_level=new_level,
                    escalation_score=new_score,
                    signal_count_1h=0,
                    signal_count_6h=tracker.signal_count_6h,
                    signal_count_24h=tracker.signal_count_24h,
                    unique_sources_1h=0,
                    avg_sentiment_1h=tracker.avg_sentiment_1h,
                    matched_patterns=json.loads(tracker.matched_patterns or "[]"),
                    contributing_source_types=json.loads(
                        tracker.contributing_source_types or "[]"
                    ),
                    countries=json.loads(tracker.countries or "[]"),
                    keywords=json.loads(tracker.keywords or "[]"),
                    linked_market_ids=json.loads(tracker.linked_market_ids or "[]"),
                    linked_market_questions=json.loads(
                        tracker.linked_market_questions or "[]"
                    ),
                    is_upgrade=False,
                ))

    @staticmethod
    def _extract_headlines(corr: CorrelationResult) -> list[dict]:
        """Extract top 5 headlines from correlation items, sorted by priority."""
        items_with_title = [i for i in corr.items if i.get("title")]
        sorted_items = sorted(
            items_with_title,
            key=lambda x: x.get("priority_score", 0),
            reverse=True,
        )
        # Deduplicate by title (keep highest priority)
        seen_titles: set[str] = set()
        headlines = []
        for item in sorted_items:
            title = item["title"].strip()
            if title.lower() in seen_titles:
                continue
            seen_titles.add(title.lower())
            headlines.append({
                "title": title[:200],
                "source": item.get("source", ""),
            })
            if len(headlines) >= 5:
                break
        return headlines

    def _generate_name(self, corr: CorrelationResult) -> str:
        """Generate a human-readable tracker name."""
        region_labels = {
            "middle_east": "Middle East",
            "europe": "Europe",
            "asia": "Asia-Pacific",
            "africa": "Africa",
            "americas": "Americas",
            "north_america": "North America",
            "oceania": "Oceania",
            "global": "Global",
        }
        region_label = region_labels.get(corr.region, corr.region.title())
        category = (corr.dominant_category or "general").replace("_", " ").title()
        return f"{region_label} — {category}"
