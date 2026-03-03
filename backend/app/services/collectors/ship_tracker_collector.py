import logging
import re
from datetime import datetime

import feedparser
import httpx

from .base_collector import BaseCollector

logger = logging.getLogger(__name__)

# Strategic maritime chokepoints and their monitoring sources
MARITIME_ZONES = [
    {
        "name": "Suez Canal",
        "region": "middle_east",
        "keywords": ["suez", "canal", "red sea", "bab el-mandeb"],
        "strategic_value": 0.9,
    },
    {
        "name": "Strait of Hormuz",
        "region": "middle_east",
        "keywords": ["hormuz", "persian gulf", "iran", "oil tanker"],
        "strategic_value": 0.95,
    },
    {
        "name": "Strait of Malacca",
        "region": "asia",
        "keywords": ["malacca", "singapore strait", "south china sea"],
        "strategic_value": 0.8,
    },
    {
        "name": "Bosphorus",
        "region": "europe",
        "keywords": ["bosphorus", "dardanelles", "turkish straits", "black sea"],
        "strategic_value": 0.85,
    },
    {
        "name": "Taiwan Strait",
        "region": "asia",
        "keywords": ["taiwan strait", "formosa", "pla navy"],
        "strategic_value": 0.9,
    },
    {
        "name": "Panama Canal",
        "region": "central_america",
        "keywords": ["panama canal", "panama"],
        "strategic_value": 0.7,
    },
]

# RSS/news feeds for maritime intelligence
MARITIME_FEEDS = [
    "https://gcaptain.com/feed/",  # Major maritime news
    "https://splash247.com/feed/",  # Shipping news
    "https://www.hellenicshippingnews.com/feed/",  # Shipping industry
]

# High-priority maritime keywords
HIGH_PRIORITY_KEYWORDS = [
    "military vessel", "warship", "naval", "blockade", "seizure",
    "piracy", "attack", "missile", "drone strike", "oil tanker",
    "lng carrier", "sanctions", "detained", "impounded",
    "military exercise", "carrier group", "destroyer", "submarine",
    "strait closed", "canal blocked", "disruption",
]

MEDIUM_PRIORITY_KEYWORDS = [
    "reroute", "diversion", "delay", "congestion",
    "inspection", "security zone", "escort", "patrol",
    "fleet", "deployment", "port call",
]


class ShipTrackerCollector(BaseCollector):
    """Monitors maritime activity in strategic chokepoints via RSS feeds and public data."""

    SOURCE_NAME = "ship_tracker"

    async def collect(self, config: dict) -> list[dict]:
        items = []

        async with httpx.AsyncClient(
            timeout=15,
            headers={"User-Agent": "ScannerOSINT/1.0 Maritime Monitor"},
        ) as client:
            # Collect from maritime RSS feeds
            for feed_url in MARITIME_FEEDS:
                try:
                    resp = await client.get(feed_url)
                    if resp.status_code != 200:
                        continue

                    feed = feedparser.parse(resp.text)

                    for entry in feed.entries[:15]:
                        title = entry.get("title", "").strip()
                        if not title:
                            continue

                        summary = entry.get("summary", entry.get("description", "")).strip()
                        summary = _strip_html(summary)[:500]
                        link = entry.get("link", "")

                        text_lower = f"{title} {summary}".lower()

                        # Check if related to our monitored zones (pick highest strategic value)
                        matched_zone = None
                        best_value = 0
                        for zone in MARITIME_ZONES:
                            for kw in zone["keywords"]:
                                if kw in text_lower and zone["strategic_value"] > best_value:
                                    matched_zone = zone
                                    best_value = zone["strategic_value"]
                                    break

                        if not matched_zone:
                            # Check for general maritime security keywords
                            has_priority_kw = any(kw in text_lower for kw in HIGH_PRIORITY_KEYWORDS)
                            if not has_priority_kw:
                                continue
                            # General maritime security item
                            matched_zone = {
                                "name": "Global Maritime",
                                "region": "global",
                                "strategic_value": 0.6,
                            }

                        # Calculate relevance
                        relevance = 0.5

                        for kw in HIGH_PRIORITY_KEYWORDS:
                            if kw in text_lower:
                                relevance = max(relevance, 0.85)
                                break

                        if relevance < 0.85:
                            for kw in MEDIUM_PRIORITY_KEYWORDS:
                                if kw in text_lower:
                                    relevance = max(relevance, 0.65)
                                    break

                        # Boost by zone strategic value (additive, not multiplicative)
                        relevance = min(1.0, relevance + (matched_zone["strategic_value"] - 0.5) * 0.2)

                        # Parse date
                        published = None
                        if hasattr(entry, "published_parsed") and entry.published_parsed:
                            try:
                                published = datetime(*entry.published_parsed[:6])
                            except (ValueError, TypeError):
                                pass

                        items.append(self._make_item(
                            title=f"Maritime: {title}",
                            summary=summary,
                            url=link,
                            category="geopolitical",
                            region=matched_zone["region"],
                            tags=["maritime", "shipping", matched_zone["name"].lower().replace(" ", "_")],
                            raw_relevance=relevance,
                            published_at=published,
                            source_id=f"ship-{link[-60:]}",
                        ))

                except Exception as e:
                    logger.error(f"Ship Tracker {feed_url} error: {e}")

        logger.info(f"Ship Tracker: collected {len(items)} items")
        return items


def _strip_html(text: str) -> str:
    """Remove HTML tags from text."""
    clean = re.sub(r'<[^>]+>', '', text)
    clean = re.sub(r'\s+', ' ', clean)
    return clean.strip()
