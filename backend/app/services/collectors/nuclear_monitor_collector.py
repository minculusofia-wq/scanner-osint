import logging
import re
from datetime import datetime

import feedparser
import httpx

from .base_collector import BaseCollector

logger = logging.getLogger(__name__)

# Nuclear/Radiation monitoring sources (all free, no key)
# Inspired by SitDeck's nuclear monitoring layer and OSINT community
NUCLEAR_FEEDS = [
    {
        "url": "https://www.iaea.org/feeds/news",
        "name": "IAEA News",
        "keywords_boost": ["nuclear", "radiation", "enrichment", "iaea", "safeguards"],
    },
    {
        "url": "https://www.federalregister.gov/api/v1/documents.rss?conditions%5Bagencies%5D%5B%5D=nuclear-regulatory-commission",
        "name": "US NRC (Federal Register)",
        "keywords_boost": ["reactor", "nuclear", "radiation", "emergency"],
    },
]

# EPA RadNet — US radiation monitoring network (JSON API)
EPA_RADNET_URL = "https://www.epa.gov/enviro/radnet-csv-query-api"

# Nuclear-related high priority keywords
NUCLEAR_HIGH_PRIORITY = [
    "nuclear test", "nuclear weapon", "enrichment", "weapons-grade",
    "uranium", "plutonium", "centrifuge", "icbm", "nuclear warhead",
    "radiation leak", "meltdown", "nuclear accident", "radioactive",
    "nuclear threat", "nuclear deterrent", "nuclear posture",
    "nuclear deal", "jcpoa", "non-proliferation",
    "dirty bomb", "radiological",
]

NUCLEAR_MEDIUM_PRIORITY = [
    "nuclear power", "reactor", "spent fuel", "nuclear energy",
    "nuclear safety", "iaea inspection", "safeguards",
    "nuclear submarine", "nuclear carrier",
]

# Countries with nuclear programs of geopolitical interest
NUCLEAR_COUNTRIES = {
    "iran": {"region": "middle_east", "boost": 0.2},
    "north korea": {"region": "asia", "boost": 0.2},
    "dprk": {"region": "asia", "boost": 0.2},
    "russia": {"region": "europe", "boost": 0.15},
    "china": {"region": "asia", "boost": 0.15},
    "pakistan": {"region": "asia", "boost": 0.15},
    "india": {"region": "asia", "boost": 0.1},
    "israel": {"region": "middle_east", "boost": 0.15},
}


class NuclearMonitorCollector(BaseCollector):
    """Monitors nuclear/radiation events from IAEA, NRC, and OSINT feeds."""

    SOURCE_NAME = "nuclear_monitor"

    async def collect(self, config: dict) -> list[dict]:
        items = []

        async with httpx.AsyncClient(
            timeout=15,
            headers={"User-Agent": "ScannerOSINT/1.0 Nuclear Monitor"},
        ) as client:
            for feed_info in NUCLEAR_FEEDS:
                try:
                    resp = await client.get(feed_info["url"])
                    if resp.status_code != 200:
                        logger.warning(f"Nuclear {feed_info['name']}: HTTP {resp.status_code}")
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

                        # Must be nuclear-related
                        is_nuclear = any(
                            kw in text_lower
                            for kw in NUCLEAR_HIGH_PRIORITY + NUCLEAR_MEDIUM_PRIORITY
                        )
                        if not is_nuclear:
                            continue

                        # Calculate relevance
                        relevance = 0.5

                        for kw in NUCLEAR_HIGH_PRIORITY:
                            if kw in text_lower:
                                relevance = max(relevance, 0.85)
                                break

                        if relevance < 0.85:
                            for kw in NUCLEAR_MEDIUM_PRIORITY:
                                if kw in text_lower:
                                    relevance = max(relevance, 0.65)
                                    break

                        # Boost for key nuclear countries
                        region = ""
                        for country, info in NUCLEAR_COUNTRIES.items():
                            if country in text_lower:
                                relevance = min(1.0, relevance + info["boost"])
                                if not region:
                                    region = info["region"]

                        # Sentiment
                        sentiment = -0.3
                        if any(kw in text_lower for kw in ["test", "weapon", "threat", "enrichment", "leak", "accident"]):
                            sentiment = -0.8
                        elif any(kw in text_lower for kw in ["deal", "agreement", "disarmament", "cooperation"]):
                            sentiment = 0.3

                        # Parse date
                        published = None
                        if hasattr(entry, "published_parsed") and entry.published_parsed:
                            try:
                                published = datetime(*entry.published_parsed[:6])
                            except (ValueError, TypeError):
                                pass

                        tags = ["nuclear"]
                        if any(kw in text_lower for kw in ["weapon", "warhead", "icbm", "enrichment"]):
                            tags.append("proliferation")
                        if any(kw in text_lower for kw in ["leak", "accident", "meltdown", "radiation"]):
                            tags.append("nuclear_incident")
                        if any(kw in text_lower for kw in ["deal", "jcpoa", "treaty"]):
                            tags.append("diplomacy")

                        items.append(self._make_item(
                            title=f"Nuclear: {title}",
                            summary=summary,
                            url=link,
                            category="geopolitical",
                            region=region,
                            tags=tags,
                            raw_relevance=relevance,
                            sentiment_score=sentiment,
                            published_at=published,
                            source_id=f"nuke-{link[-60:]}" if link else f"nuke-{title[:40]}",
                        ))

                except Exception as e:
                    logger.error(f"Nuclear {feed_info['name']} error: {e}")

        logger.info(f"Nuclear Monitor: collected {len(items)} items")
        return items


def _strip_html(text: str) -> str:
    clean = re.sub(r'<[^>]+>', '', text)
    clean = re.sub(r'\s+', ' ', clean)
    return clean.strip()
