import logging
from datetime import datetime

import httpx

from app.services.collectors.base_collector import BaseCollector

logger = logging.getLogger(__name__)


class GDELTCollector(BaseCollector):
    """Collects global news events from GDELT DOC 2.0 API (free, no key)."""

    SOURCE_NAME = "gdelt"
    BASE_URL = "https://api.gdeltproject.org/api/v2/doc/doc"

    # Rotate through these themes each cycle to stay within rate limits
    QUERY_THEMES = [
        "sanctions OR tariff OR trade war OR embargo",
        "ceasefire OR peace deal OR war OR invasion OR military",
        "election OR referendum OR coup OR impeachment",
        "interest rate OR inflation OR recession OR GDP",
        "pandemic OR epidemic OR outbreak OR WHO",
        "AI regulation OR tech antitrust OR crypto regulation",
        "NATO OR UN resolution OR G7 OR G20 OR summit",
        "oil price OR OPEC OR energy crisis OR natural gas",
    ]

    REGION_MAP = {
        "US": "North America", "UK": "Europe", "FR": "Europe",
        "DE": "Europe", "CN": "Asia", "RU": "Europe",
        "UA": "Europe", "IL": "Middle East", "IR": "Middle East",
        "SA": "Middle East", "IN": "Asia", "JP": "Asia",
        "BR": "Americas", "AU": "Oceania", "ZA": "Africa",
    }

    CATEGORY_KEYWORDS = {
        "geopolitical": ["war", "sanction", "military", "nato", "invasion", "ceasefire", "diplomacy"],
        "financial": ["interest rate", "inflation", "recession", "gdp", "stock", "market", "fed", "ecb"],
        "political": ["election", "vote", "referendum", "coup", "impeach", "president", "congress"],
        "conflict": ["attack", "bombing", "troops", "fatalities", "escalation", "strike"],
        "crypto": ["bitcoin", "crypto", "sec", "cbdc", "stablecoin", "ethereum"],
        "tech": ["ai regulation", "antitrust", "tech ban", "data privacy"],
    }

    def __init__(self):
        self._cycle_count = 0

    async def collect(self, config: dict) -> list[dict]:
        items = []
        theme_idx = self._cycle_count % len(self.QUERY_THEMES)
        query = self.QUERY_THEMES[theme_idx]
        self._cycle_count += 1

        try:
            async with httpx.AsyncClient(
                timeout=30,
                headers={"User-Agent": "ScannerOSINT/1.0 (compatible; research tool)"},
            ) as client:
                response = await client.get(
                    self.BASE_URL,
                    params={
                        "query": query,
                        "mode": "ArtList",
                        "maxrecords": "50",
                        "timespan": "2h",
                        "format": "json",
                        "sort": "ToneDesc",
                    },
                )
                response.raise_for_status()
                data = response.json()

            articles = data.get("articles", [])
            logger.info(f"GDELT: fetched {len(articles)} articles for theme '{query}'")

            for article in articles:
                title = article.get("title", "").strip()
                if not title:
                    continue

                url = article.get("url", "")
                image_url = article.get("socialimage", "")
                source_country = article.get("sourcecountry", "")

                # Parse tone: "avgTone,posScore,negScore,polarity,..."
                tone_str = article.get("tone", "0,0,0,0,0,0")
                try:
                    tone_parts = [float(x) for x in tone_str.split(",")]
                    avg_tone = tone_parts[0] if tone_parts else 0.0
                except (ValueError, TypeError):
                    avg_tone = 0.0
                sentiment = max(-1.0, min(1.0, avg_tone / 10.0))

                # Parse date
                seen_date = article.get("seendate", "")
                published_at = None
                if seen_date:
                    try:
                        published_at = datetime.strptime(seen_date[:14], "%Y%m%dT%H%M%S")
                    except (ValueError, IndexError):
                        pass

                # Categorize
                title_lower = title.lower()
                category = "general"
                for cat, keywords in self.CATEGORY_KEYWORDS.items():
                    if any(kw in title_lower for kw in keywords):
                        category = cat
                        break

                # Region
                region = self.REGION_MAP.get(source_country[:2].upper(), "") if source_country else ""

                # Relevance based on tone strength
                raw_relevance = min(1.0, abs(avg_tone) / 8.0)

                items.append(self._make_item(
                    title=title,
                    summary="",
                    url=url,
                    image_url=image_url,
                    category=category,
                    region=region,
                    country=source_country,
                    tags=[t.strip() for t in query.lower().replace(" or ", ",").split(",") if t.strip()],
                    raw_relevance=raw_relevance,
                    sentiment_score=sentiment,
                    goldstein_scale=avg_tone,
                    published_at=published_at,
                    source_id=url,
                ))

        except httpx.HTTPStatusError as e:
            logger.error(f"GDELT HTTP error: {e.response.status_code}")
        except Exception as e:
            logger.error(f"GDELT collection error: {e}")

        return items
