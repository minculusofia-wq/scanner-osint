import logging
from datetime import datetime

import feedparser
import httpx

from .base_collector import BaseCollector

logger = logging.getLogger(__name__)

# Government and international org RSS feeds
GOV_FEEDS = [
    # US Government
    {
        "url": "https://www.whitehouse.gov/briefings-statements/feed/",
        "name": "White House",
        "category": "political",
        "region": "north_america",
        "country": "US",
    },
    {
        "url": "https://www.federalregister.gov/api/v1/documents.rss?conditions%5Bagencies%5D%5B%5D=defense-department",
        "name": "US DoD",
        "category": "geopolitical",
        "region": "north_america",
        "country": "US",
    },
    {
        "url": "https://www.federalregister.gov/api/v1/documents.rss?conditions%5Bagencies%5D%5B%5D=state-department",
        "name": "State Dept",
        "category": "geopolitical",
        "region": "north_america",
        "country": "US",
    },
    {
        "url": "https://www.federalregister.gov/api/v1/documents.rss?conditions%5Bagencies%5D%5B%5D=treasury-department&conditions%5Btype%5D%5B%5D=NOTICE",
        "name": "US Treasury",
        "category": "financial",
        "region": "north_america",
        "country": "US",
    },
    # International orgs
    {
        "url": "https://news.un.org/feed/subscribe/en/news/all/rss.xml",
        "name": "UN News",
        "category": "geopolitical",
        "region": "global",
        "country": "",
    },
    {
        "url": "https://www.ecb.europa.eu/rss/press.html",
        "name": "ECB",
        "category": "financial",
        "region": "europe",
        "country": "",
    },
    # Major news (high reliability)
    {
        "url": "https://feeds.bbci.co.uk/news/world/rss.xml",
        "name": "BBC World",
        "category": "geopolitical",
        "region": "global",
        "country": "",
    },
    {
        "url": "https://rss.nytimes.com/services/xml/rss/nyt/World.xml",
        "name": "NYT World",
        "category": "geopolitical",
        "region": "global",
        "country": "",
    },
    {
        "url": "https://www.aljazeera.com/xml/rss/all.xml",
        "name": "Al Jazeera",
        "category": "geopolitical",
        "region": "global",
        "country": "",
    },
]

# Keywords that signal high-relevance items
HIGH_RELEVANCE_KEYWORDS = [
    "sanctions", "military", "emergency", "threat", "nuclear",
    "strike", "deploy", "invasion", "ceasefire", "war",
    "terror", "missile", "troops", "conflict", "crisis",
    "trade war", "tariff", "embargo", "blockade",
    "election", "impeach", "resign", "coup",
]

MEDIUM_RELEVANCE_KEYWORDS = [
    "diplomacy", "agreement", "treaty", "summit", "negotiate",
    "economy", "inflation", "interest rate", "gdp", "unemployment",
    "climate", "energy", "oil", "gas", "pipeline",
    "cyber", "hack", "intelligence", "espionage",
]


class GovRSSCollector(BaseCollector):
    """Collects intelligence from government and international organization RSS feeds."""

    SOURCE_NAME = "gov_rss"

    async def collect(self, config: dict) -> list[dict]:
        items = []

        async with httpx.AsyncClient(
            timeout=15,
            headers={"User-Agent": "ScannerOSINT/1.0 RSS Monitor"},
            follow_redirects=True,
        ) as client:
            for feed_info in GOV_FEEDS:
                try:
                    resp = await client.get(feed_info["url"])
                    if resp.status_code != 200:
                        logger.warning(f"Gov RSS {feed_info['name']}: HTTP {resp.status_code}")
                        continue

                    feed = feedparser.parse(resp.text)

                    if feed.bozo and not feed.entries:
                        logger.warning(f"Gov RSS {feed_info['name']}: feed parse error")
                        continue

                    for entry in feed.entries[:10]:
                        title = entry.get("title", "").strip()
                        if not title:
                            continue

                        summary = entry.get("summary", entry.get("description", "")).strip()
                        summary = _strip_html(summary)[:500]

                        link = entry.get("link", "")

                        published = None
                        if hasattr(entry, "published_parsed") and entry.published_parsed:
                            try:
                                published = datetime(*entry.published_parsed[:6])
                            except (ValueError, TypeError):
                                pass
                        elif hasattr(entry, "updated_parsed") and entry.updated_parsed:
                            try:
                                published = datetime(*entry.updated_parsed[:6])
                            except (ValueError, TypeError):
                                pass

                        text_lower = f"{title} {summary}".lower()
                        relevance = 0.5

                        for kw in HIGH_RELEVANCE_KEYWORDS:
                            if kw in text_lower:
                                relevance = max(relevance, 0.9)
                                break

                        if relevance < 0.9:
                            for kw in MEDIUM_RELEVANCE_KEYWORDS:
                                if kw in text_lower:
                                    relevance = max(relevance, 0.7)
                                    break

                        items.append(self._make_item(
                            title=f"[{feed_info['name']}] {title}",
                            summary=summary,
                            url=link,
                            category=feed_info["category"],
                            region=feed_info["region"],
                            country=feed_info["country"],
                            tags=["government", feed_info["name"].lower().replace(" ", "_"), "official"],
                            raw_relevance=relevance,
                            published_at=published,
                            source_id=f"gov-{feed_info['name']}-{link[-60:]}",
                        ))

                except Exception as e:
                    logger.error(f"Gov RSS {feed_info['name']} error: {e}")

        logger.info(f"Gov RSS: collected {len(items)} items")
        return items


def _strip_html(text: str) -> str:
    """Remove HTML tags and decode common entities."""
    import re
    clean = re.sub(r'<[^>]+>', '', text)
    clean = clean.replace('&amp;', '&').replace('&lt;', '<').replace('&gt;', '>').replace('&quot;', '"').replace('&#39;', "'")
    clean = re.sub(r'\s+', ' ', clean)
    return clean.strip()
