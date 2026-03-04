"""Signal Correlation Engine.

Detects when multiple independent OSINT sources converge on the same
region/topic within a short timeframe — the core of early warning.
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.intelligence_item import IntelligenceItem
from app.services.precursor_patterns import PatternMatch, PrecursorPatternMatcher

logger = logging.getLogger(__name__)

# Region normalization
REGION_NORMALIZE = {
    "Middle East": "middle_east",
    "middle_east": "middle_east",
    "Europe": "europe",
    "europe": "europe",
    "Asia": "asia",
    "asia": "asia",
    "Africa": "africa",
    "africa": "africa",
    "Americas": "americas",
    "americas": "americas",
    "North America": "north_america",
    "north_america": "north_america",
    "Oceania": "oceania",
    "oceania": "oceania",
    "global": "global",
    "central_america": "americas",
}

# Cross-reference: if an item from another region mentions these keywords,
# also attribute it to the target region
REGION_KEYWORD_MAP = {
    "middle_east": [
        "iran", "israel", "syria", "iraq", "yemen", "lebanon",
        "gaza", "hezbollah", "hamas", "irgc", "persian gulf",
        "strait of hormuz", "red sea", "houthi",
    ],
    "europe": [
        "ukraine", "russia", "nato", "donbas", "crimea", "baltic",
        "moscow", "kyiv", "kharkiv", "wagner",
    ],
    "asia": [
        "china", "taiwan", "korea", "south china sea", "philippines",
        "xi jinping", "beijing", "pyongyang",
    ],
    "africa": [
        "sahel", "mali", "niger", "sudan", "ethiopia", "somalia",
        "nigeria", "boko haram", "wagner africa",
    ],
    "americas": [
        "venezuela", "brazil crisis", "mexico cartel", "colombia",
        "ecuador", "cartel", "southcom", "narco", "drug trafficking",
        "peru", "bolivia", "central america", "panama canal",
        "intervention", "joint operation", "military operation",
    ],
    "north_america": [
        "pentagon", "white house", "executive order",
        "southcom", "centcom", "africom", "homeland security",
        "national guard", "fema", "us military",
    ],
}


@dataclass
class CorrelationResult:
    """Result of correlating signals in a region."""
    region: str
    correlation_score: float  # 0-100
    items: list[dict]
    signal_count_1h: int
    signal_count_6h: int
    signal_count_24h: int
    unique_sources_1h: int
    unique_sources_6h: int
    avg_sentiment_1h: float
    max_priority_1h: float
    source_types: list[str]
    pattern_matches: list[PatternMatch] = field(default_factory=list)
    dominant_category: str = ""
    countries: list[str] = field(default_factory=list)
    keywords: list[str] = field(default_factory=list)


class SignalCorrelator:
    """Detects convergence of multiple OSINT sources on the same event/region."""

    MIN_CORRELATION_SIGNALS = 3
    MIN_UNIQUE_SOURCES = 2

    def __init__(self):
        self._pattern_matcher = PrecursorPatternMatcher()

    async def correlate(self, db: AsyncSession) -> list[CorrelationResult]:
        now = datetime.utcnow()
        cutoff_24h = now - timedelta(hours=24)

        # Fetch all non-stale items from last 24h
        stmt = (
            select(IntelligenceItem)
            .where(
                IntelligenceItem.is_stale == False,
                IntelligenceItem.created_at >= cutoff_24h,
            )
            .order_by(IntelligenceItem.created_at.desc())
        )
        result = await db.execute(stmt)
        items = result.scalars().all()

        if not items:
            return []

        # Convert to dicts for processing
        item_dicts = []
        for item in items:
            item_dicts.append({
                "id": item.id,
                "source": item.source,
                "title": item.title,
                "summary": item.summary,
                "category": item.category,
                "region": item.region,
                "country": item.country,
                "tags": item.tags,
                "sentiment_score": item.sentiment_score,
                "priority_score": item.priority_score,
                "created_at": item.created_at,
            })

        # Group by normalized region (with cross-referencing)
        region_groups: dict[str, list[dict]] = {}
        for item in item_dicts:
            regions = self._get_item_regions(item)
            for region in regions:
                region_groups.setdefault(region, []).append(item)

        # Compute correlation for each region
        results = []
        cutoff_1h = now - timedelta(hours=1)
        cutoff_6h = now - timedelta(hours=6)

        for region, group_items in region_groups.items():
            if len(group_items) < self.MIN_CORRELATION_SIGNALS:
                continue

            # Compute time-windowed stats
            items_1h = [i for i in group_items if i["created_at"] >= cutoff_1h]
            items_6h = [i for i in group_items if i["created_at"] >= cutoff_6h]

            sources_1h = set(i["source"] for i in items_1h)
            sources_6h = set(i["source"] for i in items_6h)
            sources_24h = set(i["source"] for i in group_items)

            if len(sources_24h) < self.MIN_UNIQUE_SOURCES:
                continue

            # Compute metrics
            sentiments_1h = [i["sentiment_score"] for i in items_1h] if items_1h else [0]
            priorities_1h = [i["priority_score"] for i in items_1h] if items_1h else [0]
            avg_sentiment_1h = sum(sentiments_1h) / len(sentiments_1h)
            max_priority_1h = max(priorities_1h)

            # Compute correlation score
            score = self._compute_score(
                signal_count_1h=len(items_1h),
                signal_count_6h=len(items_6h),
                signal_count_24h=len(group_items),
                unique_sources_1h=len(sources_1h),
                unique_sources_6h=len(sources_6h),
                avg_sentiment=avg_sentiment_1h,
                avg_priority=sum(priorities_1h) / len(priorities_1h) if priorities_1h else 0,
            )

            # Match precursor patterns
            pattern_matches = self._pattern_matcher.match_patterns(group_items, region)

            # Boost score if patterns match
            if pattern_matches:
                best_pattern = max(pattern_matches, key=lambda p: p.confidence)
                pattern_bonus = best_pattern.confidence * 15  # up to +15
                score = min(100, score + pattern_bonus)

            # Determine dominant category
            category_counts: dict[str, int] = {}
            for item in group_items:
                cat = item.get("category", "general")
                category_counts[cat] = category_counts.get(cat, 0) + 1
            dominant_category = max(category_counts, key=category_counts.get) if category_counts else ""

            # Extract countries mentioned
            countries = list(set(
                item["country"] for item in group_items
                if item.get("country")
            ))

            # Extract top keywords from titles
            keywords = self._extract_keywords(group_items)

            results.append(CorrelationResult(
                region=region,
                correlation_score=score,
                items=group_items,
                signal_count_1h=len(items_1h),
                signal_count_6h=len(items_6h),
                signal_count_24h=len(group_items),
                unique_sources_1h=len(sources_1h),
                unique_sources_6h=len(sources_6h),
                avg_sentiment_1h=avg_sentiment_1h,
                max_priority_1h=max_priority_1h,
                source_types=sorted(sources_24h),
                pattern_matches=pattern_matches,
                dominant_category=dominant_category,
                countries=countries[:10],
                keywords=keywords[:15],
            ))

        # Sort by score descending
        results.sort(key=lambda r: r.correlation_score, reverse=True)
        if results:
            logger.info(
                f"Signal Correlator: {len(results)} regional correlations "
                f"(top: {results[0].region}={results[0].correlation_score:.0f})"
            )
        else:
            logger.info("Signal Correlator: 0 regional correlations")
        return results

    def _get_item_regions(self, item: dict) -> list[str]:
        """Get all regions an item belongs to (primary + cross-referenced)."""
        regions = set()

        # Primary region
        primary = REGION_NORMALIZE.get(item.get("region", ""), "")
        if primary:
            regions.add(primary)

        # Cross-reference: check if item text mentions keywords for other regions
        text = f"{item.get('title', '')} {item.get('summary', '')}".lower()
        for region, keywords in REGION_KEYWORD_MAP.items():
            if any(kw in text for kw in keywords):
                regions.add(region)

        return list(regions) if regions else ["global"]

    def _compute_score(
        self,
        signal_count_1h: int,
        signal_count_6h: int,
        signal_count_24h: int,
        unique_sources_1h: int,
        unique_sources_6h: int,
        avg_sentiment: float,
        avg_priority: float,
    ) -> float:
        """Compute correlation score (0-100)."""
        # 1. Signal density (0-30)
        if signal_count_6h >= 12:
            density = 30
        elif signal_count_6h >= 8:
            density = 25
        elif signal_count_6h >= 5:
            density = 20
        elif signal_count_6h >= 3:
            density = 15
        else:
            density = signal_count_6h * 3

        # 2. Source diversity (0-25)
        if unique_sources_6h >= 7:
            diversity = 25
        elif unique_sources_6h >= 5:
            diversity = 20
        elif unique_sources_6h >= 3:
            diversity = 15
        elif unique_sources_6h >= 2:
            diversity = 10
        else:
            diversity = 5

        # 3. Sentiment convergence (0-20) — strong negative = higher score
        abs_sentiment = abs(avg_sentiment)
        if abs_sentiment >= 0.6:
            sentiment_score = 20
        elif abs_sentiment >= 0.4:
            sentiment_score = 15
        elif abs_sentiment >= 0.2:
            sentiment_score = 10
        else:
            sentiment_score = 5

        # 4. Priority concentration (0-15)
        if avg_priority >= 70:
            priority_score = 15
        elif avg_priority >= 50:
            priority_score = 10
        elif avg_priority >= 30:
            priority_score = 5
        else:
            priority_score = 0

        # 5. Acceleration bonus (0-10) — more signals in 1h than expected
        expected_1h = signal_count_6h / 6.0 if signal_count_6h > 0 else 0
        if expected_1h > 0 and signal_count_1h > 0:
            acceleration = signal_count_1h / expected_1h
            if acceleration >= 2.0:
                accel_bonus = 10
            elif acceleration >= 1.5:
                accel_bonus = 7
            elif acceleration >= 1.2:
                accel_bonus = 4
            else:
                accel_bonus = 0
        else:
            accel_bonus = 0

        return min(100, density + diversity + sentiment_score + priority_score + accel_bonus)

    def _extract_keywords(self, items: list[dict], top_n: int = 15) -> list[str]:
        """Extract most frequent meaningful words from item titles."""
        stop_words = {
            "the", "a", "an", "in", "on", "at", "to", "for", "of", "and",
            "or", "is", "are", "was", "were", "be", "been", "being",
            "has", "have", "had", "do", "does", "did", "will", "would",
            "could", "should", "may", "might", "shall", "can",
            "this", "that", "these", "those", "it", "its", "with",
            "from", "by", "as", "not", "no", "but", "if", "than",
            "so", "up", "out", "about", "into", "over", "after",
        }
        word_counts: dict[str, int] = {}
        for item in items:
            words = item.get("title", "").lower().split()
            for word in words:
                word = word.strip(".,;:!?()[]\"'")
                if len(word) >= 3 and word not in stop_words:
                    word_counts[word] = word_counts.get(word, 0) + 1

        sorted_words = sorted(word_counts.items(), key=lambda x: x[1], reverse=True)
        return [w for w, _ in sorted_words[:top_n]]
