import logging
import re
from datetime import datetime

import feedparser
import httpx

from .base_collector import BaseCollector

logger = logging.getLogger(__name__)

# LiveUAMap RSS feeds for conflict monitoring (free, no key)
# These track real-time conflict events, airstrikes, troop movements
LIVEUAMAP_FEEDS = {
    "middle_east": {
        "url": "https://liveuamap.com/rss/middleeast",
        "region": "middle_east",
        "keywords_boost": ["iran", "israel", "strike", "missile", "irgc", "hezbollah", "hamas"],
    },
    "ukraine": {
        "url": "https://liveuamap.com/rss/ukraine",
        "region": "europe",
        "keywords_boost": ["offensive", "missile", "drone", "frontline", "kharkiv", "donbas"],
    },
    "syria": {
        "url": "https://liveuamap.com/rss/syria",
        "region": "middle_east",
        "keywords_boost": ["airstrike", "isis", "turkey", "kurds", "idlib"],
    },
    "africa": {
        "url": "https://liveuamap.com/rss/africa",
        "region": "africa",
        "keywords_boost": ["sahel", "wagner", "coup", "junta", "boko haram"],
    },
}

# Additional OSINT conflict RSS feeds (from @clement_molin thread and community)
OSINT_CONFLICT_FEEDS = [
    {
        "url": "https://www.understandingwar.org/feed",
        "name": "ISW (Institute for Study of War)",
        "region": "",
    },
    {
        "url": "https://www.crisisgroup.org/feed/rss",
        "name": "International Crisis Group",
        "region": "",
    },
]

HIGH_PRIORITY_KEYWORDS = [
    "airstrike", "missile", "nuclear", "chemical", "invasion",
    "ceasefire", "breakthrough", "encirclement", "surrender",
    "killed", "casualties", "captured", "evacuation", "blockade",
    "carrier strike", "bomber", "icbm", "ballistic", "cruise missile",
    "escalation", "retaliation", "declaration of war",
]

MEDIUM_PRIORITY_KEYWORDS = [
    "artillery", "drone", "offensive", "defensive", "shelling",
    "reinforcement", "deployment", "mobilization", "sanctions",
    "embargo", "humanitarian", "refugee", "displaced",
    "militia", "insurgent", "counteroffensive",
]


class LiveUAMapCollector(BaseCollector):
    """Collects real-time conflict events from LiveUAMap and OSINT RSS feeds."""

    SOURCE_NAME = "liveuamap"

    async def collect(self, config: dict) -> list[dict]:
        items = []

        async with httpx.AsyncClient(
            timeout=15,
            headers={"User-Agent": "ScannerOSINT/1.0 Conflict Monitor"},
        ) as client:
            # 1. LiveUAMap feeds
            for feed_name, feed_info in LIVEUAMAP_FEEDS.items():
                try:
                    resp = await client.get(feed_info["url"])
                    if resp.status_code != 200:
                        logger.warning(f"LiveUAMap {feed_name}: HTTP {resp.status_code}")
                        continue

                    feed = feedparser.parse(resp.text)
                    for entry in feed.entries[:20]:
                        item = self._parse_entry(entry, feed_info["region"], feed_info["keywords_boost"])
                        if item:
                            items.append(item)

                except Exception as e:
                    logger.error(f"LiveUAMap {feed_name} error: {e}")

            # 2. Additional OSINT conflict feeds
            for feed_info in OSINT_CONFLICT_FEEDS:
                try:
                    resp = await client.get(feed_info["url"])
                    if resp.status_code != 200:
                        continue

                    feed = feedparser.parse(resp.text)
                    for entry in feed.entries[:10]:
                        item = self._parse_entry(entry, feed_info["region"], [])
                        if item:
                            items.append(item)

                except Exception as e:
                    logger.error(f"OSINT feed {feed_info['name']} error: {e}")

        logger.info(f"LiveUAMap: collected {len(items)} conflict items")
        return items

    def _parse_entry(self, entry, region: str, boost_keywords: list[str]) -> dict | None:
        title = entry.get("title", "").strip()
        if not title:
            return None

        summary = entry.get("summary", entry.get("description", "")).strip()
        summary = _strip_html(summary)[:500]
        link = entry.get("link", "")

        text_lower = f"{title} {summary}".lower()

        # Calculate relevance
        relevance = 0.5

        for kw in HIGH_PRIORITY_KEYWORDS:
            if kw in text_lower:
                relevance = max(relevance, 0.9)
                break

        if relevance < 0.9:
            for kw in MEDIUM_PRIORITY_KEYWORDS:
                if kw in text_lower:
                    relevance = max(relevance, 0.7)
                    break

        # Boost for region-specific keywords
        for kw in boost_keywords:
            if kw in text_lower:
                relevance = min(1.0, relevance + 0.05)

        # Skip low-relevance items
        if relevance < 0.5:
            return None

        # Detect region from content if not set
        if not region:
            region = self._detect_region(text_lower)

        # Sentiment — conflict news is negative
        sentiment = -0.4
        if any(kw in text_lower for kw in ["ceasefire", "peace", "agreement", "withdrawal"]):
            sentiment = 0.2
        elif any(kw in text_lower for kw in ["nuclear", "chemical", "icbm", "escalation"]):
            sentiment = -0.9

        # Parse date
        published = None
        if hasattr(entry, "published_parsed") and entry.published_parsed:
            try:
                published = datetime(*entry.published_parsed[:6])
            except (ValueError, TypeError):
                pass

        tags = ["conflict"]
        if any(kw in text_lower for kw in ["missile", "airstrike", "bombing", "strike"]):
            tags.append("kinetic")
        if any(kw in text_lower for kw in ["nuclear", "chemical", "biological"]):
            tags.append("wmd")
        if any(kw in text_lower for kw in ["drone", "uav"]):
            tags.append("drone")

        return self._make_item(
            title=f"Conflict: {title}",
            summary=summary,
            url=link,
            category="conflict",
            region=region,
            tags=tags,
            raw_relevance=relevance,
            sentiment_score=sentiment,
            published_at=published,
            source_id=f"luam-{link[-60:]}" if link else f"luam-{title[:40]}",
        )

    def _detect_region(self, text: str) -> str:
        region_keywords = {
            "middle_east": ["iran", "israel", "syria", "iraq", "yemen", "lebanon", "gaza", "hezbollah", "hamas", "irgc"],
            "europe": ["ukraine", "russia", "nato", "donbas", "kharkiv", "crimea", "baltic"],
            "asia": ["china", "taiwan", "korea", "south china sea", "philippines", "india", "pakistan"],
            "africa": ["sahel", "mali", "niger", "sudan", "ethiopia", "somalia", "nigeria", "wagner"],
        }
        for region, keywords in region_keywords.items():
            if any(kw in text for kw in keywords):
                return region
        return ""


def _strip_html(text: str) -> str:
    clean = re.sub(r'<[^>]+>', '', text)
    clean = re.sub(r'\s+', ' ', clean)
    return clean.strip()
